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

BUILDIFIER_VERSION = "8.2.1"
POSTFIX_SHA256: dict[tuple[str, str], tuple[str, str]] = {
    ("Linux", "arm64"): (
        "linux-arm64",
        "3baa1cf7eb41d51f462fdd1fff3a6a4d81d757275d05b2dd5f48671284e9a1a5",
    ),
    ("Linux", "x86_64"): (
        "linux-amd64",
        "6ceb7b0ab7cf66fceccc56a027d21d9cc557a7f34af37d2101edb56b92fcfa1a",
    ),
    ("Darwin", "arm64"): (
        "darwin-arm64",
        "cfab310ae22379e69a3b1810b433c4cd2fc2c8f4a324586dfe4cc199943b8d5a",
    ),
    ("Darwin", "x86_64"): (
        "darwin-amd64",
        "9f8cffceb82f4e6722a32a021cbc9a5344b386b77b9f79ee095c61d087aaea06",
    ),
    ("Windows", "AMD64"): (
        "windows-amd64.exe",
        "802104da0bcda0424a397ac5be0004c372665a70289a6d5146e652ee497c0dc6",
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
