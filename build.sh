#!/usr/bin/env bash
# Build the workspace. build/, install/ and log/ stay inside this project.
# Extra arguments go to colcon, e.g. ./build.sh --packages-select rov_sonar_bringup
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${ROV_SONAR_ROS_ENV:-$HOME/.ros_ardusub_env/env}"
# One job keeps the Ogre/Rust builds inside the VM's memory; raise if you have more.
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-1}"
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-1}"
export MAKEFLAGS="${MAKEFLAGS:--j1}"
cd "$root"
paths=("$root/src")
overrides=()
if [[ -d "$root/deps/ros_gz" ]]; then
    # scripts/fetch-deps.sh: newer ros_gz_bridge than the Lyrical binaries.
    paths+=("$root/deps/ros_gz")
    overrides=(--allow-overriding ros_gz_bridge ros_gz_interfaces)
else
    printf 'Note: deps/ros_gz not found; using the system ros_gz_bridge (run scripts/fetch-deps.sh).\n' >&2
fi
exec colcon --log-base "$root/log" build \
    --base-paths "${paths[@]}" "${overrides[@]}" \
    --build-base "$root/build" --install-base "$root/install" \
    --merge-install --symlink-install --executor sequential \
    "$@" \
    --cmake-args -DCMAKE_BUILD_TYPE=Release
