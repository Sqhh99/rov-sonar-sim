"""Parallels VM: GPU (Ogre 1) scene display, software Ogre 2 for sensors.

The Gazebo server renders the camera and sonar with llvmpipe, which the
Parallels virgl driver cannot replace for Ogre 2. A separate GUI client uses
the GPU through a locally built Ogre 1 render plugin
(extras/parallels/build.sh). Set ROV_SONAR_PARALLELS_RUNTIME to its folder.
"""

import importlib.util
import os
from pathlib import Path
import sys
import tempfile

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    EmitEvent,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene  # noqa: E402

HYBRID_ONLY = ("gui", "gz_partition")


def _sim_launch():
    spec = importlib.util.spec_from_file_location(
        "rov_sonar_sim_launch", Path(__file__).resolve().parent / "sim.launch.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setup(context):
    runtime = Path(os.environ.get("ROV_SONAR_PARALLELS_RUNTIME", ""))
    plugin = runtime / "build" / "libgz-rendering-ogre.so"
    if not plugin.is_file():
        raise RuntimeError(
            f"Parallels display plugin not found: {plugin}. "
            "Build it with extras/parallels/build.sh and set ROV_SONAR_PARALLELS_RUNTIME."
        )
    share = Path(get_package_share_directory("rov_sonar_bringup"))
    description = get_package_share_directory("rov_sonar_description")
    temporary = tempfile.TemporaryDirectory(prefix="rov-sonar-gui-")
    config = scene.gui_config(description, Path(temporary.name) / "gui.config")
    partition = f"rov_sonar_hybrid_{os.getpid()}"

    forwarded = {
        name: LaunchConfiguration(name) for name in _sim_launch().ARGUMENTS if name not in HYBRID_ONLY
    }
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(share / "launch/sim.launch.py")),
        launch_arguments={**forwarded, "gui": "false", "gz_partition": partition}.items(),
    )
    client = (
        Path(get_package_prefix("gz_sim_vendor"))
        / "opt/gz_sim_vendor/libexec/gz/sim10/gz-sim-gui-client"
    )
    display = ExecuteProcess(
        name="gpu_display",
        cmd=[
            "env", "-u", "LIBGL_ALWAYS_SOFTWARE", "-u", "GALLIUM_DRIVER",
            str(client), "--render-engine-gui", "ogre", "--gui-config", str(config),
        ],
        additional_env={
            "GZ_PARTITION": partition,
            "GZ_RENDERING_PLUGIN_PATH": str(runtime / "build"),
            # The GUI loads a static water visual in place of Wave Sim's.
            "GZ_SIM_SYSTEM_PLUGIN_PATH": str(runtime / "build")
            + ":"
            + os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", ""),
            "QT_QPA_PLATFORM": "xcb",
        },
        output="screen",
    )
    return [
        RegisterEventHandler(
            OnShutdown(on_shutdown=[OpaqueFunction(function=lambda _c: temporary.cleanup())])
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=display,
                on_exit=[EmitEvent(event=Shutdown(reason="Gazebo display closed"))],
            )
        ),
        SetEnvironmentVariable("LIBGL_ALWAYS_SOFTWARE", "1"),
        SetEnvironmentVariable("GALLIUM_DRIVER", "llvmpipe"),
        simulation,
        TimerAction(period=4.0, actions=[display]),
    ]


def generate_launch_description():
    arguments = _sim_launch().arguments(skip=HYBRID_ONLY, sonar_window="true")
    return LaunchDescription(arguments + [OpaqueFunction(function=setup)])
