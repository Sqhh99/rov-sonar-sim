cmake_minimum_required(VERSION 3.22)
project(rov_sonar_control)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(mavros_msgs REQUIRED)
find_package(gz-transport REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GEOGRAPHICLIB REQUIRED IMPORTED_TARGET geographiclib)

# Gazebo posim_gnss samples -> MAVROS GPS_INPUT for ArduSub.
add_executable(marine_gnss_input src/MarineGnssInput.cc)
target_compile_features(marine_gnss_input PRIVATE cxx_std_17)
target_link_libraries(marine_gnss_input PRIVATE
  rclcpp::rclcpp ${mavros_msgs_TARGETS}
  gz-transport::gz-transport PkgConfig::GEOGRAPHICLIB)
install(TARGETS marine_gnss_input DESTINATION lib/${PROJECT_NAME})

install(
  PROGRAMS
    scripts/ardusub_manual_control.py
    scripts/keyboard_publisher.py
    scripts/ws_to_joy.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config web DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_gnss_input test/test_gnss_input.cc)
  target_compile_features(test_gnss_input PRIVATE cxx_std_17)
  target_include_directories(test_gnss_input PRIVATE src)
  target_link_libraries(test_gnss_input ${mavros_msgs_TARGETS})
  find_package(ament_cmake_pytest REQUIRED)
  # Mocked-service callback tests; keep them out of other tests' DDS discovery.
  ament_add_pytest_test(
    test_manual_control_buttons test/test_manual_control_buttons.py
    ENV ROS_AUTOMATIC_DISCOVERY_RANGE=OFF)
  ament_add_pytest_test(
    test_manual_control_services test/test_manual_control_services.py
    ENV ROS_AUTOMATIC_DISCOVERY_RANGE=OFF)
  ament_add_pytest_test(test_ws_lifecycle test/test_ws_lifecycle.py)
  ament_add_pytest_test(test_control_launch test/test_control_launch.py)
endif()

ament_package()
