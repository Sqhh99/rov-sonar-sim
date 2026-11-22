cmake_minimum_required(VERSION 3.22)
project(rov_sonar_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY models meshes worlds
  DESTINATION share/${PROJECT_NAME}
)

# model://meshes/... resolves from share/<pkg>; model://calm_waves from share/<pkg>/models.
ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

ament_package()
