// SPDX-License-Identifier: Apache-2.0
// Image panel: title bar with an enlarge button. Enlarging opens the image in
// a separate window; closing that window returns it to this panel.
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window

Item {
  id: root
  anchors.fill: parent
  Layout.minimumWidth: 430
  Layout.minimumHeight: header.height + 2 * margin + (Layout.minimumWidth - 2 * margin) * _RovImageView.aspect

  readonly property int margin: 8
  property bool poppedOut: false
  // Same colours as the plugin title bars of the window theme.
  readonly property color barColor: _MainWindow.pluginToolBarColorLight !== "" ?
    _MainWindow.pluginToolBarColorLight : Material.accent
  readonly property color barText: _MainWindow.pluginToolBarTextColorLight !== "" ?
    _MainWindow.pluginToolBarTextColorLight : "white"

  function popOut() {
    poppedOut = true;
    popup.show();
    popup.raise();
    popup.requestActivate();
  }

  Rectangle {
    id: header
    anchors { left: parent.left; right: parent.right; top: parent.top }
    height: 40
    color: root.barColor

    Text {
      anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
      text: _RovImageView.caption
      color: root.barText
      font.pixelSize: 16
    }

    Rectangle {
      id: enlarge
      anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
      width: 30; height: 30; radius: 15
      color: area.containsMouse ? Qt.rgba(1, 1, 1, 0.22) : "transparent"

      // Expand icon: four corner brackets; inward brackets once popped out.
      Canvas {
        id: icon
        anchors.centerIn: parent
        width: 16; height: 16
        property bool inward: root.poppedOut
        property color ink: root.barText
        onInwardChanged: requestPaint()
        onInkChanged: requestPaint()
        onPaint: {
          var ctx = getContext("2d");
          ctx.reset();
          ctx.strokeStyle = ink;
          ctx.lineWidth = 2;
          ctx.lineCap = "square";
          var a = 1, b = 6, c = 15;
          var corners = inward ?
            [[b, a, b, b, a, b], [c - b + a, a, c - b + a, b, c, b],
             [a, c - b + a, b, c - b + a, b, c], [c, c - b + a, c - b + a, c - b + a, c - b + a, c]] :
            [[a, b, a, a, b, a], [c - b + a, a, c, a, c, b],
             [a, c - b + a, a, c, b, c], [c, c - b + a, c, c, c - b + a, c]];
          for (var i = 0; i < corners.length; ++i) {
            var p = corners[i];
            ctx.beginPath();
            ctx.moveTo(p[0], p[1]);
            ctx.lineTo(p[2], p[3]);
            ctx.lineTo(p[4], p[5]);
            ctx.stroke();
          }
        }
      }

      MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.poppedOut ? popup.close() : root.popOut()
      }

      ToolTip.visible: area.containsMouse
      ToolTip.delay: 500
      ToolTip.text: root.poppedOut ? qsTr("Return to the main window") : qsTr("Open in a separate window")
    }
  }

  Image {
    anchors { left: parent.left; right: parent.right; top: header.bottom; bottom: parent.bottom; margins: root.margin }
    visible: !root.poppedOut
    source: root.poppedOut ? "" : _RovImageView.source
    fillMode: Image.PreserveAspectFit
    verticalAlignment: Image.AlignTop
    cache: false
    smooth: true
  }

  Text {
    anchors { horizontalCenter: parent.horizontalCenter; top: header.bottom; topMargin: 24 }
    visible: root.poppedOut
    text: qsTr("Shown in a separate window")
    color: "#8a8a8a"
    font.pixelSize: 13
  }

  Window {
    id: popup
    title: _RovImageView.caption
    color: _RovImageView.windowColor
    width: 960
    height: Math.round(960 * _RovImageView.aspect)
    minimumWidth: 320
    minimumHeight: 200
    onClosing: root.poppedOut = false

    Image {
      anchors.fill: parent
      source: root.poppedOut ? _RovImageView.source : ""
      fillMode: Image.PreserveAspectFit
      cache: false
      smooth: true
      mipmap: true
    }

    Shortcut {
      sequence: "Esc"
      onActivated: popup.close()
    }
  }
}
