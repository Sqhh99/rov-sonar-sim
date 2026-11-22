# rov-sonar-sim

Simulation, teleoperation and sonar imaging for an underwater robot (BlueROV2 Heavy) carrying a forward-looking multibeam sonar. The code was extracted from [POSIM](https://github.com/IOES-Lab/POSIM) and keeps only what this scenario needs, so it can be built, run and developed on its own.

- **Simulation**: Gazebo Jetty, a 4 m shallow inspection site (seabed plus pillar, box, pipe and sphere targets), hydrodynamics, buoyancy, 8 thrusters, IMU, GNSS, camera and multibeam sonar.
- **Control**: ArduSub SITL + MAVROS with keyboard (or web joystick) manual control.
- **Imaging**: the multibeam sonar plugin (CPU / WGPU / CUDA backends) publishes raw echoes; the `sonar_view` node renders them as an Amber/Gold fan image with range arcs, sector lines and range labels.

Environment: Ubuntu 26.04 ARM64 (Parallels VM), ROS 2 Lyrical, Gazebo Jetty.

## Layout

```text
rov-sonar-sim/
├── build.sh                  # Build the workspace (build/, install/, log/ stay in the project)
├── run.sh                    # Recommended: Parallels hybrid-rendering launch
├── run-software.sh           # Fallback: all-software rendering (gui:=false runs headless)
├── teleop.sh                 # Keyboard teleoperation
├── test.sh                   # Run the tests
├── scripts/env.sh            # Load the ROS environment and this workspace
├── scripts/fetch-deps.sh     # Fetch source dependencies (ros_gz 3.0.12) into deps/
├── extras/parallels/         # Parallels GPU display: Ogre 1 render plugin and underwater look
└── src/
    ├── rov_sonar_bringup/    # Launch files, scene generation, sonar fan viewer, RViz preset
    │   ├── launch/sim.launch.py      # Main simulation entry point
    │   ├── launch/hybrid.launch.py   # Parallels hybrid entry point (includes sim.launch.py)
    │   ├── launch/scene.py           # World generation: robot setup, sonar profiles, GUI config and theme
    │   ├── scripts/sonar_view.py     # Raw echoes -> fan image
    │   └── scripts/sonar_window.py   # Standalone sonar window
    ├── rov_sonar_control/    # ArduSub/MAVROS vehicle stack, keyboard/web teleop, GNSS input
    ├── rov_sonar_description/# Robot model, meshes, shallow-water world (and its Gazebo GUI layout)
    ├── rov_sonar_gui/        # Gazebo GUI plugins: XYZ view axes, camera/sonar panels with pop-out windows
    └── simulator/            # Gazebo plugins copied from POSIM
        ├── multibeam_sonar/          # Multibeam sonar sensor
        ├── multibeam_sonar_system/   # Sonar system plugin (libmultibeam_sonar_system)
        ├── wgpu_vendor/              # WGPU sonar compute backend (Rust)
        ├── posim_gz_gnss/            # Marine GNSS sensor
        └── posim_gz_rendering/       # Underwater optics (posim_underwater)
```

## Dependencies

This project does not install system dependencies itself. It reuses the environment set up by the POSIM installer, loaded through `~/.ros_ardusub_env/env`:

| Dependency | Location |
| --- | --- |
| ROS 2 Lyrical, Gazebo Jetty, ros_gz, MAVROS, marine_acoustic_msgs | `/opt/ros/lyrical` |
| ArduSub SITL, ardupilot_gazebo (ArduPilotPlugin, GstCameraPlugin) | `/opt/ardusub_ws` |
| Wave Sim (sea surface) | `/opt/waves`, `/opt/asv_wave_sim` |
| Patched gz-rendering | `/opt/posim/rendering-compat` |
| MAVROS router and RViz fix overlays | `/opt/posim/mavros-router`, `/opt/posim/rviz-close` |
| Rust (cargo, rustc) for `wgpu_vendor` | `/usr/bin` |

One source dependency is placed in `deps/ros_gz` by `scripts/fetch-deps.sh`. The system `ros_gz_bridge` 3.0.10 segfaults on shutdown (fixed upstream in #977), so, like POSIM, the project pins the 3.0.12 sources and builds only `ros_gz_bridge` and `ros_gz_interfaces`. Without `deps/ros_gz`, `build.sh` falls back to the system version and prints a note.

If the environment script is elsewhere, set `ROV_SONAR_ROS_ENV=/path/to/env` before running the project scripts.

The project does not depend on the POSIM source tree or its `install/`. Both can coexist; load only one of the two workspaces in a given terminal.

## Build

```bash
cd ~/workspace/ros2-workspace/rov-sonar-sim
./scripts/fetch-deps.sh          # First time: clone the pinned ros_gz into deps/
                                 # (offline: copy an existing checkout, e.g.
                                 #  ./scripts/fetch-deps.sh ../POSIM/.local/deps/ros_gz)
./build.sh                       # Build the whole workspace
./extras/parallels/build.sh      # First time (and after changes in extras/parallels): build the Parallels
                                 # GPU display plugins into .local/runtime (needed by run.sh)
```

Rebuild a single package:

```bash
./build.sh --packages-select rov_sonar_bringup
```

Builds use one job by default to stay within the VM's memory (`ros_gz_bridge` runs out of memory at three jobs on a 7 GB VM). With more memory, raise the parallelism:

```bash
CMAKE_BUILD_PARALLEL_LEVEL=4 MAKEFLAGS=-j4 CARGO_BUILD_JOBS=4 ./build.sh
```

Run the tests (after building):

```bash
./test.sh --packages-select rov_sonar_bringup rov_sonar_control rov_sonar_gui   # launch, scene, imaging, GUI and teleop tests
./test.sh                                                                        # also the plugin tests copied from POSIM
```

## Running

### Terminal A: start the simulation

```bash
cd ~/workspace/ros2-workspace/rov-sonar-sim
./run.sh
```

In hybrid mode the GPU draws the main Gazebo view, while the camera and sonar are still rendered by the server with software Ogre 2 (with underwater optics) and the sonar is computed on the CPU. Defaults: `balanced` sonar profile at 5 Hz, display gain 3 dB, dynamic range 35 dB, Amber/Gold palette. RViz and the standalone sonar window are off, and the vehicle is not armed automatically.

The interface is a single window: the 3D view with an X/Y/Z orientation indicator in its top-right corner, the camera and sonar images stacked in a compact side panel, and the simulation controls along the bottom edge. The enlarge button at the right of each image's title bar opens that image in a separate window; closing the window (or pressing `Esc` in it, or the button again) returns it to the panel. The sonar image is drawn on a dark page: the fan with range arcs, sector lines and range labels, and the sonar data as plain text in the top-left corner.

The GPU view adds an underwater look at fixed-function cost: per-pixel exponential fog in the water colour, blue-green ambient and sun light, a translucent water surface seen from below, and 4x multisample anti-aliasing. This changes only the display; the camera and sonar images are unaffected.

Common arguments (`./run.sh --show-args` lists them all):

| Argument | Default | Description |
| --- | --- | --- |
| `sonar_quality` | `balanced` | `preview` 128 beams × 64 rays, 15 kHz; `balanced` 192 × 96, 29.9 kHz; `full` 512 × 300, 29.9 kHz (the sensor's original configuration, very CPU-heavy) |
| `sonar_rate` | `5` | Sonar update rate (Hz); the achieved rate depends on compute load |
| `compute_backend` | `cpu` | `cpu`, `wgpu`, `cuda` or `auto` |
| `sonar_gain_db` | `3.0` | Display gain, -30 to 30 dB |
| `sonar_dynamic_range_db` | `35.0` | Display dynamic range, 20 to 100 dB |
| `sonar_palette` | `amber` | `amber` (Amber/Gold) or `gray` |
| `sonar_window` | `false` | Extra standalone sonar window (useful with `gui:=false`) |
| `rviz` | `false` | Open RViz (robot model, camera, sonar image, point cloud) |
| `ardusub` | `true` | Start ArduSub SITL and MAVROS; `false` runs only the simulation and sonar |
| `camera_stream` | `false` | Send the camera to QGroundControl as H.264 over UDP (port `camera_stream_port`, default 5600) |
| `x` `y` `z` `yaw` | `0 0 -3.1 0` | Initial robot pose (the seabed top is at z = -4.0) |
| `paused` | `false` | Start paused |

Examples:

```bash
./run.sh sonar_quality:=preview                    # Lower sonar load
./run.sh sonar_gain_db:=6.0 sonar_dynamic_range_db:=40.0
```

All-software fallback (the Gazebo GUI also uses llvmpipe, which is slower):

```bash
./run-software.sh                                  # With the Gazebo GUI
./run-software.sh gui:=false sonar_window:=true    # No Gazebo GUI, sonar window only
```

### Terminal B: keyboard teleoperation

```bash
cd ~/workspace/ros2-workspace/rov-sonar-sim
./teleop.sh
```

Keep keyboard focus on terminal B. First move: wait for ArduSub to connect → press `j` (STABILIZE) → press `c` to arm and wait for `ArduSub armed` → tap `w` to move forward.

| Key | Action |
| --- | --- |
| `j` / `h` | `STABILIZE` attitude hold / `ALT_HOLD` depth hold |
| `c` / `x` | Arm / disarm |
| `w` / `s` | Forward / backward |
| `a` / `d` | Yaw left / right |
| `r` / `f` | Ascend / descend |
| Space | Centre all motion commands |
| `q` | Disarm and quit the keyboard node |

Web joystick: `./teleop.sh use_web_joystick:=true`, then open `install/share/rov_sonar_control/web/virtual_joystick.html` in a browser and connect to `ws://127.0.0.1:8765`.

### Terminal C: tune the sonar display and inspect data

```bash
cd ~/workspace/ros2-workspace/rov-sonar-sim
source scripts/env.sh

ros2 param set /sonar_view gain_db 6.0
ros2 param set /sonar_view dynamic_range_db 45.0
ros2 param set /sonar_view palette gray
ros2 topic echo /mavros/state --once
```

Display parameters change only the rendered image, not the raw echoes. Changing `sonar_quality` requires restarting the simulation.

| Topic | Content |
| --- | --- |
| `/rov/sonar/fan_image` | Sonar fan image (range arcs, sector lines, range labels; the robot's left is on the image's left). `sonar_view` publishes it both as a ROS topic and directly on Gazebo transport for the GUI panel |
| `/model/bluerov2_heavy_multibeam_sonar/multibeam_sonar/sonar_image_raw` | Raw echoes (`marine_acoustic_msgs/ProjectedSonarImage`, float32 dB) |
| `/model/bluerov2_heavy_multibeam_sonar/multibeam_sonar/sonar_image` | The sensor's built-in colour preview |
| `/model/bluerov2_heavy_multibeam_sonar/multibeam_sonar/point_cloud` | Sonar point cloud |
| `/rov/camera/image` | Underwater optical camera |
| `/model/bluerov2_heavy_multibeam_sonar/odometry` | Odometry (ground truth) |
| `/mavros/state` | Autopilot connection, mode and arming state |
| `/clock` | Simulation clock |

Gazebo topics live in a `GZ_PARTITION` that is unique per launch (`rov_sonar_<pid>` or `rov_sonar_hybrid_<pid>`) to avoid clashing with other simulations; set the same partition before using `gz topic`.

### Stopping

In terminal B press `x` to disarm, then `Ctrl+C`. Close the Gazebo window or press `Ctrl+C` in terminal A. Closing a pop-out camera or sonar window only returns it to the panel.

## Development notes

- **Scene generation**: `launch/scene.py` reads the model and world from `rov_sonar_description`, applies the sonar profile, camera settings and neutral-buoyancy ballast, and embeds the robot directly in the generated world file (no spawn service needed). The installed model and world files are not modified. To add a profile, edit `SONAR_PROFILES`.
- **Sonar sensor parameters**: `<gz:multibeam_sonar>` in `src/rov_sonar_description/models/bluerov2_heavy_multibeam_sonar/model.sdf` (frequency, bandwidth, source level, field of view, ...).
- **Sonar imaging**: `src/rov_sonar_bringup/scripts/sonar_view.py` (publishes the fan image to the Gazebo GUI itself: a ROS → Gazebo `ros_gz_bridge` for these large images stalled after several minutes) (palette in `AMBER_STOPS`, page and text colours at the top of the file); tests in `test/test_sonar_view.py`.
- **Interface style**: window theme in `WINDOW_STYLE` (`launch/scene.py`); panel layout in the `<gui>` block of `src/rov_sonar_description/worlds/shallow_underwater.world`; the axes indicator (`RovViewAxes`) and image panels (`RovImageView`) in `src/rov_sonar_gui`; the GPU view's underwater look (fog density and colours) in `extras/parallels/underwater_view.cc` (rebuild with `./extras/parallels/build.sh`).
- **Vehicle stack**: `src/rov_sonar_control/launch/vehicle.launch.py` (Gazebo bridges → wait for IMU → ArduSub → MAVROS).
- **Main differences from POSIM**: Gazebo is started directly and the robot is embedded in the world file, so `ros_gz_sim`'s launch file and spawn service are no longer needed; topics `/tutorial/*` were renamed to `/rov/*`; the QGroundControl camera stream is optional (off by default); new `full` sonar profile and `sonar_rate` / `sonar_palette` arguments.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `run.sh` reports a missing display plugin | Run `./extras/parallels/build.sh` (again after updating the project) |
| ROS packages not found | Run `./build.sh` first, then `source scripts/env.sh` in the current terminal |
| Keys have no effect | Make sure terminal B has focus, `/mavros/state` shows `connected: true`, and the vehicle is armed |
| Simulation is sluggish | Use `sonar_quality:=preview`; close RViz and windows you don't need |
| Arcs or stripes in the sonar image | Adjust gain and dynamic range first; some arcs come from seabed returns and discrete sampling |

## License

Apache License 2.0 (see `LICENSE`). Provenance and third-party notes are in `NOTICE`.
