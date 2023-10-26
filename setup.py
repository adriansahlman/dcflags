import re
import os
from setuptools import (
    setup,
    find_packages,
)
from typing import Optional


def find_version(
    fpath: str,
) -> Optional[str]:
    with open(fpath, "r") as fp:
        match = re.search(
            r'(?<=__version__ = [\'"])([^\'"]+)(?=[\'"])',
            fp.read(),
        )
    if not match:
        return None
    return match.group(1)


root = os.path.dirname(os.path.abspath(__file__))


with open(os.path.join(root, "README.md"), "r") as fp:
    long_description = fp.read()


version = find_version(os.path.join(root, "dcflags/__init__.py"))
if not version:
    raise RuntimeError("could not find version of dcflags")


setup(
    name="dcflags",
    version=version,
    description="Dataclass fields as cmd args and env vars",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/adriansahlman/dcflags",
    author="Adrian Sahlman",
    author_email="adrian.sahlman@gmail.com",
    license="MIT",
    packages=find_packages(include=("dcflags", "dcflags.*")),
    package_data={"dcflags": ["py.typed"]},
    python_requires=">=3.5",
    zip_safe=True,
    keywords="parse arguments cmd command dataclass env environmental dcflags",
)
