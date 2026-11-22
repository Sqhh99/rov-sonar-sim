// SPDX-License-Identifier: Apache-2.0
// The image panel opens its view in a separate window and returns it to the
// panel when that window closes. Runs offscreen with stub plugin data.
#include <gtest/gtest.h>

#include <QGuiApplication>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQmlPropertyMap>
#include <QQuickWindow>
#include <memory>

namespace
{
struct Panel
{
  QQmlEngine engine;
  QQmlPropertyMap view, window;
  std::unique_ptr<QObject> root;

  Panel()
  {
    view.insert("caption", "Camera");
    view.insert("source", "");
    view.insert("aspect", 0.75);
    view.insert("windowColor", "#101010");
    window.insert("pluginToolBarColorLight", "#03A9F4");
    window.insert("pluginToolBarTextColorLight", "#FFFFFF");
    engine.rootContext()->setContextProperty("_RovImageView", &view);
    engine.rootContext()->setContextProperty("_MainWindow", &window);
    QQmlComponent component(&engine, QUrl("qrc:/RovImageView/RovImageView.qml"));
    root.reset(component.create());
    if (!root)
    {
      ADD_FAILURE() << component.errorString().toStdString();
    }
  }

  QQuickWindow * Popup() const
  {
    return root ? root->findChild<QQuickWindow *>() : nullptr;
  }
};

void Settle()
{
  for (int i = 0; i < 20; ++i)
  {
    QCoreApplication::processEvents();
  }
}
}  // namespace

TEST(ImageViewQml, EnlargeOpensWindowAndClosingReturns)
{
  Panel panel;
  ASSERT_TRUE(panel.root);
  auto popup = panel.Popup();
  ASSERT_NE(popup, nullptr);
  EXPECT_FALSE(popup->isVisible());
  EXPECT_EQ(popup->title(), "Camera");

  QMetaObject::invokeMethod(panel.root.get(), "popOut");
  Settle();
  EXPECT_TRUE(panel.root->property("poppedOut").toBool());
  EXPECT_TRUE(popup->isVisible());

  popup->close();
  Settle();
  EXPECT_FALSE(panel.root->property("poppedOut").toBool());
  EXPECT_FALSE(popup->isVisible());

  // It can be opened again after closing.
  QMetaObject::invokeMethod(panel.root.get(), "popOut");
  Settle();
  EXPECT_TRUE(popup->isVisible());
}

int main(int argc, char ** argv)
{
  if (!qEnvironmentVariableIsSet("QT_QPA_PLATFORM"))
  {
    qputenv("QT_QPA_PLATFORM", "offscreen");
  }
  QGuiApplication app(argc, argv);
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
