# POSIM multibeam sonar

The ray-based point-scattering model produces intensity–range data, sonar images
and point clouds. Select WGPU, CUDA or CPU processing at launch. WGPU uses Vulkan
on Linux and Metal on native macOS; all backends require Gazebo rendering.

In this project the backend is chosen with the `compute_backend` launch argument,
which sets `POSIM_SONAR_COMPUTE_BACKEND` for the sensor.

## Documentation (POSIM)

- [Sensor, demo and output topics](https://github.com/IOES-Lab/POSIM/blob/main/website/content/en/sonar.md)
- [Build, backend selection and troubleshooting](https://github.com/IOES-Lab/POSIM/blob/main/website/content/en/sonar-tuning.md)
- [Apple Silicon](https://github.com/IOES-Lab/POSIM/blob/main/website/content/en/sonar-tuning.md#apple-silicon)
- [Research citation and licenses](https://github.com/IOES-Lab/POSIM/blob/main/website/content/en/citation.md)
