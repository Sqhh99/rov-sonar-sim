#!/usr/bin/env python3
"""Plain window (no toolbars) showing the sonar fan image.

Closing the window stops this node only; the simulation keeps running.
"""
import sys

import rclpy
from PyQt6.QtCore import QRectF, QTimer
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication, QWidget
from rclpy.node import Node
from sensor_msgs.msg import Image

PAGE = QColor(32, 32, 32)  # Matches the sonar_view page colour.


class SonarWindow(QWidget):
    def __init__(self, node):
        super().__init__()
        self.image = None
        self.setWindowTitle("Sonar")
        self.resize(800, 500)
        node.create_subscription(Image, "image", self.receive, 1)

    def receive(self, message):
        if message.encoding != "rgb8":
            return
        self.image = QImage(bytes(message.data), message.width, message.height, message.step,
                            QImage.Format.Format_RGB888).copy()
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), PAGE)
        if self.image is None:
            return
        scale = min(self.width() / self.image.width(), self.height() / self.image.height())
        w, h = self.image.width() * scale, self.image.height() * scale
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h), self.image)


def main():
    rclpy.init(args=sys.argv)
    node = Node("sonar_window")
    app = QApplication(sys.argv[:1])
    window = SonarWindow(node)
    window.show()

    def poll():
        # rclpy's signal handlers shut the context down on Ctrl+C / SIGTERM.
        try:
            rclpy.spin_once(node, timeout_sec=0)
        except Exception:
            if rclpy.ok():
                raise
        if not rclpy.ok():
            app.quit()

    spin = QTimer(timeout=poll)
    spin.start(20)
    try:
        app.exec()
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
