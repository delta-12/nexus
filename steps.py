from abc import ABC, abstractmethod
from enum import StrEnum, auto
import logging
from tomllib import loads, TOMLDecodeError

from environment import Environment

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_FILE = "nexus.toml"
BASE_CERTIFICATE_PATH = "/etc/letsencrypt/live/"
DEFAULT_CERTIFICATE_NAME = "nexus"


class HostFields(StrEnum):
    NAME = auto()
    DOMAIN = auto()
    EMAIL = auto()


class SourceFields(StrEnum):
    BRANCH = auto()
    ROOT_DIRECTORY = auto()


class DeployFields(StrEnum):
    BUILD_COMMAND = auto()
    PUBLISH_DIRECTORY = auto()


class Properties(StrEnum):
    NAME = auto()
    DOMAIN = auto()
    EMAIL = auto()


class Step(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.exit_code = None
        self.output = None
        self.next_steps = []
        self.properties = {}

    @abstractmethod
    def run_action(self, environment: Environment) -> tuple[int, str]:
        return -1, "Not implemented"

    # TODO getters

    def get_next_steps(self) -> list:
        return self.next_steps

    def get_properties(self) -> dict:
        return self.properties

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
        self.deploy_name = name

    def run_action(self, environment: Environment) -> tuple[int, str]:
        environment.set_name(self.deploy_name)
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


class BuildNginxStaticSiteConfig(Step):
    def __init__(self, config_file: str, domain: str, publish_directory: str) -> None:
        super().__init__("Build Nginx Static Site Config")
        self.config_file = config_file
        self.domain = domain
        self.publish_directory = publish_directory

    def run_action(self, environment: Environment) -> tuple[int, str]:
        config = (
            "server {\n"
            "\tlisten 80;\n\n"
            f"\tserver_name {self.domain} www.{self.domain};\n\n"
            f"\troot {self.publish_directory};\n"
            "}\n"
        )

        return environment.run_command(
            f"sh -c 'echo \"{config}\" > /etc/nginx/http.d/site.conf'"
        )


class BuildNginxReverseProxyConfig(Step):
    def __init__(
        self,
        domain: str,
        upstream: str,
        certificate_name: str = DEFAULT_CERTIFICATE_NAME,
    ) -> None:
        super().__init__("Build Nginx Reverse Proxy Config")
        self.domain = domain
        self.upstream = upstream
        self.path_to_certificate = (
            BASE_CERTIFICATE_PATH + certificate_name + "/fullchain.pem"
        )
        self.path_to_key = BASE_CERTIFICATE_PATH + certificate_name + "/privkey.pem"

    def run_action(self, environment: Environment) -> tuple[int, str]:
        config = (
            "server {\n"
            "\tlisten 443 ssl;\n"
            f"\tserver_name {self.domain} www.{self.domain};\n\n"
            f"\tssl_certificate {self.path_to_certificate};\n"
            f"\tssl_certificate_key {self.path_to_key};\n\n"
            "\tlocation / {\n"
            f"\t\tproxy_pass http://{self.upstream}:80;\n"
            "\t\tproxy_set_header   X-Forwarded-For $remote_addr;\n"
            "\t\tproxy_set_header   Host $http_host;\n"
            "\t}\n"
            "}\n\n"
            "server {\n"
            "\tlisten 80;\n"
            f"\tserver_name {self.domain} www.{self.domain};\n\n"
            "\treturn 301 https://$host$request_uri;\n"
            "}\n"
        )

        return environment.run_command(
            f"sh -c 'echo \"{config}\" > /etc/nginx/http.d/{self.domain}.conf'"
        )


class TestNginxConfig(Step):
    def __init__(self) -> None:
        super().__init__("Test Nginx Config")

    def run_action(self, environment: Environment) -> tuple[int, str]:
        return environment.run_command("nginx -t")


class ReloadNginx(Step):
    def __init__(self) -> None:
        super().__init__("Reload Nginx")

    def run_action(self, environment: Environment) -> tuple[int, str]:
        return environment.run_command("nginx -s reload")


class AddDomainToCertificate(Step):
    def __init__(
        self,
        domain: str,
        email: str,
        certificate_name: str = DEFAULT_CERTIFICATE_NAME,
    ) -> None:
        super().__init__("Add Domain to Certificate")
        self.domain = domain
        self.email = email
        self.certificate_name = certificate_name

    def run_action(self, environment: Environment) -> tuple[int, str]:
        domains_path = f"/etc/letsencrypt/live/{self.certificate_name}/domains.txt"
        exit_code, output = environment.run_command(
            f"sh -c'if [ ! -e {domains_path} ]; then echo \"\"; else cat {domains_path}; fi'"
        )
        if 0 != exit_code:
            pass
        elif self.domain in output.split(","):
            exit_code = -1
            output = "Domain already added to certificate"
        else:
            domains = output
            if 0 != len(domains):
                domains += ","
            domains += self.domain
            exit_code, output = environment.run_command(
                "sh -c 'certbot "
                "--agree-tos "
                f"-m {self.email} "
                "certonly "
                "--nginx "
                "--preferred-challenges http "
                f"-d {domains} "
                "--redirect "
                "--non-interactive "
                f"--cert-name {self.certificate_name}'"
            )

            if 0 == exit_code:
                exit_code, output = environment.run_command(
                    f"sh -c 'echo {domains} > {domains_path}'"
                )

        return exit_code, output


class ReadNexusConfig(Step):
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE) -> None:
        super().__init__("Read Nexus Config")
        self.config_file = config_file
        self.publish_directory = None

    def parse(self, config: dict, environment: Environment) -> tuple[int, str]:
        exit_code = 0
        output = ""
        if "host" in config:
            host = config["host"]
            if HostFields.NAME not in host:
                exit_code = -1
                output = "Missing name"
            elif HostFields.DOMAIN not in host:
                # TODO set sub-domain based on name if domain not provide (e.g. subdomain.domain.toplevel)
                exit_code = -1
                output = "Missing domain"
            elif HostFields.EMAIL not in host:
                exit_code = -1
                output = "Missing email"
            else:
                self.next_steps.append(SetName(host[HostFields.NAME]))
                self.properties[Properties.DOMAIN] = host[HostFields.DOMAIN]
                self.properties[Properties.EMAIL] = host[HostFields.EMAIL]
        else:
            exit_code = -1
            output = "Missing host"

        if "source" in config and 0 == exit_code:
            source = config["source"]
            if SourceFields.BRANCH in source:
                self.next_steps.append(GitCheckout(source[SourceFields.BRANCH]))
            if SourceFields.ROOT_DIRECTORY in source:
                self.next_steps.append(
                    SetWorkingDirectory(source[SourceFields.ROOT_DIRECTORY])
                )

        if "deploy" in config and 0 == exit_code:
            deploy = config["deploy"]
            if DeployFields.BUILD_COMMAND in deploy:
                self.next_steps.append(BuildSource(deploy[DeployFields.BUILD_COMMAND]))
            if DeployFields.PUBLISH_DIRECTORY in deploy:
                self.publish_directory = (
                    environment.get_working_directory()
                    + "/"
                    + deploy[DeployFields.PUBLISH_DIRECTORY]
                )
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
                # TODO conditionally add steps to build configs for other deployments if applicable
                if 0 == exit_code:
                    self.next_steps.append(
                        BuildNginxStaticSiteConfig(
                            "config.conf",
                            self.properties[Properties.DOMAIN],
                            self.publish_directory,
                        )
                    )
                    self.next_steps.append(TestNginxConfig())
            except TOMLDecodeError:
                exit_code = -1
                output = f"Config file {self.config_file} is invalid"

        return exit_code, output
