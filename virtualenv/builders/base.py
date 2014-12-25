import glob
import os.path
import subprocess
import sys

from virtualenv._system import WINDOWS


WHEEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_wheels",
)

SCRIPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_scripts",
)


class BaseBuilder(object):

    def __init__(self, python, system_site_packages=False, clear=False,
                 pip=True, setuptools=True, extra_search_dirs=None,
                 prompt=""):
        # We default to sys.executable if we're not given a Python.
        if python is None:
            python = sys.executable

        # We default extra_search_dirs to and empty list if it's None
        if extra_search_dirs is None:
            extra_search_dirs = []

        self.python = python
        self.system_site_packages = system_site_packages
        self.clear = clear
        self.pip = pip
        self.setuptools = setuptools
        self.extra_search_dirs = extra_search_dirs
        self.prompt = prompt

    @classmethod
    def check_available(self, python):
        raise NotImplementedError

    def create(self, destination):
        # Actually Create the virtual environment
        self.create_virtual_environment(destination)

        # Install our activate scripts into the virtual environment
        self.install_scripts(destination)

        # Install the packaging tools (pip and setuptools) into the virtual
        # environment.
        self.install_tools(destination)

    def create_virtual_environment(self, destination):
        raise NotImplementedError

    def install_scripts(self, destination):
        # Determine the list of files based on if we're running on Windows
        if WINDOWS:
            files = {"activate.bat", "activate.ps1", "deactivate.bat"}
        else:
            files = {"activate.sh", "activate.fish", "activate.csh"}

        # We just always want add the activate_this.py script regardless of
        # platform.
        files.add("activate_this.py")

        # Ensure that our destination is an absolute path
        destination = os.path.abspath(destination)

        # Determine the name of our virtual environment
        name = os.path.basename(destination)

        # Determine the special Windows prompt
        win_prompt = self.prompt if self.prompt else "({0})".format(name)

        # Go through each file that we want to install, replace the special
        # variables so that they point to the correct location, and then write
        # them into the bin directory
        for filename in files:
            # Compute our source and target paths
            source = os.path.join(SCRIPT_DIR, filename)
            target = os.path.join(destination, "bin", filename)

            # Write the files themselves into their target locations
            with open(source, "r", encoding="utf-8") as source_fp:
                with open(target, "w", encoding="utf-8") as target_fp:
                    # Get the content from the sources and then replace the
                    # variables with their final values.
                    win_prompt = self.prompt or "(%s)" % "wat"
                    data = source_fp.read()
                    data = data.replace("__VIRTUAL_PROMPT__", self.prompt)
                    data = data.replace("__VIRTUAL_WINPROMPT__", win_prompt)
                    data = data.replace("__VIRTUAL_ENV__", destination)
                    data = data.replace("__VIRTUAL_NAME__", name)
                    data = data.replace("__BIN_NAME__", "bin")

                    # Actually write our content to the target locations
                    target_fp.write(data)

    def install_tools(self, destination):
        # Determine which projects we are going to install
        projects = []
        if self.pip:
            projects.append("pip")
        if self.setuptools:
            projects.append("setuptools")

        # Short circuit if we're not going to install anything
        if not projects:
            return

        # Compute the path to the Python interpreter inside the virtual
        # environment.
        python = os.path.join(destination, "bin", "python")

        # Find all of the Wheels inside of our WHEEL_DIR
        wheels = glob.iglob(os.path.join(WHEEL_DIR, "*.whl"))

        # Construct the command that we're going to use to actually do the
        # installs.
        command = [
            python, "-m", "pip", "install", "--no-index", "--isolated",
            "--find-links", WHEEL_DIR,
        ]

        # Add our extra search directories to the pip command
        for directory in self.extra_search_dirs:
            command.extend(["--find-links", directory])

        # Actually execute our command, adding the wheels from our WHEEL_DIR
        # to the PYTHONPATH so that we can import pip into the virtual
        # environment even though it's not currently installed.
        subprocess.check_call(
            command + projects,
            env={
                "PYTHONPATH": os.pathsep.join(wheels),
            },
        )