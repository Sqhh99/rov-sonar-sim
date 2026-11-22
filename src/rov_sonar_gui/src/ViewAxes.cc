// SPDX-License-Identifier: Apache-2.0
#include "ViewAxes.hh"

#include <QMetaObject>
#include <algorithm>
#include <gz/common/Console.hh>
#include <gz/msgs/Utility.hh>
#include <gz/plugin/Register.hh>
#include <string>
#include <utility>

namespace rov_sonar
{
ViewAxes::ViewAxes()
: axes(Project(gz::math::Quaterniond::Identity))
{
}

void ViewAxes::LoadConfig(const tinyxml2::XMLElement * config)
{
  if (this->title.empty())
  {
    this->title = "View axes";
  }
  std::string topic = "/gui/camera/pose";
  if (config)
  {
    if (auto element = config->FirstChildElement("topic"); element && element->GetText())
    {
      topic = element->GetText();
    }
  }
  if (!this->node.Subscribe(topic, &ViewAxes::OnPose, this))
  {
    gzerr << "View axes: cannot subscribe to [" << topic << "]\n";
  }
}

QVariantList ViewAxes::Axes() const
{
  return this->axes;
}

QVariantList ViewAxes::Project(const gz::math::Quaterniond & camera)
{
  struct Axis
  {
    const char * label;
    const char * color;
    gz::math::Vector3d direction;
  };
  const Axis world[] = {
    {"X", "#c0392b", gz::math::Vector3d::UnitX},
    {"Y", "#2e8b57", gz::math::Vector3d::UnitY},
    {"Z", "#2a5caa", gz::math::Vector3d::UnitZ},
  };
  std::vector<std::pair<double, QVariantMap>> projected;
  for (const auto & axis : world)
  {
    const auto v = camera.RotateVectorReverse(axis.direction);
    QVariantMap entry;
    entry["label"] = axis.label;
    entry["color"] = axis.color;
    entry["x"] = -v.Y();
    entry["y"] = -v.Z();
    entry["depth"] = v.X();
    projected.emplace_back(v.X(), entry);
  }
  std::stable_sort(projected.begin(), projected.end(), [](const auto & a, const auto & b) {
    return a.first > b.first;
  });
  QVariantList result;
  for (const auto & item : projected)
  {
    result.append(item.second);
  }
  return result;
}

void ViewAxes::OnPose(const gz::msgs::Pose & message)
{
  const auto orientation = gz::msgs::Convert(message.orientation());
  if (orientation.Equal(this->last, 1e-5))
  {
    return;
  }
  this->last = orientation;
  // Transport callbacks run on a worker thread; update QML on the GUI thread.
  QMetaObject::invokeMethod(
    this, [this, value = Project(orientation)]() {
      this->axes = value;
      emit this->AxesChanged();
    },
    Qt::QueuedConnection);
}
}  // namespace rov_sonar

GZ_ADD_PLUGIN(rov_sonar::ViewAxes, gz::gui::Plugin)
