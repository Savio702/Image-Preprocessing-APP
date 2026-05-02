import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPixmapCache
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QLabel, QSizePolicy, QVBoxLayout, QWidget


class ImagePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("imagePanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.s1 = QGraphicsScene(self)
        self.s2 = QGraphicsScene(self)
        self.v1 = QGraphicsView(self.s1)
        self.v2 = QGraphicsView(self.s2)
        self.v1.setObjectName("imageView")
        self.v2.setObjectName("imageView")
        self.v1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        original_title = QLabel("原始影像")
        processed_title = QLabel("處理後影像")
        original_title.setObjectName("sectionTitle")
        processed_title.setObjectName("sectionTitle")

        layout.addWidget(original_title)
        layout.addWidget(self.v1)
        layout.addWidget(processed_title)
        layout.addWidget(self.v2)

    def show(self, original, processed):
        if original is None or processed is None:
            self.clear()
            return
        self.draw(self.s1, self.v1, original)
        self.draw(self.s2, self.v2, processed)

    def draw(self, scene, view, img):
        scene.clear()
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        qimg = QImage(rgb.data, w, h, c * w, QImage.Format.Format_RGB888).copy()
        pixmap_item = scene.addPixmap(QPixmap.fromImage(qimg))
        scene.setSceneRect(pixmap_item.boundingRect())
        view.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def clear(self):
        self.s1.clear()
        self.s2.clear()
        self.s1.setSceneRect(0, 0, 0, 0)
        self.s2.setSceneRect(0, 0, 0, 0)

    def release_resources(self):
        self.clear()
        self.v1.setScene(None)
        self.v2.setScene(None)
        QPixmapCache.clear()
