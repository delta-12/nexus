from collections import deque

from environment import Environment
from steps import Step


class Deployment:
    def __init__(self, environment: Environment, name: str = "") -> None:
        self.steps = deque()
        self.environment = environment
        self.environment.set_name(name)

    def add_step(self, step: Step) -> None:
        self.steps.appendleft(step)

    def add_steps(self, steps: list[Step]) -> None:
        self.steps.extendleft(steps)

    def run_next_step(self) -> tuple[int, str]:
        step = self.steps.pop()
        exit_code, output = step.run(self.environment)
        self.add_steps(step.get_next_steps())
        return exit_code, output

    def run_all_steps(self) -> tuple[int, str]:
        exit_code = 0
        output = ""
        while self.steps:
            exit_code, output = self.run_next_step()
            if 0 != exit_code:
                break
        return exit_code, output
