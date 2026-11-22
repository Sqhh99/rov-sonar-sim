cmake_minimum_required(VERSION 3.22)
project(rov_sonar_bringup)

find_package(ament_cmake REQUIRED)

install(PROGRAMS scripts/sonar_view.py scripts/sonar_window.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch rviz DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_sonar_view test/test_sonar_view.py)
  ament_add_pytest_test(test_scene test/test_scene.py
    ENV "ROV_SONAR_DESCRIPTION_SRC=${CMAKE_CURRENT_SOURCE_DIR}/../rov_sonar_description")
endif()

ament_package()
