from PySide2.QtWidgets import QApplication
from PySide2.QtQuick import QQuickView
from PySide2.QtCore import QUrl, Qt, QObject, Signal, QCoreApplication
from PySide2.QtGui import QSurfaceFormat, QSurface, QColor


class UIBackend(QObject):
    onOverlayInfoAdded = Signal("QVariant")
    onOverlayInfoCleared = Signal()


class LabelManager:
    """Displays overlays with tooltips."""

    def __init__(self, toggle_input_transparency):
        self.views = []
        self.toggle_input_transparency = toggle_input_transparency

    def start(self):
        self.backend = UIBackend()
        self.infos = []
        self.app = QApplication([])

        view = QQuickView()
        view.rootContext().setContextProperty("backend", self.backend)

        view.setFlags(view.flags() | Qt.WindowStaysOnTopHint)

        view.setSurfaceType(QSurface.OpenGLSurface)

        surface_format = QSurfaceFormat()
        surface_format.setAlphaBufferSize(8)
        surface_format.setRenderableType(QSurfaceFormat.OpenGL)

        view.setFormat(surface_format)
        view.setColor(QColor(Qt.transparent))
        view.setClearBeforeRendering(True)

        view.setSource(QUrl("ui/views/overlay.qml"))

        view.show()

        self.view = view
        return self.app.exec_()

    def reset(self):
        self.backend.onOverlayInfoCleared.emit()
        self.infos.clear()

        if self.toggle_input_transparency:
            self.view.setFlags(self.view.flags() |
                               Qt.WindowTransparentForInput)

    def add(self, position, text, tooltip):
        info = {
            "position": list(position),
            "text": text,
            "tooltip": tooltip
        }

        if self.toggle_input_transparency:
            self.view.setFlags(self.view.flags() &
                               ~Qt.WindowTransparentForInput)

        self.infos.append(info)

        self.backend.onOverlayInfoAdded.emit(info)

    def get_monitor(self):
        return {
            "left": self.view.x(),
            "top": self.view.y(),
            "width": self.view.width(),
            "height": self.view.height()
        }
