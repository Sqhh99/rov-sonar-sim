// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <QVariantList>
#include <gz/gui/Plugin.hh>
#include <gz/math/Quaternion.hh>
#include <gz/msgs/pose.pb.h>
#include <gz/transport/Node.hh>

namespace rov_sonar
{
/// Draws the world X, Y and Z axes as seen from the 3D view's camera.
/// The camera orientation comes from the GUI's camera pose topic.
class ViewAxes : public gz::gui::Plugin
{
  Q_OBJECT
  Q_PROPERTY(QVariantList axes READ Axes NOTIFY AxesChanged)

public:
  ViewAxes();
  void LoadConfig(const tinyxml2::XMLElement * config) override;
  QVariantList Axes() const;

  /// Screen-space unit axes for a camera orientation (Gazebo camera frame:
  /// +X forward, +Y left, +Z up). Each entry holds label, color, x (right),
  /// y (down) and depth (away from the viewer); farthest first.
  static QVariantList Project(const gz::math::Quaterniond & camera);

signals:
  void AxesChanged();

private:
  void OnPose(const gz::msgs::Pose & message);

  QVariantList axes;
  gz::math::Quaterniond last{0, 0, 0, 0};
  // Last member: destroyed first, so no callback outlives the state above.
  gz::transport::Node node;
};
}  // namespace rov_sonar
