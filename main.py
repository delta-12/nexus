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

LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


def main() -> int:
    repo = input("Enter repo to deploy: ")
    reverse_proxy_environment = ContainerEnvironment(
        container_image=Images.REVERSE_PROXY,
        container_ports={"80/tcp": 80, "443/tcp": 443},
    )
    reverse_proxy_deployment = Deployment(
        reverse_proxy_environment, "nexus-reverse-proxy"
    )
    environment = ContainerEnvironment()
    deployment = Deployment(environment)
    deployment.add_step(GitClone(repo))
    deployment.add_step(ReadNexusConfig())
    exit_code, output = deployment.run_all_steps()

    if 0 == exit_code:
        name = deployment.get_property(Properties.NAME)
        domain = deployment.get_property(Properties.DOMAIN)
        email = deployment.get_property(Properties.EMAIL)
        reverse_proxy_deployment.add_step(AddDomainToCertificate(domain, email))
        reverse_proxy_deployment.add_step(BuildNginxReverseProxyConfig(domain, name))
        reverse_proxy_deployment.add_step(TestNginxConfig())
        reverse_proxy_deployment.add_step(ReloadNginx())
        exit_code, output = reverse_proxy_deployment.run_all_steps()

    if 0 != exit_code:
        # TODO kill container and prune if failure
        print(f"Exit code: {exit_code}, Error message {output}")

    return exit_code


if __name__ == "__main__":
    main()
