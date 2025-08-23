from collections import deque
import sqlite3

from environment import Environment, ContainerEnvironment
from steps import Step, Properties

DATABASE_NAME = "nexus.db"


class Deployment:
    def __init__(self, environment: Environment, name: str = "") -> None:
        self.steps = deque()
        self.environment = environment
        self.environment.set_name(name)
        self.properties = {}
        self.id = None

    def get_property(self, property: str) -> str | None:
        value = None
        if Properties.NAME == property:
            value = self.environment.get_name()
        elif property in self.properties:
            value = self.properties[property]
        return value

    def set_properties(self, properties: dict) -> None:
        for property, value in properties.items():
            if property in Properties:
                self.properties[property] = value

    def save(self) -> None:
        with sqlite3.connect(DATABASE_NAME) as database:
            cursor = database.cursor()
            cursor.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS deployments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        {Properties.NAME} TEXT UNIQUE,
                        {Properties.DOMAIN} TEXT UNIQUE,
                        {Properties.EMAIL} TEXT,
                        environment TEXT
                    )
                """
            )
            if self.id is None:
                cursor.execute("INSERT INTO deployments DEFAULT VALUES")
                self.id = cursor.lastrowid
            cursor.execute(
                f"""
                    UPDATE deployments
                    SET {Properties.NAME} = ?, environment = ?
                    WHERE id = ?
                """,
                (
                    self.get_property(Properties.NAME),
                    type(self.environment).__name__,
                    self.id,
                ),
            )
            for property, value in self.properties.items():
                cursor.execute(
                    f"""
                        UPDATE deployments
                        SET {property} = ?
                        WHERE id = ?
                    """,
                    (value, self.id),
                )
            database.commit()

    def delete(self) -> None:
        with sqlite3.connect(DATABASE_NAME) as database:
            cursor = database.cursor()
            cursor.execute(
                f"""
                    DELETE FROM deployments
                    WHERE name = ?
                """,
                (self.get_property(Properties.NAME),),
            )
            database.commit()

    def add_step(self, step: Step) -> None:
        self.steps.appendleft(step)

    def add_steps(self, steps: list[Step]) -> None:
        self.steps.extendleft(steps)

    def run_next_step(self) -> tuple[int, str]:
        step = self.steps.pop()
        exit_code, output = step.run(self.environment)
        self.add_steps(step.get_next_steps())
        self.set_properties(step.get_properties())
        return exit_code, output

    def run_all_steps(self) -> tuple[int, str]:
        exit_code = 0
        output = ""
        while self.steps:
            exit_code, output = self.run_next_step()
            if 0 != exit_code:
                break
        return exit_code, output


def get_deployments() -> list[Deployment]:
    deployments = []
    with sqlite3.connect(DATABASE_NAME) as database:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM deployments")
        for row in cursor.fetchall():
            environment_type = row[4]
            environment = None
            if ContainerEnvironment.__name__ == environment_type:
                environment = ContainerEnvironment(container_name=row[1])
            if environment is not None:
                deployment = Deployment(environment)
                deployment.set_properties(
                    {Properties.DOMAIN: row[2], Properties.EMAIL: row[3]}
                )  # TODO get properties by name from row instead of by index
                deployments.append(deployment)
    return deployments
