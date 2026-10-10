"""Client transport tests; no Tailscale peers or physical devices."""
import hashlib
import io
import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from remote_client import Client, NoRedirect
import remote_client

TOKEN = 'test-only-token-that-is-at-least-32-characters'


class Response(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}


class ClientTests(unittest.TestCase):
    def test_public_credentials_or_query_origin_is_refused(self):
        for url in ('http://example.com', 'http://192.168.1.2', 'http://user:pass@localhost',
                    'http://localhost?token=secret', 'http://localhost/api', 'file:///tmp/token'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                Client(url, TOKEN)

    def test_accepts_loopback_and_tailscale_origins(self):
        for url in ('http://127.0.0.1:9770', 'https://laptop.tail1234.ts.net',
                    'http://100.77.33.76:9771', 'http://[fd7a:115c:a1e0::1]:9771'):
            Client(url, TOKEN)

    def test_redirect_never_reuses_token(self):
        with self.assertRaisesRegex(ValueError, 'Redirect refused'):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')

    def test_job_timeout_never_resubmits(self):
        client = Client('http://127.0.0.1:9770', TOKEN)
        client.opener = Mock()
        client.opener.open.side_effect = URLError('network disconnected')
        with self.assertRaises(URLError):
            client.call('/v1/jobs', {'id': 'a'*32, 'operation': 'reset'})
        self.assertEqual(client.opener.open.call_count, 1)
        request = client.opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), 'Bearer '+TOKEN)
        self.assertNotIn(TOKEN.encode(), request.data)
        self.assertNotIn(TOKEN, request.full_url)

    def test_verified_binary_download_and_bad_digest(self):
        data = bytes(1048576)
        client = Client('http://127.0.0.1:9770', TOKEN)
        client.opener = Mock()
        client.opener.open.return_value = Response(data, {'X-FM1-SHA256': hashlib.sha256(data).hexdigest()})
        self.assertEqual(client.call('/v1/baseline', binary=True), data)
        for payload, digest in ((data, '0'*64), (data[:-1], hashlib.sha256(data[:-1]).hexdigest())):
            client.opener.open.return_value = Response(payload, {'X-FM1-SHA256': digest})
            with self.assertRaisesRegex(ValueError, 'size/hash mismatch'):
                client.call('/v1/baseline', binary=True)

    def test_known_failed_job_is_returned_without_retry(self):
        job = {'id': 'a'*32, 'status': 'failed'}
        client = Client('http://127.0.0.1:9770', TOKEN)
        client.opener = Mock()
        client.opener.open.return_value = Response(json.dumps({'ok': True, 'data': job}).encode())
        self.assertEqual(client.wait('a'*32, 1), job)
        self.assertEqual(client.opener.open.call_count, 1)

    def test_unknown_official_job_is_inspected_without_resubmission(self):
        saved = {'id': 'a' * 32, 'operation': 'official_updater', 'status': 'unknown'}
        client = Client('http://127.0.0.1:9770', TOKEN)
        client.opener = Mock()
        client.opener.open.return_value = Response(json.dumps({'ok': True, 'data': saved}).encode())
        self.assertEqual(client.wait(saved['id'], 1), saved)
        self.assertEqual(client.opener.open.call_count, 1)
        request = client.opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertTrue(request.full_url.endswith('/v1/jobs/' + saved['id']))
        self.assertIsNone(request.data)

    def test_official_updater_cli_keeps_the_reviewed_hash_and_explicit_job_id(self):
        identifier, digest = 'e' * 32, '1a' * 32
        client = Mock()
        client.call.return_value = {'id': identifier, 'status': 'queued'}
        arguments = ['remote_client.py', '--url', 'http://127.0.0.1:9770',
                     '--token-file', 'offline.token', 'job', 'official_updater',
                     '--id', identifier, '--expected-sha256', digest]
        with patch('sys.argv', arguments), patch('remote_client.Path.read_text', return_value=TOKEN), \
                patch('remote_client.Client', return_value=client), \
                patch('sys.stdout', new_callable=io.StringIO), patch('sys.stderr', new_callable=io.StringIO):
            self.assertEqual(remote_client.main(), 0)
        client.call.assert_called_once_with('/v1/jobs', {'id': identifier,
                                                       'operation': 'official_updater',
                                                       'expected_sha256': digest})
        client.wait.assert_not_called()

    def test_auto_switch_cli_lost_reply_preserves_id_without_retry_or_wait(self):
        identifier = 'f' * 32
        client = Mock()
        client.call.side_effect = URLError('submission reply lost')
        arguments = ['remote_client.py', '--url', 'http://127.0.0.1:9770',
                     '--token-file', 'offline.token', 'job', 'switch_app',
                     '--id', identifier, '--catalog-id', 'nes-test',
                     '--entry-method', 'auto', '--wait']
        with patch('sys.argv', arguments), patch('remote_client.Path.read_text', return_value=TOKEN), \
                patch('remote_client.Client', return_value=client), \
                patch('sys.stdout', new_callable=io.StringIO), \
                patch('sys.stderr', new_callable=io.StringIO) as error_output:
            with self.assertRaises(URLError):
                remote_client.main()
            self.assertIn('Job id: ' + identifier, error_output.getvalue())
        client.call.assert_called_once_with('/v1/jobs', {'id': identifier, 'operation': 'switch_app',
                                                       'catalog_id': 'nes-test', 'entry_method': 'auto'})
        client.wait.assert_not_called()


if __name__ == '__main__':
    unittest.main()
