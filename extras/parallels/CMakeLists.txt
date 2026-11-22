cmake_minimum_required(VERSION 3.22)
project(posim_virgl_ogre1 LANGUAGES CXX)
find_package(gz-rendering 10.0.2 EXACT REQUIRED)
find_package(gz-common REQUIRED COMPONENTS graphics events geospatial)
find_package(gz-plugin REQUIRED COMPONENTS register)
find_package(PkgConfig REQUIRED)
pkg_check_modules(OGRE REQUIRED IMPORTED_TARGET OGRE)
find_package(OpenGL REQUIRED)
set(POSIM_OGRE_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/../ogre" CACHE PATH "Patched Ogre 1 source")
file(GLOB sources CONFIGURE_DEPENDS "${POSIM_OGRE_SOURCE}/src/*.cc")
add_library(posim_virgl_ogre1 SHARED ${sources})
target_compile_features(posim_virgl_ogre1 PRIVATE cxx_std_17)
target_compile_definitions(posim_virgl_ogre1 PRIVATE
  gz_rendering_ogre_EXPORTS OGRE_VERSION_LT_1_11_0 OGRE_VERSION_LT_1_12_0
  OGRE_RESOURCE_PATH="/usr/lib/aarch64-linux-gnu/OGRE-1.9.0")
target_include_directories(posim_virgl_ogre1 PRIVATE
  "${POSIM_OGRE_SOURCE}/include"
  "${gz-rendering_INCLUDE_DIRS}"
  /usr/include/OGRE/Paging /usr/include/OGRE/Terrain
  /usr/include/OGRE/RTShaderSystem /usr/include/OGRE/Overlay
  /usr/include/OGRE/RenderSystems/GL)
target_link_libraries(posim_virgl_ogre1 PRIVATE
  gz-rendering::gz-rendering gz-common::requested gz-plugin::register
  PkgConfig::OGRE OpenGL::GL OpenGL::GLU
  OgreRTShaderSystem OgreOverlay OgreTerrain OgrePaging)
set_target_properties(posim_virgl_ogre1 PROPERTIES OUTPUT_NAME gz-rendering-ogre)
find_package(gz-sim REQUIRED)
add_library(posim_static_water SHARED static_water.cc)
target_compile_features(posim_static_water PRIVATE cxx_std_17)
target_link_libraries(posim_static_water PRIVATE gz-sim::gz-sim gz-plugin::register)
set_target_properties(posim_static_water PROPERTIES OUTPUT_NAME gz-waves1-waves-visual-system)

# GUI plugin: underwater look (fog, colours, water surface) for the Ogre 1 view.
find_package(gz-gui REQUIRED)
qt_add_resources(UNDERWATER_VIEW_QML RovUnderwaterView.qrc)
add_library(RovUnderwaterView SHARED underwater_view.cc ${UNDERWATER_VIEW_QML})
target_compile_features(RovUnderwaterView PRIVATE cxx_std_17)
target_include_directories(RovUnderwaterView PRIVATE /usr/include/OGRE/RTShaderSystem)
target_link_libraries(RovUnderwaterView PRIVATE
  gz-gui::gz-gui gz-rendering::gz-rendering gz-plugin::register PkgConfig::OGRE
  OgreRTShaderSystem)
set_target_properties(RovUnderwaterView PROPERTIES PREFIX "")
