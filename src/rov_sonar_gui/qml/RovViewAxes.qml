// SPDX-License-Identifier: Apache-2.0
// XYZ orientation indicator for the 3D view (X red, Y green, Z blue).
import QtQuick
import QtQuick.Layouts

Item {
  Layout.minimumWidth: 84
  Layout.minimumHeight: 84
  anchors.fill: parent

  Canvas {
    id: canvas
    anchors.fill: parent
    antialiasing: true
    property var axes: _RovViewAxes.axes
    onAxesChanged: requestPaint()

    onPaint: {
      var ctx = getContext("2d");
      ctx.reset();
      var cx = width / 2, cy = height / 2;
      var length = Math.min(width, height) * 0.30;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.font = "bold 11px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      // Axes arrive farthest first, so nearer axes are drawn on top. A light
      // halo keeps them legible over both bright and dark scenes.
      for (var i = 0; i < axes.length; ++i) {
        var a = axes[i];
        var x = cx + a.x * length, y = cy + a.y * length;
        var n = Math.sqrt(a.x * a.x + a.y * a.y);
        var ux = n > 0.15 ? a.x / n : 0.7, uy = n > 0.15 ? a.y / n : -0.7;
        var lx = x + ux * 9, ly = y + uy * 9;
        ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.lineWidth = 3;
        ctx.strokeText(a.label, lx, ly);
        ctx.strokeStyle = a.color;
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.fillStyle = a.color;
        ctx.fillText(a.label, lx, ly);
      }
      ctx.fillStyle = "#3a3a3a";
      ctx.beginPath();
      ctx.arc(cx, cy, 1.8, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
}
