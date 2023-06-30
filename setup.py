#!/usr/bin/env python3

# Forked from https://github.com/shellcheck-py/shellcheck-py/blob/main/setup.py

from __future__ import annotations

import hashlib
import http
import os.path
import platform
import stat
import urllib.request

from distutils.command.build import build as orig_build
from distutils.core import Command
from setuptools import setup
from setuptools.command.install import install as orig_install

BUILDIFIER_VERSION = "6.1.2"
POSTFIX_SHA256: dict[tuple[str, str], tuple[str, str]] = {
    ("Linux", "arm64"): (
        "linux-arm64",
        "0ba6e8e3208b5a029164e542ddb5509e618f87b639ffe8cc2f54770022853080",
    ),
    ("Linux", "x86_64"): (
        "linux-amd64",
        "51bc947dabb7b14ec6fb1224464fbcf7a7cb138f1a10a3b328f00835f72852ce",
    ),
    ("Darwin", "arm64"): (
        "darwin-arm64",
        "7549b5f535219ac957aa2a6069d46fbfc9ea3f74abd85fd3d460af4b1a2099a6",
    ),
    ("Darwin", "x86_64"): (
        "darwin-amd64",
        "e2f4a67691c5f55634fbfb3850eb97dd91be0edd059d947b6c83d120682e0216",
    ),
    ("Windows", "x86_64"): (
        "windows-amd64.exe",
        "92bdd284fbc6766fc3e300b434ff9e68ac4d76a06cb29d1bdefe79a102a8d135",
    ),
}

PY_VERSION = "0"


def get_download_url() -> tuple[str, str]:
    postfix, sha256 = POSTFIX_SHA256[(platform.system(), platform.machine())]
    url = (
        f"https://github.com/bazelbuild/buildtools/releases/download/"
        f"v{BUILDIFIER_VERSION}/buildifier-{postfix}"
    )
    return url, sha256


def download(url: str, sha256: str) -> bytes:
    with urllib.request.urlopen(url) as resp:
        code = resp.getcode()
        if code != http.HTTPStatus.OK:
            raise ValueError(f"HTTP failure. Code: {code}")
        data = resp.read()

    checksum = hashlib.sha256(data).hexdigest()
    if checksum != sha256:
        raise ValueError(f"sha256 mismatch, expected {sha256}, got {checksum}")

    return data


def save_executable(data: bytes, base_dir: str):
    exe = "buildifier.exe" if platform.system() == "Windows" else "buildifier"
    output_path = os.path.join(base_dir, exe)
    os.makedirs(base_dir, exist_ok=True)

    with open(output_path, "wb") as fp:
        fp.write(data)

    # Mark as executable.
    # https://stackoverflow.com/a/14105527
    mode = os.stat(output_path).st_mode
    mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    os.chmod(output_path, mode)


class build(orig_build):
    sub_commands = orig_build.sub_commands + [("fetch_binaries", None)]


class install(orig_install):
    sub_commands = orig_install.sub_commands + [("install_buildifier", None)]


class fetch_binaries(Command):
    build_temp = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.set_undefined_options("build", ("build_temp", "build_temp"))

    def run(self):
        # save binary to self.build_temp
        url, sha256 = get_download_url()
        data = download(url, sha256)
        save_executable(data, self.build_temp)


class install_buildifier(Command):
    description = "install the buildifier executable"
    outfiles = ()
    build_dir = install_dir = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        # this initializes attributes based on other commands' attributes
        self.set_undefined_options("build", ("build_temp", "build_dir"))
        self.set_undefined_options(
            "install",
            ("install_scripts", "install_dir"),
        )

    def run(self):
        self.outfiles = self.copy_tree(self.build_dir, self.install_dir)

    def get_outputs(self):
        return self.outfiles


command_overrides = {
    "install": install,
    "install_buildifier": install_buildifier,
    "build": build,
    "fetch_binaries": fetch_binaries,
}


try:
    from wheel.bdist_wheel import bdist_wheel as orig_bdist_wheel
except ImportError:
    pass
else:

    class bdist_wheel(orig_bdist_wheel):
        def finalize_options(self):
            orig_bdist_wheel.finalize_options(self)
            # Mark us as not a pure python package
            self.root_is_pure = False

        def get_tag(self):
            _, _, plat = orig_bdist_wheel.get_tag(self)
            # We don't contain any python source, nor any python extensions
            return "py3", "none", plat

    command_overrides["bdist_wheel"] = bdist_wheel

setup(version=f"{BUILDIFIER_VERSION}.{PY_VERSION}", cmdclass=command_overrides)
