from docker import from_env
from docker.models.containers import Container

NAME = "foobar"
REPO = "https://github.com/delta-12/nexus.git"
BRANCH = "main"

CONFIG_FILE = "nexus.toml"


def command_runner(
    container: Container, commands: list[str], working_dir: str = ""
) -> tuple[int, str]:
    exit_code = 0
    output = b""
    for command in commands:
        exit_code, output = container.exec_run(
            command, workdir=working_dir if len(working_dir) > 0 else None
        )
        if 0 != exit_code:
            break
    return exit_code, output.decode()


def git_clone(
    container: Container, repository: str, working_dir: str = ""
) -> tuple[int, str]:
    return command_runner(container, [f"git clone {repository} ."], working_dir)


def git_checkout(
    container: Container, branch: str, working_dir: str = ""
) -> tuple[int, str]:
    return command_runner(
        container, [f"git fetch origin {branch}", f"git checkout {branch}"], working_dir
    )


def get_config(container: Container, working_dir: str) -> dict:
    config = {}
    exit_code, _ = command_runner(
        container,
        [f"sh -c 'if [ -f \"{CONFIG_FILE}\" ]; then exit 0; else exit 1; fi'"],
        working_dir,
    )

    if 0 == exit_code:
        # TODO parse config
        config = {"config": True}
    else:
        config = {"config": False}

    return config


client = from_env()
# TODO set env vars
container = client.containers.run("d3lta12/nexus/static-host", name=NAME, detach=True)
print(git_clone(container, REPO, "/tmp"))
print(git_checkout(container, BRANCH, "/tmp"))
print(get_config(container, "/tmp"))
