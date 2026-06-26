from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class Memory:
    feedback_history: List[Dict[str, str]] = field(default_factory=list)

    def store(self, task: str, output: str, feedback: str) -> None:
        self.feedback_history.append({
            "task": task,
            "output": output,
            "feedback": feedback,
        })

    def get_last_feedback(self) -> Optional[str]:
        if not self.feedback_history:
            return None
        return self.feedback_history[-1]["feedback"]


class ReflexionLoop:
    def __init__(self, max_attempts: int = 3, memory: Optional[Memory] = None):
        self.max_attempts = max_attempts
        self.memory = memory or Memory()

    def run(self, task: str, actor: Callable, evaluator: Callable) -> dict:
        last_output = None
        last_feedback = None

        for attempt in range(1, self.max_attempts + 1):
            output = actor(task)
            success, feedback = evaluator(task, output)
            self.memory.store(task, output, feedback)
            last_output = output
            last_feedback = feedback

            if success:
                return {
                    "success": True,
                    "attempts": attempt,
                    "output": output,
                    "feedback": feedback,
                }

        return {
            "success": False,
            "attempts": self.max_attempts,
            "output": last_output,
            "feedback": last_feedback,
        }
