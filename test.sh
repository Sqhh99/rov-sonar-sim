#!/usr/bin/env bash
# Run the workspace tests (build first). Extra arguments go to colcon test,
# e.g. ./test.sh --packages-select rov_sonar_bringup
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$root/scripts/env.sh"
cd "$root"
colcon --log-base "$root/log" test \
    --base-paths "$root/src" \
    --packages-ignore ros_gz_bridge ros_gz_interfaces \
    --build-base "$root/build" --install-base "$root/install" \
    --test-result-base "$root/log/test" --merge-install --executor sequential "$@"
exec colcon test-result --test-result-base "$root/log/test" --verbose
