import re
from os import environ


def check_version(filename, tag_name):
    """
    Get package version from version file and compare with tag name.
    """
    version = None

    with open(filename, "r") as version_file:
        if version_match := re.search(
                r"^__version__ = ['\"]([^'\"]*)['\"]",
                version_file.read(), re.M):
            version = version_match.group(1)

    # We have a versioning convention:
    #   App version: <major>.<minor>.<patch>
    #   Repository tag: v<major>.<minor>.<patch>
    if not (version and f"v{version}" == tag_name):
        exit(1)


if __name__ == "__main__":
    filename = "gamma_bridge/__init__.py"

    if tag_name := environ.get("CI_COMMIT_TAG"):
        check_version(filename, tag_name)
    else:
        exit(1)
