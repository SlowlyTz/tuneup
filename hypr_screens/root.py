"""Running a one-time setup script as root: pkexec (a password dialog) from the
settings window, sudo from a terminal. The script goes in as an argument, not
a file: a file of the user's could be changed while the password is asked for."""
import shutil
import subprocess


def run_as_root(text: str, graphical: bool) -> bool:
    elevate = ["pkexec"] if graphical or not shutil.which("sudo") else ["sudo"]
    return subprocess.run([*elevate, "/bin/sh", "-c", text], check=False).returncode == 0
