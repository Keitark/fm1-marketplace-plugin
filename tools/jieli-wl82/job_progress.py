"""Read-only progress from current-job protected receipts; no device access."""
from datetime import datetime
import json
from pathlib import Path
import re


HASH = re.compile(r'[0-9a-f]{64}')
RUN = re.compile(r'[0-9a-f]{32}')
TERMINAL = {'succeeded', 'failed', 'unknown'}


def validate_terminal_progress(progress, status):
    """Return a compact metadata-only snapshot consistent with its job outcome."""
    required = {'phase', 'verified_sectors', 'total_sectors', 'message',
                'write_complete', 'full_readback_verified', 'boot_verified', 'failed'}
    if (status not in TERMINAL or type(progress) is not dict or
            not required <= set(progress) <= required | {'error'}):
        raise ValueError('Invalid terminal progress snapshot')
    expected_phase = 'completed' if status == 'succeeded' else 'failed'
    if progress['phase'] != expected_phase:
        raise ValueError('Progress phase differs from job outcome')
    if (type(progress['message']) is not str or not 1 <= len(progress['message']) <= 500 or
            any(type(progress[key]) is not bool for key in
                ('write_complete', 'full_readback_verified', 'boot_verified', 'failed')) or
            progress['failed'] != (status != 'succeeded')):
        raise ValueError('Invalid terminal progress values')
    verified, total = progress['verified_sectors'], progress['total_sectors']
    if not ((verified is None and total is None) or
            (type(verified) is int and type(total) is int and 0 <= verified <= total <= 143 and total > 0)):
        raise ValueError('Invalid terminal sector counts')
    if (progress['write_complete'] and (total is None or verified != total) or
            progress['full_readback_verified'] and not progress['write_complete'] or
            progress['boot_verified'] and (status != 'succeeded' or not progress['full_readback_verified'])):
        raise ValueError('Invalid terminal completion proof')
    if 'error' in progress and (type(progress['error']) is not str or
            not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', progress['error'])):
        raise ValueError('Invalid terminal progress error')
    return dict(progress)


def _read(path):
    # Metadata only. Do not load firmware images, transcripts, tokens, or logs.
    if path.stat().st_size > 131072:
        raise ValueError('Progress metadata exceeds size limit')
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if type(value) is not dict:
        raise ValueError('Invalid progress metadata')
    return value


def _epoch(value):
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('Progress timestamp lacks a timezone')
    return date.timestamp()


def _base(job):
    status = job.get('status')
    failed = status in {'failed', 'unknown'}
    return {'phase': 'failed' if failed else ('completed' if status == 'succeeded' else 'preparing'),
            'verified_sectors': None, 'total_sectors': None,
            'message': ('Operation outcome unknown.' if status == 'unknown' else
                        'Operation failed.' if failed else
                        'Operation completed.' if status == 'succeeded' else 'Preparing firmware.'),
            'write_complete': False, 'full_readback_verified': False,
            'boot_verified': False, 'failed': failed}


def _expected(packages, request):
    if request.get('operation') == 'switch_app':
        bundle = packages.get(request.get('catalog_id'))
        return bundle['request']['sha256'], None
    if request.get('operation') in {'flash', 'retry_flash', 'recover_flash'}:
        image = request.get('request') or {}
        return image.get('sha256'), image.get('baseline_sha256')
    return None, None


def _matching_run(session, job, candidate, baseline):
    created = _epoch(job['created'])
    ended = _epoch(job['updated']) if job.get('status') in TERMINAL else None
    runs = (session / 'runs').resolve()
    if not runs.is_relative_to(session) or not runs.is_dir():
        return None
    matches = []
    # Restrict history inspection to named run directories in the job's time
    # window. A newer attempt cannot become an older job's progress receipt.
    directories = list(runs.iterdir())
    if len(directories) > 4096:
        raise ValueError('Too many protected progress runs')
    for run in directories:
        if not RUN.fullmatch(run.name) or not run.is_dir():
            continue
        resolved = run.resolve()
        if not resolved.is_relative_to(runs):
            continue
        attempt_path = resolved / 'attempt.json'
        receipt_path = resolved / 'deployment.json'
        if any(not path.resolve().is_relative_to(resolved) for path in (attempt_path, receipt_path)):
            continue
        if not attempt_path.is_file():
            continue
        started = attempt_path.stat().st_ctime
        if started < created or (ended is not None and started > ended):
            continue
        attempt = _read(attempt_path)
        if attempt.get('sha256') != candidate or (baseline and attempt.get('baseline_sha256') != baseline):
            continue
        if not receipt_path.is_file():
            continue
        # Require both files to stay in this run even if local filesystem
        # metadata contains a junction/symlink; never follow an external path.
        receipt = _read(receipt_path)
        if (receipt.get('candidate_sha256') != candidate or
                receipt.get('baseline_sha256') != attempt.get('baseline_sha256') or
                not HASH.fullmatch(attempt.get('baseline_sha256') or '')):
            continue
        matches.append((resolved, attempt, receipt))
    # Ambiguity is unavailable progress, never a guess based on latest state.
    return matches[0] if len(matches) == 1 else None


def progress_for_job(session, packages, job, request):
    progress = _base(job)
    try:
        if not session or request.get('id') != job.get('id') or request.get('operation') != job.get('operation'):
            return progress
        session = Path(session).resolve()
        candidate, baseline = _expected(packages, request)
        if not candidate or not HASH.fullmatch(candidate):
            return progress
        if baseline is not None and not HASH.fullmatch(baseline or ''):
            return progress
        match = _matching_run(session, job, candidate, baseline)
        if match is None:
            if job.get('status') == 'running':
                progress['message'] = 'Preparing firmware; waiting for this job’s write receipt.'
            return progress
        run, attempt, receipt = match
        sectors, verified = attempt.get('sectors'), receipt.get('verified_sectors')
        if (type(sectors) is not list or not 1 <= len(sectors) <= 143 or
                any(type(a) is not int or a % 4096 or not 0x4000 <= a <= 0x92000 for a in sectors) or
                len(set(sectors)) != len(sectors) or sectors[-1] != 0x4000 or
                type(verified) is not list or len(verified) > len(sectors) or
                verified != [hex(a) for a in sectors[:len(verified)]]):
            raise ValueError('Invalid protected sector progress')
        progress['verified_sectors'] = len(verified)
        progress['total_sectors'] = len(sectors)
        progress['write_complete'] = len(verified) == len(sectors)
        progress['full_readback_verified'] = bool(progress['write_complete'] and
            receipt.get('status') in {'written_and_readback_verified', 'written_and_twice_readback_verified'} and
            type(receipt.get('full_readback_count')) is int and receipt['full_readback_count'] in (1, 2) and
            receipt.get('full_readback_sha256') == candidate)
        data = (job.get('result') or {}).get('data') or {}
        progress['boot_verified'] = bool(job.get('status') == 'succeeded' and
                                          data.get('serial_boot_verified') is True)
        status = job.get('status')
        if receipt.get('status') == 'failed' and status != 'unknown':
            progress.update(phase='failed', failed=True,
                message='Firmware write or readback failed; inspect the protected session.',
                error='write_or_readback_failed')
        elif status in {'failed', 'unknown'}:
            if status == 'unknown':
                progress['message'] = 'Operation outcome unknown; inspect the protected session.'
            elif progress['full_readback_verified']:
                progress['message'] = 'Write and full readback verified; startup verification failed.'
                progress['error'] = 'startup_verification_failed'
            else:
                progress['message'] = 'Firmware write or readback failed; inspect the protected session.'
                progress['error'] = 'write_or_readback_failed'
        elif status == 'succeeded':
            progress['message'] = ('Firmware write, full readback, and startup verified.' if progress['boot_verified'] else
                                   'Firmware write operation completed.')
        elif not progress['write_complete']:
            progress.update(phase='write', message=f'Writing firmware: {len(verified)}/{len(sectors)} sectors verified.')
        elif not progress['full_readback_verified']:
            progress.update(phase='readback', message='All sectors verified; checking the complete firmware readback.')
        else:
            # Mutable state is usable for phase selection only when it still
            # points to this exact attempt. It cannot authorize completion.
            state = _read(session / 'state.json')
            current = state.get('flash_attempt') or {}
            same_run = (current.get('run') == str(run.relative_to(session)).replace('\\', '/') or
                        current.get('run') == str(run.relative_to(session)))
            same_attempt = same_run and current.get('sha256') == candidate
            operation = state.get('operation') if same_attempt else None
            if operation in {'observe', 'serial_status'}:
                progress.update(phase='boot', message='Full readback verified; checking firmware startup.')
            else:
                progress.update(phase='reset', message='Full readback verified; restarting the FM-1.')
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        # Reads can race atomic receipt updates. A progress failure cannot alter
        # the job outcome or initiate any operation; retain safe base metadata.
        progress = _base(job)
        progress['message'] = 'Progress metadata unavailable; job status remains authoritative.'
    return progress
