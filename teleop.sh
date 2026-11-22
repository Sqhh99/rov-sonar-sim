#!/usr/bin/env bash
# Keyboard teleoperation; run in its own terminal while the simulation runs.
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$root/scripts/env.sh"
exec ros2 launch rov_sonar_control teleop.launch.py "$@"
