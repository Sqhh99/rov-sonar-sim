#!/usr/bin/env bash
# Fetch source dependencies that must be newer than the ROS 2 Lyrical binaries.
#
# ros_gz 3.0.12 (+ POSIM's pinned launch fix): the Lyrical binary ros_gz_bridge
# 3.0.10 segfaults on shutdown; upstream #977 fixes it. Only ros_gz_bridge and
# ros_gz_interfaces are built; the other ros_gz packages are COLCON_IGNOREd.
#
# Usage: scripts/fetch-deps.sh [existing ros_gz checkout to copy instead of cloning]
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
url=https://github.com/yeseorizi/ros_gz.git
commit=c38a35deaaba29380665949872023a5998f24222
dest="$root/deps/ros_gz"
mkdir -p "$root/deps"
if [[ ! -d "$dest/.git" ]]; then
    if [[ -n "${1:-}" ]]; then
        git clone --no-hardlinks "$1" "$dest"
        git -C "$dest" remote set-url origin "$url"
    else
        git clone "$url" "$dest"
    fi
fi
git -C "$dest" -c advice.detachedHead=false checkout --quiet "$commit"
for package in ros_gz ros_gz_image ros_gz_sim ros_gz_sim_demos test_ros_gz_bridge; do
    [[ -d "$dest/$package" ]] && touch "$dest/$package/COLCON_IGNORE"
done
printf 'ros_gz pinned at %s in %s\n' "$(git -C "$dest" rev-parse --short HEAD)" "$dest"
