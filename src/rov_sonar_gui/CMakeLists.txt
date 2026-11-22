cmake_minimum_required(VERSION 3.22)
project(rov_sonar_gui LANGUAGES CXX)

find_package(ament_cmake REQUIRED)
find_package(gz-gui REQUIRED)
find_package(gz-math REQUIRED)
find_package(gz-msgs REQUIRED)
find_package(gz-plugin REQUIRED COMPONENTS register)
find_package(gz-transport REQUIRED)

set(CMAKE_AUTOMOC ON)

# Each plugin loads qrc:/<Name>/<Name>.qml; the file name is the plugin name.
qt_add_resources(VIEW_AXES_QML qml/RovViewAxes.qrc)
add_library(RovViewAxes SHARED src/ViewAxes.cc src/ViewAxes.hh ${VIEW_AXES_QML})
target_compile_features(RovViewAxes PRIVATE cxx_std_17)
target_link_libraries(RovViewAxes PRIVATE
  gz-gui::gz-gui gz-math::gz-math gz-msgs::gz-msgs gz-plugin::register gz-transport::gz-transport)

qt_add_resources(IMAGE_VIEW_QML qml/RovImageView.qrc)
add_library(RovImageView SHARED src/ImageView.cc src/ImageView.hh ${IMAGE_VIEW_QML})
target_compile_features(RovImageView PRIVATE cxx_std_17)
target_link_libraries(RovImageView PRIVATE
  gz-gui::gz-gui gz-msgs::gz-msgs gz-plugin::register gz-transport::gz-transport)

set_target_properties(RovViewAxes RovImageView PROPERTIES PREFIX "")
install(TARGETS RovViewAxes RovImageView LIBRARY DESTINATION lib)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_view_axes test/test_view_axes.cc src/ViewAxes.cc src/ViewAxes.hh)
  target_link_libraries(test_view_axes
    gz-gui::gz-gui gz-math::gz-math gz-msgs::gz-msgs gz-plugin::register gz-transport::gz-transport)
  ament_add_gtest(test_image_view test/test_image_view.cc src/ImageView.cc src/ImageView.hh)
  target_link_libraries(test_image_view
    gz-gui::gz-gui gz-msgs::gz-msgs gz-plugin::register gz-transport::gz-transport)
  find_package(Qt6 REQUIRED COMPONENTS Gui Qml Quick)
  ament_add_gtest(test_image_view_qml test/test_image_view_qml.cc ${IMAGE_VIEW_QML}
    SKIP_LINKING_MAIN_LIBRARIES)
  target_link_libraries(test_image_view_qml Qt6::Gui Qt6::Qml Qt6::Quick)
endif()

ament_environment_hooks(gui.dsv)
ament_package()
