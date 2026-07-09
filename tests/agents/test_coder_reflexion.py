"""Tests for CoderAgent Reflexion integration."""
import unittest
import asyncio


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

    def test_reflexive_generate_with_spec(self):
        from src.agents.coder import CoderAgent
        import asyncio

        agent = CoderAgent()

        async def test():
            result = await agent.reflexive_generate(
                "Create a class for managing user sessions with login and logout",
                "python"
            )
            self.assertIn("code", result)
            self.assertIn("attempts", result)
            self.assertIn("success", result)
            return result

        result = asyncio.run(test())
        self.assertIsInstance(result["attempts"], int)
        self.assertGreaterEqual(result["attempts"], 1)

    def test_reflexion_history_tracked(self):
        from src.agents.coder import CoderAgent
        import asyncio

        agent = CoderAgent()

        async def test():
            result = await agent.reflexive_generate("simple task", "python")
            self.assertIn("reflexion_history", result)
            history = result["reflexion_history"]
            self.assertIsInstance(history, list)
            return result

        result = asyncio.run(test())
        self.assertIsInstance(result["reflexion_history"], list)

    def test_generate_with_reflexion_action(self):
        from src.agents.coder import CoderAgent
        from src.colony_types import Task
        import asyncio

        agent = CoderAgent()

        async def test():
            task = Task(
                description="Write a simple calculator function",
                payload={"action": "generate_with_reflexion", "language": "python"}
            )
            result = await agent._generate_with_reflexion(task)
            self.assertIn("action", result)
            self.assertIn("code", result)
            self.assertIn("attempts", result)
            return result

        result = asyncio.run(test())
        self.assertEqual(result["action"], "generate_with_reflexion")


if __name__ == "__main__":
    unittest.main()