# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

BlueROV2 Heavy + forward-looking multibeam sonar simulation (ROS 2 Lyrical, Gazebo Jetty / gz-sim 10, gz-gui 10 on Qt6), extracted from POSIM. It targets Ubuntu 26.04 ARM64 in a Parallels VM. System dependencies come from POSIM's installer through `~/.ros_ardusub_env/env` (override with `ROV_SONAR_ROS_ENV`); this repo installs nothing system-wide. Docs, comments and commit messages are in English.

## Commands

All scripts source the ROS environment themselves; `build/`, `install/`, `log/` stay in the project (merge-install, symlink-install).

```bash
./scripts/fetch-deps.sh                     # once: pinned ros_gz 3.0.12 into deps/ (system 3.0.10 bridge segfaults on shutdown)
./build.sh                                  # whole workspace; extra args go to colcon build
./build.sh --packages-select rov_sonar_gui  # one package
./extras/parallels/build.sh                 # Ogre 1 GPU display plugins into .local/runtime (required by run.sh; rerun after editing extras/parallels)
./test.sh --packages-select rov_sonar_bringup rov_sonar_control rov_sonar_gui   # project tests
./test.sh                                   # also the plugin tests copied from POSIM
./test.sh --packages-select rov_sonar_bringup --ctest-args -R test_scene        # one test target
./run.sh [arg:=value ...]                   # hybrid launch (recommended); ./run.sh --show-args
./run-software.sh [gui:=false]              # all-software fallback
./teleop.sh                                 # keyboard teleop, separate terminal
```

Builds default to one job (`CMAKE_BUILD_PARALLEL_LEVEL=1`, `MAKEFLAGS=-j1`, `CARGO_BUILD_JOBS=1`): `ros_gz_bridge` OOMs at three jobs on the 7 GB VM. Don't raise parallelism above 2 there.

The pytest files load their module under test by file path (`scripts/sonar_view.py`, `launch/scene.py`), so after `source scripts/env.sh` they also run directly, e.g. `python3 -m pytest src/rov_sonar_bringup/test/test_sonar_view.py -k palette`. The `rov_sonar_gui` gtests include an offscreen QML test of the pop-out window (`test_image_view_qml`).

## Architecture

**Launch flow.** `run.sh` → `hybrid.launch.py` → includes `sim.launch.py` with `gui:=false` and a per-launch `GZ_PARTITION` (`rov_sonar_hybrid_<pid>`), then starts a separate `gz-sim-gui-client` 4 s later. The Gazebo server renders the camera and sonar with software Ogre 2 (llvmpipe). The GUI client unsets the software-GL variables and uses the GPU through a privately built Ogre 1 render plugin plus `RovUnderwaterView` (fog, lighting, water styling) and `StaticWater`, which aliases `WavesVisual` so the GUI does not load Wave Sim. Closing the display shuts the whole launch down. `run-software.sh` runs `sim.launch.py` directly with Gazebo's own GUI on Ogre 2. `hybrid.launch.py` forwards every `sim.launch.py` `ARGUMENTS` entry except `HYBRID_ONLY`, so new launch arguments belong in `sim.launch.py`'s `ARGUMENTS` dict.

**Scene generation (`rov_sonar_bringup/launch/scene.py`).** No spawn service is used. At launch, `robot_model()` reads the model SDF from the installed `rov_sonar_description`, applies the sonar profile (`SONAR_PROFILES`: beams, rays, bandwidth), rate, camera options and ballast. `build_world()` embeds the robot into a temporary world file. `gui_config()` extracts the `<gui>` block from `worlds/shallow_underwater.world`, adapts it per render engine (Ogre 1 hybrid vs Ogre 2), and adds the window size and `WINDOW_STYLE` theme. Installed model and world files are never modified. `test_scene.py` covers all of this.

**Sonar pipeline.** The `multibeam_sonar` sensor (`src/simulator/multibeam_sonar`, CPU/WGPU/CUDA backends; WGPU is Rust in `wgpu_vendor`) is loaded by `multibeam_sonar_system` and publishes raw echoes (`marine_acoustic_msgs/ProjectedSonarImage`, float32 dB). `scripts/sonar_view.py` (`FanRenderer`) turns them into the fan image (Amber/Gold LUT, range arcs, sector lines, range labels, plain-text readout). It publishes the image both on ROS (`/rov/sonar/fan_image`) and directly on Gazebo transport (`gz_topic` parameter) for the GUI panel. Don't route the fan image through a ROS→GZ `ros_gz_bridge`: that bridge stalls after several minutes with these large images. Display parameters (`gain_db`, `dynamic_range_db`, `palette`) can be changed at runtime with `ros2 param set /sonar_view ...`.

**GUI (`src/rov_sonar_gui`).** gz-gui plugins found via `GZ_GUI_PLUGIN_PATH` (set by `gui.dsv`):
- `RovViewAxes`: an X/Y/Z indicator driven by `/gui/camera/pose`.
- `RovImageView`: the camera and sonar panels. A `QQuickImageProvider` serves the frames; the enlarge button pops the panel out into a separate QML `Window`, and closing that window docks it again.

QML loads from `qrc:/<Name>/<Name>.qml`. Properties read in QML must emit their NOTIFY signal from `LoadConfig`, because the QML is created before the config is loaded. Panel layout lives in the world's `<gui>` block.

**Vehicle stack (`rov_sonar_control`).** `vehicle.launch.py` starts the Gazebo→ROS bridges, waits for the IMU topic, then starts ArduSub SITL, then MAVROS. Teleop (keyboard or web joystick → `ardusub_manual_control.py`) is a separate launch because it needs its own terminal. ArduSub writes `eeprom.bin` and `logs/` into the working directory, so the run scripts `cd` into `.local/run`.

**Environment hooks.** Each package's `.dsv` hook adds its plugin and resource paths (`GZ_SIM_SYSTEM_PLUGIN_PATH`, `GZ_SIM_RESOURCE_PATH`, `GZ_GUI_PLUGIN_PATH`). If Gazebo can't find a plugin or model, check that `install/setup.bash` was sourced after the build.

## Conventions

- `src/simulator/*` is code copied from POSIM; keep changes there minimal. Provenance is tracked in `NOTICE`.
- Topics use the `/rov/*` prefix (POSIM used `/tutorial/*`). To inspect Gazebo topics, set the launch's `GZ_PARTITION` before running `gz topic`.
- Interface style: academic, minimalist, white UI with compact spacing; sonar fan on a dark page (never white) with the Amber/Gold palette; orange (#FF5722) window toolbar and light-blue (#03A9F4) panel title bars.
- Keep README.md in sync when launch arguments, defaults or the interface change.
