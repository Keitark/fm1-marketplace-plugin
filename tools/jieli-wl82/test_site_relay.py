"""Offline relay contract tests; fake Sites and synthetic loopback HTTP only."""
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

import site_relay as relay


RELAY_TOKEN = "synthetic-relay-" + "r" * 48
SITES_TOKEN = "synthetic-sites-" + "s" * 48
BRIDGE_TOKEN = "synthetic-bridge-" + "b" * 48
EXPECTED_SHA = "c" * 64


def task(operation="status", identifier=None, **arguments):
    return {"id": identifier or uuid.uuid4().hex,
            "operation": operation, "arguments": arguments}


def envelope(identifier, status="queued", **fields):
    return {"ok": True, "data": {"id": identifier, "status": status, **fields}}


class FakeBridge:
    def __init__(self):
        self.calls = []
        self.post_error = None
        self.get_error = None
        self.jobs = {}
        self.metadata = {"engine": {"blocked_unknown": True}, "device": {"device_io": False}}
        self.catalog = {"apps": [{"profile": "nes", "variants": [
            {"id": "nes-test", "sha256": EXPECTED_SHA, "ready": True}]}]}
        self.hook = None

    def request(self, method, route, body=None):
        self.calls.append((method, route, body))
        if self.hook is not None:
            self.hook(method, route, body)
        if method == "POST":
            self.jobs[body["id"]] = envelope(body["id"])
            if self.post_error is not None:
                raise self.post_error
            return self.jobs[body["id"]]
        if self.get_error is not None:
            raise self.get_error
        if route.startswith("/v1/jobs/"):
            identifier = route.rsplit("/", 1)[-1]
            if identifier not in self.jobs:
                raise relay.RelayError("http_rejected", 404)
            return self.jobs[identifier]
        if route == "/v1/catalog":
            return {"ok": True, "data": self.catalog}
        return {"ok": True, "data": self.metadata}


class FakeSite:
    def __init__(self):
        self.tasks = []
        self.calls = []
        self.result_error = None
        self.connected = True

    def request(self, method, route, body=None):
        self.calls.append((method, route, body))
        if route == "/relay/poll":
            batch, self.tasks = self.tasks, []
            return {"tasks": batch, "connected": self.connected}
        if route == "/relay/result" and self.result_error is not None:
            raise self.result_error
        if route == "/relay/result":
            return {"saved": True}
        return {"ok": True}


class ValidationTests(unittest.TestCase):
    def test_exact_task_schema_rejects_device_or_arbitrary_paths(self):
        bad = [task("reset"), task("read_firmware"), task("status", url="https://other.example"),
               task("status", path="/v1/baseline"), task("plan_app", catalog_id="../escape"),
               task("switch_app", catalog_id="nes-test", entry_method="guess"),
               task("switch_app", catalog_id="nes-test"), task("job", job_id="../escape"),
               task("catalog", command="rm"), task("status", identifier="A" * 32),
               dict(task(), payload={}), dict(task(), arguments=[])]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(relay.RelayError):
                relay.normalize_task(value)

    def test_origin_rules_require_https_site_and_literal_loopback_http(self):
        self.assertEqual(relay.normalize_origin("https://fm1.example/", site=True), "https://fm1.example")
        self.assertEqual(relay.normalize_origin("http://127.0.0.1:9770", site=False), "http://127.0.0.1:9770")
        self.assertEqual(relay.normalize_origin("http://[::1]:9770", site=False), "http://[::1]:9770")
        self.assertEqual(relay.normalize_origin("https://bench.tailnet.ts.net", site=False), "https://bench.tailnet.ts.net")
        values = [("http://fm1.example", True), ("http://localhost:9770", False),
                  ("http://127.0.0.1.evil.example:9770", False), ("http://192.168.1.2", False),
                  ("https://public.example", False), ("https://user:secret@fm1.example", True),
                  ("https://fm1.example/tools", True), ("https://fm1.example?token=x", True),
                  ("https://fm1.example#part", True), ("https://fm1.example:0", True),
                  ("https://fm1.example\\@evil.example", True), ("https://fm1.example\n", True)]
        for value, site in values:
            with self.subTest(value=value), self.assertRaises(relay.RelayError):
                relay.normalize_origin(value, site=site)

    def test_json_rejects_duplicate_keys_nonfinite_and_oversize(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                    b"x" * (relay.MAX_JSON_BYTES + 1)):
            with self.assertRaises(relay.RelayError):
                relay.parse_json(raw)

    def test_token_sources_reject_missing_newline_and_oversized_tokens(self):
        with patch.dict(os.environ, {"FM1_TEST_TOKEN": RELAY_TOKEN}):
            self.assertEqual(relay.load_token("FM1_TEST_TOKEN", None), RELAY_TOKEN)
        for value in (None, "short", RELAY_TOKEN + "\r\nInjection", "x" * 4097):
            with self.assertRaises(relay.RelayError):
                relay.validate_token(value)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.token"
            path.write_text(RELAY_TOKEN)
            path.chmod(0o600)
            self.assertEqual(relay.load_token("FM1_TEST_TOKEN", path), RELAY_TOKEN)

    def test_recursive_projection_removes_bytes_paths_payloads_and_credentials(self):
        metadata = {"engine": {"blocked_unknown": True}, "id": "a" * 32, "status": "unknown",
                    "image": "raw-image", "firmwareBlob": "raw-firmware", "accessToken": RELAY_TOKEN,
                    "nested": [{"path": "F:\\private\\x", "title": "safe", "note": BRIDGE_TOKEN,
                                "unexpected": b"firmware", "file_name": "secret.bin"}],
                    "message": "Failure in C:\\private\\session.json", "encoded": "A" * 200,
                    "baseline_sha256": "a" * 64,
                    "session": {"blocked": True, "root": "F:\\secret", "loader_running": False},
                    "description": "NES offline variant"}
        result = relay.metadata_only(metadata, (RELAY_TOKEN, SITES_TOKEN, BRIDGE_TOKEN))
        raw = relay.json_bytes(result)
        for private in (b"raw-image", b"raw-firmware", b"private", b"secret", BRIDGE_TOKEN.encode(), RELAY_TOKEN.encode()):
            self.assertNotIn(private, raw)
        self.assertEqual(result["status"], "unknown")
        self.assertTrue(result["session"]["blocked"])
        self.assertEqual(result["nested"], [{"title": "safe"}])
        self.assertEqual(result["baseline_sha256"], "a" * 64)

    def test_recursive_projection_removes_physical_identifiers_preserving_inventory(self):
        identifiers = {key: "synthetic-unique-identity" for key in (
            "serial_number", "SerialNumber", "SERIAL_NUMBER", "serial_no",
            "device_serial_number", "usb_serial_number", "PNPDeviceID",
            "pnp_device_id", "PNP_DEVICE_ID", "pnp_id", "device_instance_id",
            "hardware_id", "hardware_ids", "physical_device_id",
            "device_unique_id", "device_uuid")}
        inventory = {"serial_ports": [{"port": "COM7", "vid": 0x3654,
            "pid": 0x5155, "description": "Synthetic FM1 serial port", **identifiers}],
            "uboot_disks": [{"Model": "WL82 UBOOT1.00 USB Device", **identifiers}],
            "session_configured": True, "device_io": False, "blocked": True}
        result = relay.metadata_only({"device": inventory})
        self.assertEqual(result, {"device": {
            "serial_ports": [{"port": "COM7", "vid": 0x3654, "pid": 0x5155,
                              "description": "Synthetic FM1 serial port"}],
            "uboot_disks": [{"Model": "WL82 UBOOT1.00 USB Device"}],
            "session_configured": True, "device_io": False, "blocked": True}})
        self.assertNotIn(b"synthetic-unique-identity", relay.json_bytes(result))


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name) / "relay-state"
        self.bridge, self.site = FakeBridge(), FakeSite()
        self.relay = relay.Relay(self.root, self.site, self.bridge,
                                 secrets=(RELAY_TOKEN, SITES_TOKEN, BRIDGE_TOKEN))

    def tearDown(self):
        self.relay.close()
        self.folder.cleanup()

    def restart(self, **fields):
        self.relay.close()
        self.relay = relay.Relay(self.root, self.site, self.bridge, **fields)

    def test_metadata_routes_are_fixed_and_job_status_is_authoritative(self):
        job_id = uuid.uuid4().hex
        self.bridge.jobs[job_id] = envelope(job_id, "unknown", operation="switch_app")
        for value in (task("status"), task("catalog"), task("job", job_id=job_id)):
            result = self.relay.handle_task(value)
            self.assertEqual(result["status"], "succeeded")
        self.assertEqual(self.bridge.calls, [("GET", "/v1/status", None), ("GET", "/v1/catalog", None),
                                            ("GET", "/v1/jobs/" + job_id, None)])
        self.assertEqual(result["data"]["status"], "unknown")

    def test_normalized_task_is_persisted_as_executing_before_submission(self):
        value = task("plan_app", catalog_id="nes-test")
        def inspect(method, route, body):
            record = self.relay._load(value["id"])
            self.assertEqual(record["task"], value)
            self.assertEqual(record["phase"], "executing")
        self.bridge.hook = inspect
        result = self.relay.handle_task(value)
        self.assertEqual(result["data"]["id"], value["id"])
        self.assertEqual(self.bridge.calls, [("POST", "/v1/jobs", {"id": value["id"], "operation": "plan_app", "catalog_id": "nes-test"})])

    def test_duplicate_and_restart_use_cached_result_without_repost(self):
        value = task("plan_app", catalog_id="nes-test")
        first = self.relay.handle_task(value)
        self.assertEqual(self.relay.handle_task(value), first)
        self.restart()
        self.assertEqual(self.relay.handle_task(value), first)
        self.assertEqual(len(self.bridge.calls), 1)

    def test_conflicting_task_id_never_executes_second_request(self):
        value = task("plan_app", catalog_id="nes-test")
        self.relay.handle_task(value)
        with self.assertRaisesRegex(relay.RelayError, "task_id_conflict"):
            self.relay.handle_task(task("plan_app", identifier=value["id"], catalog_id="doom-test"))
        self.assertEqual(len(self.bridge.calls), 1)

    def test_lost_submission_reply_queries_original_id_once(self):
        value = task("plan_app", catalog_id="nes-test")
        self.bridge.post_error = relay.RelayError("network_unavailable")
        result = self.relay.handle_task(value)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["data"]["status"], "queued")
        self.assertEqual([(method, route) for method, route, _ in self.bridge.calls],
                         [("POST", "/v1/jobs"), ("GET", "/v1/jobs/" + value["id"])])

    def test_lost_submission_and_missing_receipt_remain_unknown(self):
        value = task("plan_app", catalog_id="nes-test")
        self.bridge.post_error = relay.RelayError("network_unavailable")
        self.bridge.get_error = relay.RelayError("http_rejected", 404)
        result = self.relay.handle_task(value)
        self.assertEqual(result, {"id": value["id"], "status": "unknown", "error": "bridge_outcome_unknown"})
        self.restart()
        self.assertEqual(self.relay.handle_task(value), result)
        self.assertEqual(len(self.bridge.calls), 2)

    def test_restart_of_executing_job_only_queries_saved_id_even_if_switch_disabled(self):
        value = task("switch_app", catalog_id="nes-test", entry_method="already_uboot", expected_sha256=EXPECTED_SHA,
                     approval_expires=int(time.time()) - 1)
        self.relay._prepare(value)
        record = self.relay._load(value["id"])
        record["phase"] = "executing"
        relay.atomic_json(self.relay._path(value["id"]), record)
        self.bridge.jobs[value["id"]] = envelope(value["id"], "failed")
        self.restart()
        result = self.relay.handle_task(value)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["data"]["status"], "failed")
        self.assertEqual(self.bridge.calls, [("GET", "/v1/jobs/" + value["id"], None)])

    def test_executing_record_without_bridge_job_cannot_be_resubmitted(self):
        value = task("plan_app", catalog_id="nes-test")
        self.relay._prepare(value)
        record = self.relay._load(value["id"])
        record["phase"] = "executing"
        relay.atomic_json(self.relay._path(value["id"]), record)
        self.restart()
        result = self.relay.handle_task(value)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(self.bridge.calls, [("GET", "/v1/jobs/" + value["id"], None)])

    def test_switch_requires_deliberate_local_enable(self):
        disabled = task("switch_app", catalog_id="nes-test", entry_method="serial", expected_sha256=EXPECTED_SHA,
                        approval_expires=int(time.time()) + 120)
        self.assertEqual(self.relay.handle_task(disabled)["error"], "switch_disabled")
        self.assertEqual(self.bridge.calls, [])
        self.restart(allow_switch=True)
        enabled = task("switch_app", catalog_id="nes-test", entry_method="already_uboot", expected_sha256=EXPECTED_SHA,
                       approval_expires=int(time.time()) + 120)
        self.assertEqual(self.relay.handle_task(enabled)["status"], "succeeded")
        self.assertEqual(self.bridge.calls[1][2]["entry_method"], "already_uboot")
        self.assertEqual(set(self.bridge.calls[1][2]), {"id", "operation", "catalog_id", "entry_method"})

    def test_switch_rechecks_exact_approved_digest_and_readiness_before_submission(self):
        self.restart(allow_switch=True)
        fixtures = [({"apps": []}, "catalog_digest_mismatch"),
                    ({"apps": [{"variants": [{"id": "nes-test", "sha256": "d" * 64, "ready": True}]}]}, "catalog_digest_mismatch"),
                    ({"apps": [{"variants": [{"id": "nes-test", "ready": True}]}]}, "catalog_digest_mismatch"),
                    ({"apps": [{"variants": [{"id": "nes-test", "sha256": EXPECTED_SHA, "ready": False}]}]}, "catalog_not_ready")]
        for catalog, label in fixtures:
            self.bridge.catalog = catalog
            value = task("switch_app", catalog_id="nes-test", entry_method="serial", expected_sha256=EXPECTED_SHA,
                         approval_expires=int(time.time()) + 120)
            result = self.relay.handle_task(value)
            self.assertEqual(result["error"], label)
            self.assertEqual(self.relay._load(value["id"])["task"]["arguments"]["expected_sha256"], EXPECTED_SHA)
        self.assertTrue(all(method == "GET" and route == "/v1/catalog" for method, route, _ in self.bridge.calls))

    def test_switch_task_requires_a_valid_approved_digest(self):
        for args in ({}, {"expected_sha256": "invalid"}, {"expected_sha256": "D" * 64}):
            with self.assertRaises(relay.RelayError):
                self.relay.handle_task(task("switch_app", catalog_id="nes-test", entry_method="serial",
                                           approval_expires=int(time.time()) + 120, **args))
        self.assertEqual(self.bridge.calls, [])

    def test_prepared_switch_approval_expiration_prevents_submission_after_restart(self):
        value = task("switch_app", catalog_id="nes-test", entry_method="serial", expected_sha256=EXPECTED_SHA,
                     approval_expires=100)
        self.relay._prepare(value)
        self.restart(allow_switch=True)
        with patch.object(relay.time, "time", return_value=101):
            result = self.relay.handle_task(value)
        self.assertEqual(result["error"], "approval_expired")
        self.assertEqual(self.bridge.calls, [])

    def test_approval_is_rechecked_after_catalog_lookup_immediately_before_post(self):
        self.restart(allow_switch=True)
        value = task("switch_app", catalog_id="nes-test", entry_method="serial", expected_sha256=EXPECTED_SHA,
                     approval_expires=100)
        with patch.object(relay.time, "time", side_effect=[99, 100]):
            result = self.relay.handle_task(value)
        self.assertEqual(result["error"], "approval_expired")
        self.assertEqual(self.bridge.calls, [("GET", "/v1/catalog", None)])

    def test_switch_approval_expiry_is_a_required_integer_timestamp(self):
        for expiry in (None, True, 100.5, "100", 0, 2 ** 53):
            args = {} if expiry is None else {"approval_expires": expiry}
            with self.assertRaises(relay.RelayError):
                self.relay.handle_task(task("switch_app", catalog_id="nes-test", entry_method="serial",
                                           expected_sha256=EXPECTED_SHA, **args))
        self.assertEqual(self.bridge.calls, [])

    def test_metadata_projection_has_journal_headroom_and_stable_cached_receipt(self):
        self.bridge.metadata = {"id": "d" * 32, "status": "unknown",
            "engine": {"blocked_unknown": True, "unknown_jobs": [uuid.uuid4().hex for _ in range(400)]},
            "lots": ["descriptive metadata " * 20 for _ in range(400)]}
        value = task()
        first = self.relay.handle_task(value)
        self.assertLess(len(relay.json_bytes(first)), relay.MAX_METADATA_BYTES)
        self.assertTrue(first["data"]["metadata_truncated"])
        self.assertTrue(first["data"]["engine"]["blocked_unknown"])
        self.assertEqual(first, self.relay.handle_task(value))

    def test_site_result_requires_exact_saved_ack_before_marking_reported(self):
        value = task()
        result = self.relay.handle_task(value)
        self.site.request = lambda *_: {"ok": True}
        with self.assertRaisesRegex(relay.RelayError, "invalid_result_acknowledgment"):
            self.relay.report(result)
        self.assertFalse(self.relay._load(value["id"])["reported"])

    def test_known_bridge_rejection_is_fixed_failure_without_private_text(self):
        self.bridge.post_error = relay.RelayError(BRIDGE_TOKEN + " C:\\secret", 409)
        result = self.relay.handle_task(task("plan_app", catalog_id="nes-test"))
        self.assertEqual(result["error"], "bridge_request_rejected")
        self.assertNotIn(BRIDGE_TOKEN, json.dumps(result))
        self.assertEqual(len(self.bridge.calls), 1)

    def test_invalid_job_metadata_after_submit_is_queried_and_never_reposted(self):
        value = task("plan_app", catalog_id="nes-test")
        def malformed(method, route, body):
            self.bridge.calls.append((method, route, body))
            return envelope(uuid.uuid4().hex)
        self.bridge.request = malformed
        result = self.relay.handle_task(value)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual([call[0] for call in self.bridge.calls], ["POST", "GET"])

    def test_lost_site_result_ack_resumes_cached_result_after_restart(self):
        value = task("plan_app", catalog_id="nes-test")
        self.site.tasks = [value]
        self.site.result_error = relay.RelayError("network_unavailable")
        with self.assertRaises(relay.RelayError):
            self.relay.run_once()
        self.assertEqual(len(self.bridge.calls), 1)
        self.restart()
        self.site.result_error = None
        self.relay.run_once()
        self.assertTrue(self.relay._load(value["id"])["reported"])
        self.assertEqual(len(self.bridge.calls), 1)
        results = [body for _, route, body in self.site.calls if route == "/relay/result"]
        self.assertEqual(results[0], results[1])

    def test_entire_poll_batch_is_persisted_before_first_result_report(self):
        first, second = task("status"), task("plan_app", catalog_id="nes-test")
        self.site.tasks = [first, second]
        self.site.result_error = relay.RelayError("network_unavailable")
        with self.assertRaises(relay.RelayError):
            self.relay.run_once()
        self.assertEqual(self.relay._load(second["id"])["phase"], "prepared")
        self.site.result_error = None
        self.restart()
        self.relay.run_once()
        self.assertEqual([call[0] for call in self.bridge.calls], ["GET", "POST"])

    def test_idle_heartbeat_reports_switch_disabled_without_bridge_io(self):
        self.assertEqual(self.relay.run_once(), 0)
        self.assertEqual(self.site.calls, [("POST", "/relay/heartbeat", {"allow_switch": False}),
                                          ("POST", "/relay/poll", {})])
        self.assertEqual(self.bridge.calls, [])

    def test_poll_validation_happens_before_any_bridge_call(self):
        for values in ([task(), task("reset")], [task(identifier="b" * 32)] * 2):
            self.site.tasks = values
            with self.assertRaises(relay.RelayError):
                self.relay.run_once()
        self.assertEqual(self.bridge.calls, [])

    def test_private_metadata_never_reaches_site_or_journal(self):
        self.bridge.metadata = {"status": "unknown", "image": "x" * 1000,
            "firmware": "x" * 1000, "path": "C:\\private", "message": BRIDGE_TOKEN,
            "safe": True}
        self.site.tasks = [task()]
        self.relay.run_once()
        result = [body for _, route, body in self.site.calls if route == "/relay/result"][0]
        self.assertEqual(result["data"], {"status": "unknown", "safe": True})
        for path in self.relay.tasks_dir.glob("*.json"):
            raw = path.read_bytes()
            self.assertNotIn(BRIDGE_TOKEN.encode(), raw)
            self.assertNotIn(b"private", raw)

    def test_physical_identifiers_never_reach_site_result_or_journal(self):
        self.bridge.metadata = {"engine": {"blocked_unknown": True}, "device": {
            "serial_ports": [{"port": "COM7", "serial_number": "synthetic-unit-serial"}],
            "uboot_disks": [{"Model": "WL82 UBOOT1.00 USB Device",
                             "PNPDeviceID": "synthetic-unit-pnp-identity"}],
            "device_io": False}}
        value = task()
        self.site.tasks = [value]
        self.relay.run_once()
        result = [body for _, route, body in self.site.calls if route == "/relay/result"][0]
        self.assertEqual(result["data"]["device"]["serial_ports"], [{"port": "COM7"}])
        self.assertEqual(result["data"]["device"]["uboot_disks"], [{"Model": "WL82 UBOOT1.00 USB Device"}])
        self.assertTrue(result["data"]["engine"]["blocked_unknown"])
        for raw in (relay.json_bytes(result), self.relay._path(value["id"]).read_bytes()):
            self.assertNotIn(b"synthetic-unit-serial", raw)
            self.assertNotIn(b"synthetic-unit-pnp-identity", raw)

    def test_task_cannot_copy_configured_credentials_into_private_journal(self):
        token = "e" * 64
        self.restart(secrets=(token,))
        with self.assertRaisesRegex(relay.RelayError, "invalid_task"):
            self.relay.handle_task(task("plan_app", catalog_id=token))
        self.assertEqual(list(self.relay.tasks_dir.glob("*.json")), [])
        self.assertEqual(self.bridge.calls, [])

    def test_corrupt_journal_blocks_start_instead_of_forgetting_old_submission(self):
        value = task("plan_app", catalog_id="nes-test")
        self.relay.handle_task(value)
        self.relay.close()
        self.relay._path(value["id"]).write_text('{"broken":true}')
        with self.assertRaisesRegex(relay.RelayError, "invalid_relay_state"):
            relay.Relay(self.root, self.site, self.bridge)

    def test_another_process_cannot_own_same_state(self):
        script = ('import sys\nfrom pathlib import Path\nimport site_relay as r\n'
                  'try:\n x=r.Relay(Path(sys.argv[1]),None,None)\n'
                  'except r.RelayError as e:\n print(e.label)\n'
                  'else:\n x.close(); raise SystemExit("unexpected owner")\n')
        result = subprocess.run([sys.executable, "-c", script, str(self.root)],
            cwd=Path(__file__).parent, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("relay_state_already_owned", result.stdout)


class HttpTransportTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.payload = b'{"ok":true,"data":{"device_io":false}}'
        self.code = 200
        self.content_type = "application/json"
        self.length_extra = 0
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_GET(self):
                owner.requests.append((self.path, dict(self.headers)))
                self.send_response(owner.code)
                self.send_header("Content-Type", owner.content_type)
                self.send_header("Content-Length", str(len(owner.payload) + owner.length_extra))
                if owner.code == 302:
                    self.send_header("Location", "/credential-sink")
                self.end_headers()
                self.wfile.write(owner.payload)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = "http://127.0.0.1:" + str(self.server.server_address[1])
        self.client = relay.JsonClient(self.origin, {"Authorization": "Bearer " + BRIDGE_TOKEN})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def test_authenticated_fixed_origin_json(self):
        self.assertFalse(self.client.request("GET", "/v1/status")["data"]["device_io"])
        self.assertEqual(self.requests[0][1]["Authorization"], "Bearer " + BRIDGE_TOKEN)
        self.assertNotIn("Oai-Sites-Authorization", self.requests[0][1])

    def test_redirect_is_rejected_without_sending_auth_to_redirect_target(self):
        self.code = 302
        with self.assertRaisesRegex(relay.RelayError, "redirect_rejected"):
            self.client.request("GET", "/v1/status")
        self.assertEqual(len(self.requests), 1)

    def test_response_bounds_type_duplicate_keys_and_nonfinite_numbers(self):
        for payload, content_type in ((b"x" * (relay.MAX_JSON_BYTES + 1), "application/json"),
                                     (b'{}', "application/octet-stream"),
                                     (b'{"ok":true,"ok":false}', "application/json"),
                                     (b'{"x":NaN}', "application/json")):
            self.payload, self.content_type = payload, content_type
            with self.assertRaises(relay.RelayError):
                self.client.request("GET", "/v1/status")

    def test_route_cannot_change_origin_or_add_private_download(self):
        for route in ("//evil.example", "https://evil.example", "/v1/status?token=secret", "/a\\b"):
            with self.assertRaises(relay.RelayError):
                self.client.request("GET", route)
        self.assertEqual(self.requests, [])

    def test_lost_http_body_produces_fixed_network_error(self):
        self.length_extra = 20
        with self.assertRaisesRegex(relay.RelayError, "network_unavailable"):
            self.client.request("GET", "/v1/status")

    def test_main_uses_separate_site_credentials_and_logs_only_fixed_errors(self):
        clients = []
        def factory(origin, headers):
            clients.append((origin, headers))
            return FakeSite() if origin == "https://fm1.example" else FakeBridge()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
                "FM1_RELAY_TOKEN": RELAY_TOKEN, "FM1_SITES_SERVICE_TOKEN": SITES_TOKEN,
                "FM1_BRIDGE_TOKEN": BRIDGE_TOKEN}), patch.object(relay, "JsonClient", factory):
            self.assertEqual(relay.main(["--site-url", "https://fm1.example", "--state-dir", folder, "--once"]), 0)
        self.assertEqual(clients, [("https://fm1.example", {"Authorization": "Bearer " + RELAY_TOKEN,
                "OAI-Sites-Authorization": "Bearer " + SITES_TOKEN}),
                ("http://127.0.0.1:9770", {"Authorization": "Bearer " + BRIDGE_TOKEN})])
        output = io.StringIO()
        with patch.object(relay, "load_token", side_effect=relay.RelayError("credential_unavailable")), patch("sys.stderr", output):
            self.assertEqual(relay.main(["--site-url", "https://fm1.example", "--state-dir", "unused"]), 1)
        self.assertEqual(output.getvalue(), "FM1 relay: credential_unavailable\n")


if __name__ == "__main__":
    unittest.main()
