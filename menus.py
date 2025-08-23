from deploy import Deployment, get_deployments
from environment import ContainerEnvironment, Images
import logging
from menu import Choice, ListMenu, TextMenu
from steps import (
    AddDomainToCertificate,
    BuildNginxReverseProxyConfig,
    GitClone,
    Properties,
    ReadNexusConfig,
    ReloadNginx,
    RemoveNginxConfig,
    TeardownEnvironment,
    TestNginxConfig,
)

LOGGER = logging.getLogger(__name__)
REVERSR_PROXY_NAME = "nexus-reverse-proxy"

logging.basicConfig(level=logging.INFO)


def get_reverse_proxy() -> Deployment:
    return Deployment(
        ContainerEnvironment(
            container_name=REVERSR_PROXY_NAME,
            container_image=Images.REVERSE_PROXY,
            container_ports={"80/tcp": 80, "443/tcp": 443},
        ),
        REVERSR_PROXY_NAME,
    )


# TODO return and handle exit code
def teardown(deployment: Deployment) -> None:
    reverse_proxy_deployment = get_reverse_proxy()
    reverse_proxy_deployment.add_step(
        RemoveNginxConfig(deployment.get_property(Properties.DOMAIN))
    )
    reverse_proxy_deployment.add_step(TestNginxConfig())
    reverse_proxy_deployment.add_step(ReloadNginx())
    exit_code, output = reverse_proxy_deployment.run_all_steps()

    if 0 == exit_code:
        deployment.add_step(TeardownEnvironment())
        exit_code, output = deployment.run_all_steps()

    if 0 != exit_code:
        logging.error(f"Exit code: {exit_code}, Error message {output}")
    else:
        deployment.delete()


class StaticSiteMenu(TextMenu):
    def __init__(self) -> None:
        super().__init__("Deploy new static site", "Enter repo to deploy: ")

    def on_select(self, selection: str) -> bool:
        valid = True
        reverse_proxy_deployment = get_reverse_proxy()
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
        else:
            deployment.save()

        return valid


NEW_DEPLOYMENT_CHOICES = [
    {"title": "Static Site", "callback": None, "next_menu": StaticSiteMenu()}
]

NEW_DEPLOYMENT_MENU = {
    "title": "New Deployment",
    "prompt": "Select option: ",
    "choices": [Choice(**choice) for choice in NEW_DEPLOYMENT_CHOICES],
}

TEARDOWN_DEPLOYMENT_MENU = {
    "title": "Teardown Deployment",
    "prompt": "Select deployment: ",
    "choices": [],
    "refresh_choices": lambda choices: [
        Choice(
            title=str(deployment.get_property(Properties.NAME)),
            callback=lambda: teardown(deployment),
        )
        for deployment in get_deployments()
    ],
}

MAIN_MENU_CHOICES = [
    {
        "title": "New Deployment",
        "callback": None,
        "next_menu": ListMenu(**NEW_DEPLOYMENT_MENU),
    },
    {
        "title": "Teardown Deployment",
        "callback": None,
        "next_menu": ListMenu(**TEARDOWN_DEPLOYMENT_MENU),
    },
]

MAIN_MENU = ListMenu(
    title="Main Menu",
    prompt="Select option: ",
    choices=[Choice(**choice) for choice in MAIN_MENU_CHOICES],
)
