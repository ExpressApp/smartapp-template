"""
Get latest frontend tag.

Default sort strategy: DATE - latest uploaded package.
"""


import argparse
import json
import re
from datetime import datetime
from urllib.request import Request, urlopen
from typing import Any, Iterable, Generator

API_URL = (
    "https://gitlab.ccsteam.ru/api/v4/projects/{gitlab_project}/packages?"
    "package_type=generic&"
    "per_page={per_page}&"
    "page={page}"
)
DATETIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"

Package = dict[str, Any]


class Version:
    def __init__(self, version: str) -> None:
        match = re.match(r"(.*)([0-9]+)\.([0-9]+)\.([0-9]+)(.*)", version)
        if match is None:
            self.major = self.minor = self.patch = -1
            self.prefix = self.postfix = ""
            return

        self.prefix, *versions, self.postfix = match.groups()
        self.major, self.minor, self.patch = map(int, versions)

    def is_compatible_with(self, version: "Version") -> bool:
        """TODO: adjust for your versioning system."""
        return self.major <= version.major and self.minor <= version.minor

    def __lt__(self, other: "Version") -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        return True

    def __repr__(self):
        return f"<{self.prefix} {self.major}.{self.minor}.{self.patch} {self.postfix}>"


def list_packages(
    gitlab_project: int,
    access_token: str,
    page: int,
    per_page: int = 1,
) -> list[Package]:
    req = Request(
        API_URL.format(gitlab_project=gitlab_project, page=page, per_page=per_page),
    )
    req.add_header("Private-Token", access_token)
    content = urlopen(req).read()

    return json.loads(content)


def get_gitlab_project_packages(
    gitlab_project: int,
    access_token: str,
) -> list[Package]:
    packages: list[Package] = []
    page = 1

    while True:
        packages_page = list_packages(gitlab_project, access_token, page)

        if not packages_page:
            return packages

        packages += packages_page
        page += 1


def sort_packages_by_version(packages: Iterable[Package]) -> list[Package]:
    return sorted(
        packages,
        key=lambda package: Version(package["version"]),
    )


def sort_packages_by_compatibility_version(
    packages: Iterable[Package], project_version: Version
) -> list[Package]:
    compatible_packages = filter(
        lambda package: Version(package["version"]).is_compatible_with(project_version),
        packages,
    )
    return sort_packages_by_version(compatible_packages)


def sort_packages_by_updated_at(packages: Iterable[Package]) -> list[Package]:
    return sorted(
        packages,
        key=lambda package: datetime.strptime(
            package["pipeline"]["updated_at"],
            DATETIME_FMT,
        ),
    )


def main(
    gitlab_project: int,
    access_token: str,
    project_version: str,
    sort_strategy: str = "DATE",
) -> None:
    pr_version = Version(project_version)
    packages = get_gitlab_project_packages(gitlab_project, access_token)

    app_env_packages = [package for package in packages]

    if sort_strategy == "VERSION":
        latest_package = sort_packages_by_version(app_env_packages)[-1]
    elif sort_strategy == "VERSION_COMPATIBILITY":
        latest_package = sort_packages_by_compatibility_version(
            app_env_packages, pr_version
        )[-1]
    elif sort_strategy == "DATE":
        latest_package = sort_packages_by_updated_at(app_env_packages)[-1]
    else:
        raise ValueError(f"Unknown sort strategy: {sort_strategy}")

    print(latest_package["version"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gitlab_project")
    parser.add_argument("access_token")
    parser.add_argument("project_version")
    parser.add_argument(
        "-s",
        "--sort-strategy",
        choices=["VERSION", "VERSION_COMPATIBILITY", "DATE"],
        default="DATE",
        help="Strategy to sort packages by. Default: DATE",
    )

    args = parser.parse_args()
    gitlab_project = args.gitlab_project
    access_token = args.access_token
    project_version = args.project_version
    sort_strategy = args.sort_strategy

    main(
        args.gitlab_project, args.access_token, args.project_version, args.sort_strategy
    )
