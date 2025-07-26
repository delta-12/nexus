from abc import ABC, abstractmethod
from collections import deque
from enum import StrEnum, auto
import logging
from tomllib import loads, TOMLDecodeError

from environment import Environment

LOGGER = logging.getLogger(__name__)


class HostFields(StrEnum):
    NAME = auto()
    DOMAIN = auto()


class SourceFields(StrEnum):
    BRANCH = auto()
    ROOT_DIRECTORY = auto()


class DeployFields(StrEnum):
    BUILD_COMMAND = auto()
    PUBLISH_DIRECTORY = auto()


class Step(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.exit_code = None
        self.output = None
        self.next_steps = deque()

    @abstractmethod
    def run_action(self, environment: Environment) -> tuple[int, str]:
        return -1, "Not implemented"

    # TODO getters

    def run(self, environment: Environment) -> tuple[int, str]:
        LOGGER.info(f"Step: {self.name}")
        exit_code, output = self.run_action(environment)
        if 0 != exit_code:
            LOGGER.error(
                f"Failure\nExit code: {exit_code}\nError message: {output}\nDirectory: {environment.get_working_directory()}"
            )
        else:
            LOGGER.info("Success")
        self.exit_code = exit_code
        self.output = output
        return exit_code, output


class SetWorkingDirectory(Step):
    def __init__(self, working_directory: str) -> None:
        super().__init__("Set Working Directory")
        self.working_directory = working_directory

    def run_action(self, environment: Environment) -> tuple[int, str]:
        environment.set_working_directory(self.working_directory)
        return 0, ""


class SetName(Step):
    def __init__(self, name: str) -> None:
        super().__init__("Set Name")
        self.name = name

    def run_action(self, environment: Environment) -> tuple[int, str]:
        environment.set_name(self.name)
        return 0, ""


class GitClone(Step):
    def __init__(self, repository: str) -> None:
        super().__init__("Git Clone")
        self.repository = repository

    def run_action(self, environment: Environment) -> tuple[int, str]:
        return environment.run_command(f"git clone {self.repository} .")


class GitCheckout(Step):
    def __init__(self, branch: str) -> None:
        super().__init__("Git Checkout")
        self.branch = branch

    def run_action(self, environment: Environment) -> tuple[int, str]:
        return environment.run_commands(
            [f"git fetch origin {self.branch}", f"git checkout {self.branch}"]
        )


class BuildSource(Step):
    def __init__(self, build_command: str) -> None:
        super().__init__("Build Source")
        self.build_command = build_command

    def run_action(self, environment: Environment) -> tuple[int, str]:
        return environment.run_command(f"sh -c '{self.build_command}'")


class ReadConfig(Step):
    def __init__(self, config_file: str) -> None:
        super().__init__("Read Config")
        self.config_file = config_file
        self.domain = None
        self.publish_directory = None

    def parse(self, config: dict, environment: Environment) -> tuple[int, str]:
        exit_code = 0
        output = ""
        if "host" in config:
            host = config["host"]
            if HostFields.NAME in host:
                self.next_steps.appendleft(SetName(host[HostFields.NAME]))
            if HostFields.DOMAIN in host:
                self.domain = host[HostFields.DOMAIN]
            else:
                # TODO set sub-domain based on name if domain not provide (e.g. subdomain.domain.toplevel)
                exit_code = -1
                output = "Missing domain"
        else:
            exit_code = -1
            output = "Missing host"

        if "source" in config and 0 == exit_code:
            source = config["source"]
            if SourceFields.BRANCH in source:
                self.next_steps.appendleft(GitCheckout(source[SourceFields.BRANCH]))
            if SourceFields.ROOT_DIRECTORY in source:
                self.next_steps.appendleft(
                    SetWorkingDirectory(source[SourceFields.ROOT_DIRECTORY])
                )

        if "deploy" in config and 0 == exit_code:
            deploy = config["deploy"]
            if DeployFields.BUILD_COMMAND in deploy:
                self.next_steps.appendleft(
                    BuildSource(deploy[DeployFields.BUILD_COMMAND])
                )
            if DeployFields.PUBLISH_DIRECTORY in deploy:
                self.publish_directory = deploy[DeployFields.PUBLISH_DIRECTORY]
            else:
                self.publish_directory = environment.get_working_directory()

        # TODO environment variable and secrets

        return exit_code, output

    def run_action(self, environment: Environment) -> tuple[int, str]:
        exit_code, output = environment.run_command(f"sh -c 'cat {self.config_file}'")

        if 0 != exit_code:
            output = f"Failed to read config file {self.config_file}"
        else:
            try:
                exit_code, output = self.parse(loads(output), environment)
                # TODO append step build nginx conf based on domain and publish directory
            except TOMLDecodeError:
                exit_code = -1
                output = f"Config file {self.config_file} is invalid"

        return exit_code, output
