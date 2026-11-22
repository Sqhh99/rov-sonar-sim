# shellcheck shell=bash
# Source from bash:  source scripts/env.sh
# Loads ROS 2 Lyrical + Gazebo Jetty + ArduSub/Wave Sim paths, then this workspace.
_rov_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROV_SONAR_ROS_ENV:-$HOME/.ros_ardusub_env/env}"
if [[ -f "$_rov_root/install/setup.bash" ]]; then
    # shellcheck source=/dev/null
    source "$_rov_root/install/setup.bash"
fi
export ROV_SONAR_ROOT="$_rov_root"
export ROV_SONAR_PARALLELS_RUNTIME="${ROV_SONAR_PARALLELS_RUNTIME:-$_rov_root/.local/runtime/virgl-compat}"
unset _rov_root
