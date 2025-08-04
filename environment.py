from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from docker import from_env, errors

CLIENT = from_env()
BASE_DIRECTORY = "/tmp"
DEFAULT_CONTAINER_NETWORK = "nexus-net"


class Images(StrEnum):
    REVERSE_PROXY = "d3lta12/nexus-reverse-proxy"
    STATIC_HOST = "d3lta12/nexus-static-host"


class Environment(ABC):
    def __init__(
        self,
        name: str = "",
        working_directory: str = BASE_DIRECTORY,
        variables: dict = {},
    ) -> None:
        self.variables = {}
        self.set_name(name)
        self.set_working_directory(working_directory)
        self.set_variables(variables)

    def set_name(self, name: str) -> None:
        self.name = name

    def get_name(self) -> str | None:
        return self.name

    def set_working_directory(self, working_directory: str) -> None:
        self.working_directory = working_directory

    def get_working_directory(self) -> str:
        return self.working_directory

    def set_variable(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def set_variables(self, variables: dict) -> None:
        for name, value in variables.items():
            self.set_variable(name, value)

    def get_variable(self, name: str) -> Any:
        value = None
        if name in self.variables:
            value = self.variables[name]
        return value

    def run_command(self, command: str) -> tuple[int, str]:
        return self.run_commands([command])

    @abstractmethod
    def run_commands(self, commands: list[str]) -> tuple[int, str]:
        return 0, ""


class ContainerEnvironment(Environment):
    def __init__(
        self,
        container_name: str = "",
        container_image: str = Images.STATIC_HOST,
        container_network: str = DEFAULT_CONTAINER_NETWORK,
        container_ports: dict = {},
        working_directory: str = BASE_DIRECTORY,
        variables: dict = {},
    ) -> None:
        super().__init__(working_directory=working_directory, variables=variables)
        try:
            self.container = CLIENT.containers.get(container_name)
        except (errors.NotFound, errors.NullResource):
            self.container = CLIENT.containers.run(
                container_image, ports=container_ports, detach=True
            )
        self.set_name(container_name)
        if len(container_network) > 0:
            networks = CLIENT.networks.list(names=[container_network])
            if 0 == len(networks):
                network = CLIENT.networks.create(container_network)
            else:
                network = networks[0]
            network.reload()
            if self.container not in network.containers:
                network.connect(self.container)

    def set_name(self, name: str) -> None:
        if "" != name and self.container.name != name:
            self.name = name
            self.container.rename(self.name)
            self.container.reload()
            super().set_name(name)

    def get_name(self) -> str | None:
        return self.container.name

    def run_commands(self, commands: list[str]) -> tuple[int, str]:
        exit_code = 0
        output = b""
        for command in commands:
            exit_code, output = self.container.exec_run(
                command,
                workdir=(
                    self.working_directory if len(self.working_directory) > 0 else None
                ),
                environment=self.variables,
            )
            if 0 != exit_code:
                break
        return exit_code, output.decode()
