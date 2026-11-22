#!/usr/bin/env bash
# Parallels VM (recommended): GPU scene display; camera and sonar render with
# software Ogre 2 on the server. Arguments go to ros2 launch, e.g.
#   ./run.sh sonar_quality:=preview sonar_window:=false
#   ./run.sh --show-args
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$root/scripts/env.sh"
if [[ ! -f "$ROV_SONAR_PARALLELS_RUNTIME/build/libgz-rendering-ogre.so" ]]; then
    printf 'Build the Parallels display plugin first: %s/extras/parallels/build.sh\n' "$root" >&2
    exit 1
fi
export QT_QPA_PLATFORM=xcb
# ArduSub writes eeprom.bin and logs/ into the working directory.
mkdir -p "$root/.local/run" && cd "$root/.local/run"
exec ros2 launch rov_sonar_bringup hybrid.launch.py "$@"
