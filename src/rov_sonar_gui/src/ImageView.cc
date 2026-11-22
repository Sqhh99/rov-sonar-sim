// SPDX-License-Identifier: Apache-2.0
#include "ImageView.hh"

#include <QMetaObject>
#include <QQmlApplicationEngine>
#include <QQuickImageProvider>
#include <atomic>
#include <gz/common/Console.hh>
#include <gz/gui/Application.hh>
#include <gz/plugin/Register.hh>
#include <mutex>
#include <utility>

namespace rov_sonar
{
class FrameProvider : public QQuickImageProvider
{
public:
  FrameProvider()
  : QQuickImageProvider(QQuickImageProvider::Image)
  {
  }

  QImage requestImage(const QString &, QSize * size, const QSize &) override
  {
    std::lock_guard<std::mutex> lock(this->mutex);
    if (size)
    {
      *size = this->image.size();
    }
    return this->image;
  }

  void Set(QImage value)
  {
    std::lock_guard<std::mutex> lock(this->mutex);
    this->image = std::move(value);
  }

private:
  std::mutex mutex;
  QImage image;
};

ImageView::ImageView()
{
  static std::atomic<unsigned> instances{0};
  this->providerName = QString("rov_image_view_%1").arg(instances++);
}

ImageView::~ImageView()
{
  // Stop callbacks before the engine deletes the provider they write to.
  for (const auto & topic : this->node.SubscribedTopics())
  {
    this->node.Unsubscribe(topic);
  }
  if (this->provider)
  {
    gz::gui::App()->Engine()->removeImageProvider(this->providerName);
  }
}

void ImageView::LoadConfig(const tinyxml2::XMLElement * config)
{
  std::string topic;
  if (config)
  {
    if (auto element = config->FirstChildElement("topic"); element && element->GetText())
    {
      topic = element->GetText();
    }
    if (auto element = config->FirstChildElement("window_color"); element && element->GetText())
    {
      this->windowColor = element->GetText();
    }
    if (auto gui = config->FirstChildElement("gz-gui"))
    {
      if (auto element = gui->FirstChildElement("title"); element && element->GetText())
      {
        this->caption = element->GetText();
      }
    }
  }
  if (this->caption.isEmpty())
  {
    this->caption = QString::fromStdString(topic);
  }
  this->title = this->caption.toStdString();
  emit this->ConfigChanged();
  this->provider = new FrameProvider;
  gz::gui::App()->Engine()->addImageProvider(this->providerName, this->provider);
  if (topic.empty() || !this->node.Subscribe(topic, &ImageView::OnImage, this))
  {
    gzerr << "Image view: cannot subscribe to [" << topic << "]\n";
  }
}

QString ImageView::Caption() const
{
  return this->caption;
}

QString ImageView::Source() const
{
  return this->frame == 0 ? QString() :
         QString("image://%1/%2").arg(this->providerName).arg(this->frame);
}

double ImageView::Aspect() const
{
  return this->aspect;
}

QString ImageView::WindowColor() const
{
  return this->windowColor;
}

QImage ImageView::Convert(const gz::msgs::Image & message)
{
  const int width = static_cast<int>(message.width());
  const int height = static_cast<int>(message.height());
  QImage::Format format;
  int depth;
  bool swap = false;
  switch (message.pixel_format_type())
  {
    case gz::msgs::PixelFormatType::RGB_INT8:
      format = QImage::Format_RGB888;
      depth = 3;
      break;
    case gz::msgs::PixelFormatType::BGR_INT8:
      format = QImage::Format_RGB888;
      depth = 3;
      swap = true;
      break;
    case gz::msgs::PixelFormatType::RGBA_INT8:
      format = QImage::Format_RGBA8888;
      depth = 4;
      break;
    case gz::msgs::PixelFormatType::L_INT8:
      format = QImage::Format_Grayscale8;
      depth = 1;
      break;
    default:
      return {};
  }
  const int step = message.step() ? static_cast<int>(message.step()) : width * depth;
  if (width <= 0 || height <= 0 || step < width * depth ||
      message.data().size() < static_cast<size_t>(step) * static_cast<size_t>(height))
  {
    return {};
  }
  QImage view(reinterpret_cast<const uchar *>(message.data().data()), width, height, step, format);
  return swap ? view.rgbSwapped() : view.copy();
}

void ImageView::OnImage(const gz::msgs::Image & message)
{
  auto image = Convert(message);
  if (image.isNull())
  {
    gzerr << "Image view [" << this->caption.toStdString() << "]: unsupported image\n";
    return;
  }
  const double ratio = static_cast<double>(image.height()) / image.width();
  this->provider->Set(std::move(image));
  // Transport callbacks run on a worker thread; notify QML on the GUI thread.
  QMetaObject::invokeMethod(
    this, [this, ratio]() {
      ++this->frame;
      emit this->SourceChanged();
      if (ratio != this->aspect)
      {
        this->aspect = ratio;
        emit this->AspectChanged();
      }
    },
    Qt::QueuedConnection);
}
}  // namespace rov_sonar

GZ_ADD_PLUGIN(rov_sonar::ImageView, gz::gui::Plugin)
