"""What install.sh asks the Python side (`tuneup installer <action>`), so the
package list, the root setup scripts and the remembered choices live in one
place. Needs nothing but Python: it runs before the packages are installed.

  packages [camera] [cava]       the packages to install, one per line
  root-script camera|galaxy-book the one-time root setup script
  choices                        the remembered answers: camera=1 cava= galaxy_book=0
  remember camera=1 cava=0 ...   remember the answers (for `install.sh --update`)
  galaxy-book                    exit 0 on a Galaxy Book with its driver loaded
  set-up camera|galaxy-book      exit 0 when that root setup is done already
  version                        Tuneup's version
"""
import getpass

from hypr_screens import camera, config, install, samsung, updates

FLAGS = {"1": True, "yes": True, "true": True, "0": False, "no": False, "false": False}


def packages(wanted: list[str]) -> list[str]:
    extra = {"cava": ["cava"], "camera": ["v4l2loopback-dkms"]}
    return install.PACKAGES + [name for want in wanted for name in extra.get(want, [])]


def root_script(what: str) -> str:
    if what == "camera":
        return camera.setup_script()
    if what == "galaxy-book":
        return samsung.setup_script(getpass.getuser())
    raise ValueError(f"no root setup for {what!r}")


def choices() -> list[str]:
    remembered = config.load()["install"]
    return [f"{key}={'' if value is None else int(value)}" for key, value in remembered.items()]


def remember(values: list[str]) -> None:
    answers = {}
    for item in values:
        key, _, value = item.partition("=")
        if key in config.INSTALL_CHOICES and value in FLAGS:
            answers[key] = FLAGS[value]
    config.update(lambda cfg: cfg["install"].update(answers))


def main(action: str, values: list[str]) -> int:
    if action == "packages":
        print("\n".join(packages(values)))
    elif action == "root-script":
        print(root_script(values[0] if values else ""))
    elif action == "choices":
        print("\n".join(choices()))
    elif action == "remember":
        remember(values)
    elif action == "galaxy-book":
        return 0 if samsung.present() else 1
    elif action == "set-up":
        done = {"camera": camera.is_set_up, "galaxy-book": samsung.is_set_up}.get(values[0] if values else "")
        return 0 if done and done() else 1
    elif action == "version":
        print(updates.current_version())
    return 0
