import unittest
from src.core.reflexion import ReflexionLoop, Memory


class TestMemory(unittest.TestCase):
    def test_store_and_retrieve(self):
        mem = Memory()
        mem.store("task1", "output1", "good")
        mem.store("task2", "output2", "bad")
        self.assertEqual(len(mem.feedback_history), 2)
        self.assertEqual(mem.get_last_feedback(), "bad")

    def test_empty_memory_returns_none(self):
        mem = Memory()
        self.assertIsNone(mem.get_last_feedback())


class TestReflexionLoop(unittest.TestCase):
    def test_first_attempt_succeeds(self):
        loop = ReflexionLoop(max_attempts=3)
        result = loop.run(
            "do thing",
            actor=lambda task: f"solved {task}",
            evaluator=lambda task, output: (True, "perfect"),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["attempts"], 1)

    def test_retry_until_success(self):
        loop = ReflexionLoop(max_attempts=5)
        attempt_counter = [0]

        def actor(task):
            attempt_counter[0] += 1
            return f"attempt_{attempt_counter[0]}"

        def evaluator(task, output):
            if "attempt_3" in output:
                return (True, "good enough")
            return (False, "try again")

        result = loop.run("test", actor, evaluator)
        self.assertTrue(result["success"])
        self.assertEqual(result["attempts"], 3)

    def test_all_attempts_fail(self):
        loop = ReflexionLoop(max_attempts=3)
        result = loop.run(
            "fail task",
            actor=lambda task: "bad output",
            evaluator=lambda task, output: (False, "always wrong"),
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["attempts"], 3)

    def test_memory_passed_between_attempts(self):
        memory = Memory()
        loop = ReflexionLoop(max_attempts=3, memory=memory)
        loop.run("task", lambda t: "x", lambda t, o: (True, "ok"))
        self.assertGreaterEqual(len(memory.feedback_history), 1)


class TestCoderAgentReflexion(unittest.TestCase):
    def test_reflexive_generate_creates_code(self):
        from src.agents.coder import CoderAgent
        import asyncio
        agent = CoderAgent()

        async def test():
            result = await agent.reflexive_generate("Calculate fibonacci numbers", "python")
            self.assertIn("code", result)
            self.assertIn("attempts", result)
            return result

        result = asyncio.run(test())
        self.assertGreater(len(result["code"]), 10)

    def test_reflexive_review_returns_feedback(self):
        from src.agents.coder import CoderAgent
        import asyncio
        agent = CoderAgent()

        async def test():
            bad_code = 'password = "secret123"\ndef main():\n    eval(user_input)\n'
            result = await agent.reflexive_review(bad_code)
            self.assertIn("success", result)
            return result

        result = asyncio.run(test())
        self.assertIsInstance(result["success"], bool)


if __name__ == "__main__":
    unittest.main()
