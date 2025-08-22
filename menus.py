from deploy import Deployment
from environment import ContainerEnvironment, Images
from steps import (
    AddDomainToCertificate,
    BuildNginxReverseProxyConfig,
    GitClone,
    Properties,
    ReadNexusConfig,
    ReloadNginx,
    TestNginxConfig,
)
import logging
from menu import ListMenu, Stack, TextMenu

LOGGER = logging.getLogger(__name__)
REVERSR_PROXY_NAME = "nexus-reverse-proxy"

logging.basicConfig(level=logging.INFO)


class MainMenu(ListMenu):
    def __init__(self) -> None:
        super().__init__("Main Menu", "Select option: ", {"New deployment": None})

    def on_update(self, stack: Stack) -> None:
        if 0 == self.index:
            stack.push(NewDeploymentMenu())


class NewDeploymentMenu(ListMenu):
    def __init__(self) -> None:
        super().__init__("New Deployment", "Select option: ", {"Static site": None})

    def on_update(self, stack: Stack) -> None:
        if 0 == self.index:
            stack.push(StaticSiteMenu())


class StaticSiteMenu(TextMenu):
    def __init__(self) -> None:
        super().__init__("Deploy new static site", "Enter repo to deploy: ")

    def on_select(self, selection: str) -> bool:
        valid = True
        reverse_proxy_environment = ContainerEnvironment(
            container_name=REVERSR_PROXY_NAME,
            container_image=Images.REVERSE_PROXY,
            container_ports={"80/tcp": 80, "443/tcp": 443},
        )
        reverse_proxy_deployment = Deployment(
            reverse_proxy_environment, REVERSR_PROXY_NAME
        )
        environment = ContainerEnvironment()
        deployment = Deployment(environment)
        deployment.add_step(GitClone(selection))
        deployment.add_step(ReadNexusConfig())
        exit_code, output = deployment.run_all_steps()

        if 0 == exit_code:
            name = deployment.get_property(Properties.NAME)
            domain = deployment.get_property(Properties.DOMAIN)
            email = deployment.get_property(Properties.EMAIL)
            reverse_proxy_deployment.add_step(AddDomainToCertificate(domain, email))
            reverse_proxy_deployment.add_step(
                BuildNginxReverseProxyConfig(domain, name)
            )
            reverse_proxy_deployment.add_step(TestNginxConfig())
            reverse_proxy_deployment.add_step(ReloadNginx())
            exit_code, output = reverse_proxy_deployment.run_all_steps()

        if 0 != exit_code:
            # TODO kill container and prune if failure
            logging.error(f"Exit code: {exit_code}, Error message {output}")
            valid = False

        return valid

    def on_update(self, stack: Stack) -> None:
        stack.push(MainMenu())
