#!/usr/bin/env bash
# Fallback: everything (including the Gazebo GUI) on software OpenGL.
# Use gui:=false for a headless server. Arguments go to ros2 launch.
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$root/scripts/env.sh"
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export QT_QPA_PLATFORM=xcb
mkdir -p "$root/.local/run" && cd "$root/.local/run"
exec ros2 launch rov_sonar_bringup sim.launch.py "$@"
