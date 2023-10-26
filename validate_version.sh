set -eu
semver_regex='(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?'
git_tag=$(git describe --tags)
(echo "${git_tag}" | grep -Pq  "^v${semver_regex}\$") || (echo "incorrect git tag format for release: ${git_tag}"; exit 1)
version_git=${git_tag#v}
version_string_python=$(grep -Po "__version__\s*=\s*[\"']${semver_regex}[\"|']" dcflags/__init__.py) || (echo "incorrect version format in dcflags/__init__.py for release"; exit 1)
version_python=$(echo "${version_string_python}" | grep -Po "${semver_regex}")
if [ ${version_git} != ${version_python} ]; then
    echo "git tag version ${version_git} does not match python package version ${version_python}"
    exit 1
fi
