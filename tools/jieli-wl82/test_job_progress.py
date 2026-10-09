"""Offline receipt/progress tests, with authenticated HTTP on a fake local server."""
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import job_progress
import remote_backend
import remote_bridge


CANDIDATE, BASELINE = 'b' * 64, 'a' * 64
TOKEN = 'offline-progress-token-' + 'x' * 48


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.session = self.root / 'session'
        self.run = self.session / 'runs' / uuid.uuid4().hex
        self.run.mkdir(parents=True)
        self.job = {'id': uuid.uuid4().hex, 'operation': 'switch_app', 'status': 'running',
            'created': (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(),
            'updated': (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
            'result': None}
        self.request = {'id': self.job['id'], 'operation': 'switch_app',
                        'catalog_id': 'doom-test', 'entry_method': 'serial'}
        self.packages = SimpleNamespace(get=lambda ident: {'request': {'sha256': CANDIDATE}})
        self.attempt = {'sha256': CANDIDATE, 'baseline_sha256': BASELINE,
                        'sectors': [0x5000, 0x4000]}
        self.receipt = {'status': 'sector_verified', 'candidate_sha256': CANDIDATE,
                        'baseline_sha256': BASELINE, 'verified_sectors': ['0x5000']}
        self.state = {'operation': 'flash', 'flash_attempt': {'sha256': CANDIDATE,
                      'run': self.run.relative_to(self.session).as_posix()}}
        self.save()

    def tearDown(self):
        self.folder.cleanup()

    def save(self):
        for path, value in [(self.run / 'attempt.json', self.attempt),
                            (self.run / 'deployment.json', self.receipt),
                            (self.session / 'state.json', self.state)]:
            path.write_text(json.dumps(value), encoding='utf-8')

    def progress(self):
        return job_progress.progress_for_job(self.session, self.packages, self.job, self.request)

    def complete_readback(self):
        self.receipt.update(status='written_and_readback_verified',
                            verified_sectors=['0x5000', '0x4000'],
                            full_readback_count=1, full_readback_sha256=CANDIDATE)
        self.save()

    def test_active_sector_counts_and_no_completion(self):
        result = self.progress()
        self.assertEqual((result['phase'], result['verified_sectors'], result['total_sectors']), ('write', 1, 2))
        self.assertFalse(result['write_complete'])
        self.assertFalse(result['full_readback_verified'])
        self.assertFalse(result['boot_verified'])

    def test_all_sectors_remain_readback_pending(self):
        self.receipt.update(status='full_verification', verified_sectors=['0x5000', '0x4000'])
        self.save()
        result = self.progress()
        self.assertEqual(result['phase'], 'readback')
        self.assertTrue(result['write_complete'])
        self.assertFalse(result['full_readback_verified'])
        self.assertFalse(result['boot_verified'])

    def test_full_readback_reset_then_startup_remains_pending(self):
        self.complete_readback()
        self.state['operation'] = 'reset'
        self.save()
        self.assertEqual(self.progress()['phase'], 'reset')
        self.state['operation'] = 'observe'
        self.save()
        result = self.progress()
        self.assertEqual(result['phase'], 'boot')
        self.assertTrue(result['full_readback_verified'])
        self.assertFalse(result['boot_verified'])

    def test_failed_startup_preserves_write_counts_without_leaking_errors(self):
        self.complete_readback()
        self.job.update(status='failed', result={'ok': False, 'error': 'SerialException PRIVATE_TOKEN PRIVATE_PATH'})
        result = self.progress()
        self.assertEqual(result['phase'], 'failed')
        self.assertEqual(result['verified_sectors'], 2)
        self.assertTrue(result['write_complete'])
        self.assertTrue(result['full_readback_verified'])
        self.assertFalse(result['boot_verified'])
        self.assertTrue(result['failed'])
        self.assertEqual(result['error'], 'startup_verification_failed')
        self.assertNotIn('PRIVATE_', json.dumps(result))

    def test_successful_switch_requires_reported_startup_confirmation(self):
        self.complete_readback()
        self.job.update(status='succeeded', result={'ok': True, 'data': {'serial_boot_verified': True}})
        result = self.progress()
        self.assertEqual(result['phase'], 'completed')
        self.assertTrue(result['boot_verified'])
        self.assertFalse(result['failed'])

    def test_failed_receipt_surfaces_before_bridge_terminal_update(self):
        self.receipt['status'] = 'failed'
        self.save()
        result = self.progress()
        self.assertEqual(result['phase'], 'failed')
        self.assertTrue(result['failed'])
        self.assertEqual(self.job['status'], 'running')

    def test_old_job_never_borrows_newer_or_older_run(self):
        self.job.update(status='failed',
            created=(datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat(),
            updated=(datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat())
        self.assertIsNone(self.progress()['verified_sectors'])
        self.job.update(status='running', created=(datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat())
        self.assertIsNone(self.progress()['verified_sectors'])

    def test_candidate_baseline_and_prefix_mismatch_are_unavailable(self):
        changes = [('attempt', 'sha256', 'c' * 64),
                   ('receipt', 'baseline_sha256', 'c' * 64),
                   ('receipt', 'verified_sectors', ['0x4000'])]
        for target, key, value in changes:
            original = getattr(self, target)[key]
            getattr(self, target)[key] = value
            self.save()
            with self.subTest(target=target, key=key):
                self.assertIsNone(self.progress()['verified_sectors'])
            getattr(self, target)[key] = original

    def test_ambiguous_matching_attempts_do_not_guess(self):
        second = self.session / 'runs' / uuid.uuid4().hex
        second.mkdir()
        for filename in ('attempt.json', 'deployment.json'):
            (second / filename).write_bytes((self.run / filename).read_bytes())
        self.assertIsNone(self.progress()['verified_sectors'])

    def test_malformed_metadata_and_invalid_full_readback_proof(self):
        (self.run / 'deployment.json').write_text('{partial', encoding='utf-8')
        result = self.progress()
        self.assertIsNone(result['verified_sectors'])
        self.assertIn('unavailable', result['message'])
        self.complete_readback()
        self.receipt['full_readback_count'] = True
        self.save()
        self.assertFalse(self.progress()['full_readback_verified'])
        self.receipt.update(full_readback_count=1, full_readback_sha256='c' * 64)
        self.save()
        self.assertFalse(self.progress()['full_readback_verified'])

    def test_request_identity_and_escaping_state_paths_are_not_followed(self):
        self.request['id'] = uuid.uuid4().hex
        self.assertIsNone(self.progress()['verified_sectors'])
        self.request['id'] = self.job['id']
        self.complete_readback()
        self.state['flash_attempt']['run'] = '../PRIVATE_OUTSIDE'
        self.state['operation'] = 'observe'
        self.save()
        result = self.progress()
        self.assertEqual(result['phase'], 'reset')
        self.assertNotIn('PRIVATE_OUTSIDE', json.dumps(result))

    def test_windows_adapter_progress_never_calls_hardware_status_or_pipe(self):
        repo = self.root / 'repo'
        client = repo / 'tools/jieli-wl82/flash-session-client.ps1'
        client.parent.mkdir(parents=True)
        client.write_text('# offline fixture', encoding='utf-8')
        (self.session / 'session.json').write_text(json.dumps({'root': str(self.session)}), encoding='utf-8')
        adapter = remote_backend.WindowsBackend(repo, self.session)
        adapter.packages = self.packages
        with patch.object(adapter, 'status', side_effect=AssertionError('No enumeration')), \
             patch.object(adapter, '_pipe', side_effect=AssertionError('No device operation')), \
             patch.object(remote_backend.subprocess, 'run', side_effect=AssertionError('No process')):
            self.assertEqual(adapter.job_progress(self.job, self.request)['verified_sectors'], 1)


class AuthenticatedProgressTests(unittest.TestCase):
    setUp = ProgressTests.setUp
    tearDown = ProgressTests.tearDown
    save = ProgressTests.save

    def manager_fixture(self):
        backend = SimpleNamespace(job_progress=lambda job, request:
            job_progress.progress_for_job(self.session, self.packages, job, request))
        manager = remote_bridge.JobManager(backend, self.root / 'bridge')
        self.job['request_digest'] = hashlib.sha256(remote_bridge._json_bytes(self.request)).hexdigest()
        manager._jobs[self.job['id']] = self.job
        directory = manager.jobs_dir / self.job['id']
        directory.mkdir()
        (directory / 'request.json').write_text(json.dumps(self.request), encoding='utf-8')
        return manager, backend

    def test_terminal_snapshot_retains_counts_after_helper_change_and_restart(self):
        self.receipt.update(status='written_and_readback_verified', verified_sectors=['0x5000', '0x4000'],
                            full_readback_count=1, full_readback_sha256=CANDIDATE)
        self.save()
        self.job.update(status='failed', result={'ok': False, 'error': 'startup error'})
        manager, backend = self.manager_fixture()
        original = {key: self.job[key] for key in ('created', 'updated', 'request_digest')}
        try:
            first = manager.get_job(self.job['id'])
            self.assertEqual(first['progress']['verified_sectors'], 2)
            saved = json.loads((manager.jobs_dir / self.job['id'] / 'job.json').read_text())
            self.assertIn('_progress_snapshot', saved)
            self.assertNotIn('_progress_snapshot', first)
            self.assertNotIn('image', json.dumps(saved['_progress_snapshot']))
            self.assertEqual({key: saved[key] for key in original}, original)
            new_session = self.root / 'replacement-helper'
            (new_session / 'runs').mkdir(parents=True)
            backend.job_progress = lambda job, request: job_progress.progress_for_job(
                new_session, self.packages, job, request)
            with patch.object(manager, '_save', side_effect=AssertionError('Cache must persist once')):
                second = manager.get_job(self.job['id'])
            self.assertEqual(second['progress'], first['progress'])
            manager.close()
            manager = remote_bridge.JobManager(backend, self.root / 'bridge')
            third = manager.get_job(self.job['id'])
            self.assertEqual(third['progress'], first['progress'])
            self.assertFalse(third['progress']['boot_verified'])
            self.assertEqual(third['status'], 'failed')
        finally:
            manager.close()

    def test_stale_wrong_or_inconsistent_cache_cannot_override_job_status(self):
        self.job['status'] = 'failed'
        manager, backend = self.manager_fixture()
        valid = {'phase': 'failed', 'verified_sectors': 2, 'total_sectors': 2,
            'message': 'Write and full readback verified; startup verification failed.',
            'write_complete': True, 'full_readback_verified': True, 'boot_verified': False, 'failed': True}
        try:
            manager._remember_progress(self.job, valid)
            snapshot = json.loads(json.dumps(self.job['_progress_snapshot']))
            variants = [('id', uuid.uuid4().hex), ('request_digest', 'd' * 64),
                        ('created', '2020-01-01T00:00:00+00:00'), ('status', 'succeeded'),
                        ('updated', '2020-01-01T00:00:00+00:00')]
            # No eligible current receipt: invalid snapshots must yield unknown
            # counts rather than borrowing claimed historical completion.
            empty = self.root / 'empty-helper'
            (empty / 'runs').mkdir(parents=True)
            backend.job_progress = lambda job, request: job_progress.progress_for_job(empty, self.packages, job, request)
            for key, value in variants:
                with self.subTest(key=key):
                    self.job['_progress_snapshot'] = dict(snapshot, **{key: value})
                    public = manager.get_job(self.job['id'])
                    self.assertEqual(public['status'], 'failed')
                    self.assertIsNone(public['progress']['verified_sectors'])
            for key, value in [('boot_verified', True), ('phase', 'completed'),
                               ('failed', False), ('total_sectors', 999), ('extra', 'PRIVATE_TOKEN')]:
                with self.subTest(progress_key=key):
                    bad = dict(valid, **{key: value})
                    self.job['_progress_snapshot'] = dict(snapshot, progress=bad)
                    public = manager.get_job(self.job['id'])
                    self.assertIsNone(public['progress']['verified_sectors'])
                    self.assertNotIn('PRIVATE_TOKEN', json.dumps(public))
            self.job['_progress_snapshot'] = snapshot
            self.job['status'] = 'succeeded'
            public = manager.get_job(self.job['id'])
            self.assertEqual(public['status'], 'succeeded')
            self.assertEqual(public['progress']['phase'], 'completed')
            self.assertIsNone(public['progress']['verified_sectors'])
        finally:
            manager.close()

    def test_engine_captures_terminal_progress_before_saving_outcome(self):
        terminal = {'phase': 'completed', 'verified_sectors': 2, 'total_sectors': 2,
            'message': 'Firmware startup verified.', 'write_complete': True,
            'full_readback_verified': True, 'boot_verified': True, 'failed': False}
        backend = SimpleNamespace(execute=lambda operation, **kwargs:
            {'ok': True, 'data': {'serial_boot_verified': True}},
            job_progress=lambda job, request: terminal)
        manager = remote_bridge.JobManager(backend, self.root / 'engine-bridge')
        try:
            manager.submit(self.request)
            manager._worker.join(timeout=5)
            self.assertFalse(manager._worker.is_alive())
            saved = json.loads((manager.jobs_dir / self.job['id'] / 'job.json').read_text())
            self.assertEqual(saved['status'], 'succeeded')
            self.assertEqual(saved['_progress_snapshot']['progress'], terminal)
            self.assertEqual(manager.get_job(self.job['id'])['progress'], terminal)
        finally:
            manager.close()

    def test_unexpected_progress_failure_cannot_change_or_lose_job_outcome(self):
        def broken_progress(job, request):
            raise RuntimeError('Optional metadata fixture failure')
        backend = SimpleNamespace(execute=lambda operation, **kwargs: {'ok': True, 'data': {}},
                                  job_progress=broken_progress)
        manager = remote_bridge.JobManager(backend, self.root / 'error-bridge')
        try:
            manager.submit(self.request)
            manager._worker.join(timeout=5)
            self.assertFalse(manager._worker.is_alive())
            saved = json.loads((manager.jobs_dir / self.job['id'] / 'job.json').read_text())
            self.assertEqual(saved['status'], 'succeeded')
            self.assertTrue(saved['result']['ok'])
            public = manager.get_job(self.job['id'])
            self.assertEqual(public['status'], 'succeeded')
            self.assertIsNone(public['progress']['verified_sectors'])
            self.assertNotIn('Optional metadata fixture failure', json.dumps(public))
        finally:
            manager.close()

    def test_authenticated_job_get_includes_progress_and_rejects_tampering(self):
        # Existing production handler, fake metadata-only backend, random local
        # port. No real service is restarted and no jobs are submitted.
        backend = SimpleNamespace(job_progress=lambda job, request:
            job_progress.progress_for_job(self.session, self.packages, job, request))
        manager = remote_bridge.JobManager(backend, self.root / 'bridge')
        self.job['request_digest'] = hashlib.sha256(remote_bridge._json_bytes(self.request)).hexdigest()
        manager._jobs[self.job['id']] = self.job
        directory = manager.jobs_dir / self.job['id']
        directory.mkdir()
        request_path = directory / 'request.json'
        request_path.write_text(json.dumps(self.request), encoding='utf-8')
        server = remote_bridge.make_server(manager, TOKEN, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def get(token):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=5)
            headers = {'Authorization': 'Bearer ' + token} if token else {}
            connection.request('GET', '/v1/jobs/' + self.job['id'], headers=headers)
            response = connection.getresponse()
            payload = json.loads(response.read())
            connection.close()
            return response.status, payload
        try:
            self.assertEqual(get(None)[0], 401)
            code, payload = get(TOKEN)
            self.assertEqual(code, 200)
            self.assertTrue(payload['ok'])
            payload = payload['data']
            self.assertEqual(payload['progress']['verified_sectors'], 1)
            self.assertNotIn('request', payload)
            changed = dict(self.request, catalog_id='other-package')
            request_path.write_text(json.dumps(changed), encoding='utf-8')
            code, payload = get(TOKEN)
            self.assertEqual(code, 200)
            payload = payload['data']
            self.assertEqual(payload['status'], 'running')
            self.assertIsNone(payload['progress']['verified_sectors'])
            self.assertIn('unavailable', payload['progress']['message'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            manager.close()


if __name__ == '__main__':
    unittest.main()
