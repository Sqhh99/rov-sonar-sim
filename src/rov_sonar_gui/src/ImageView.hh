// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <QImage>
#include <QString>
#include <gz/gui/Plugin.hh>
#include <gz/msgs/image.pb.h>
#include <gz/transport/Node.hh>
#include <memory>
#include <string>

namespace rov_sonar
{
class FrameProvider;

/// Image panel with a title bar and an "enlarge" button that opens the
/// image in a separate window; closing that window returns it to the panel.
class ImageView : public gz::gui::Plugin
{
  Q_OBJECT
  Q_PROPERTY(QString caption READ Caption NOTIFY ConfigChanged)
  Q_PROPERTY(QString source READ Source NOTIFY SourceChanged)
  Q_PROPERTY(double aspect READ Aspect NOTIFY AspectChanged)
  Q_PROPERTY(QString windowColor READ WindowColor NOTIFY ConfigChanged)

public:
  ImageView();
  ~ImageView() override;
  void LoadConfig(const tinyxml2::XMLElement * config) override;
  QString Caption() const;
  QString Source() const;
  double Aspect() const;
  QString WindowColor() const;

  /// Copy of a Gazebo image as a QImage; null for unsupported or short data.
  static QImage Convert(const gz::msgs::Image & message);

signals:
  // The QML item exists before LoadConfig runs.
  void ConfigChanged();
  void SourceChanged();
  void AspectChanged();

private:
  void OnImage(const gz::msgs::Image & message);

  QString caption;
  QString providerName;
  QString windowColor = "#202020";
  FrameProvider * provider = nullptr;  // Owned by the QML engine.
  unsigned frame = 0;
  double aspect = 0.75;
  // Last member: destroyed first, so no callback outlives the state above.
  gz::transport::Node node;
};
}  // namespace rov_sonar
