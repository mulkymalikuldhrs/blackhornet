"""Tests for RPCPipeline (Hermes Agent subagent RPC pipeline)."""

import unittest

from src.colony.orchestration.rpc_pipeline import RPCPipeline, RPCRequest, RPCResponse, RPCMethod


class TestRPCMethod(unittest.TestCase):
    def test_has_expected_methods(self):
        self.assertIn(RPCMethod.EXECUTE, RPCMethod)
        self.assertIn(RPCMethod.QUERY, RPCMethod)
        self.assertIn(RPCMethod.STATUS, RPCMethod)
        self.assertIn(RPCMethod.CANCEL, RPCMethod)


class TestRPCRequest(unittest.TestCase):
    def test_auto_generates_request_id(self):
        req = RPCRequest(method=RPCMethod.QUERY)
        self.assertTrue(req.request_id.startswith("rpc-"))

    def test_preserves_provided_request_id(self):
        req = RPCRequest(method=RPCMethod.EXECUTE, request_id="my-id")
        self.assertEqual(req.request_id, "my-id")


class TestRPCResponse(unittest.TestCase):
    def test_error_response(self):
        resp = RPCResponse(request_id="r1", success=False, error="fail")
        self.assertFalse(resp.success)
        self.assertEqual(resp.error, "fail")

    def test_success_response(self):
        resp = RPCResponse(request_id="r2", success=True, result={"ok": True})
        self.assertTrue(resp.success)
        self.assertEqual(resp.result, {"ok": True})


class TestRPCPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = RPCPipeline()

    def test_register_and_process_handler(self):
        self.pipeline.register_handler(RPCMethod.EXECUTE, lambda cmd: f"executed {cmd}")
        req = RPCRequest(method=RPCMethod.EXECUTE, params={"cmd": "ls"})
        resp = self.pipeline.process_request(req)
        self.assertTrue(resp.success)
        self.assertEqual(resp.result, "executed ls")

    def test_no_handler_returns_error(self):
        req = RPCRequest(method=RPCMethod.QUERY)
        resp = self.pipeline.process_request(req)
        self.assertFalse(resp.success)
        self.assertIn("No handler", resp.error)

    def test_handler_exception_returns_error(self):
        def handler(*args, **kwargs):
            raise ValueError("boom")

        self.pipeline.register_handler(RPCMethod.EXECUTE, handler)
        req = RPCRequest(method=RPCMethod.EXECUTE)
        resp = self.pipeline.process_request(req)
        self.assertFalse(resp.success)
        self.assertIn("boom", resp.error)

    def test_send_request_stores_pending(self):
        req = RPCRequest(method=RPCMethod.STATUS)
        req_id = self.pipeline.send_request(req)
        self.assertIn(req_id, self.pipeline.pending)

    def test_get_response_returns_stored(self):
        req = RPCRequest(method=RPCMethod.EXECUTE)
        self.pipeline.results[req.request_id] = RPCResponse(request_id=req.request_id, success=True, result="done")
        resp = self.pipeline.get_response(req.request_id)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.result, "done")

    def test_get_response_missing_returns_none(self):
        resp = self.pipeline.get_response("nonexistent")
        self.assertIsNone(resp)

    def test_cleanup_clears_pending(self):
        req = RPCRequest(method=RPCMethod.EXECUTE)
        self.pipeline.send_request(req)
        self.pipeline.cleanup()
        self.assertEqual(len(self.pipeline.pending), 0)

    def test_process_request_stores_result(self):
        self.pipeline.register_handler(RPCMethod.EXECUTE, lambda: 42)
        req = RPCRequest(method=RPCMethod.EXECUTE)
        self.pipeline.process_request(req)
        self.assertIn(req.request_id, self.pipeline.results)


if __name__ == "__main__":
    unittest.main()
