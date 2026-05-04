import cv2
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


HISTOGRAM_MODES = [
    "灰階",
    "RGB 合併",
    "紅色 R",
    "綠色 G",
    "藍色 B",
    "HSV 色相 H",
    "HSV 飽和度 S",
    "HSV 明度 V",
]


class HistogramCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.original_series = []
        self.processed_series = []
        self._palette = {
            "background": QColor("#151a18"),
            "panel": QColor("#0c0f0e"),
            "grid": QColor("#2f3a36"),
            "frame": QColor("#3b4742"),
            "title": QColor("#e8f1ef"),
            "text": QColor("#b8c7c2"),
        }

    def set_histograms(self, original_series, processed_series):
        self.original_series = original_series
        self.processed_series = processed_series
        self.update()

    def clear(self):
        self.original_series = []
        self.processed_series = []
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self._palette["background"])

        outer = self.rect().adjusted(10, 6, -10, -6)
        gap = 12
        top_height = max(120, (outer.height() - gap) // 2)
        top_rect = QRectF(outer.left(), outer.top(), outer.width(), top_height)
        bottom_rect = QRectF(outer.left(), top_rect.bottom() + gap, outer.width(), outer.height() - top_height - gap)

        self.draw_chart(painter, top_rect, "原始影像", self.original_series)
        self.draw_chart(painter, bottom_rect, "處理後影像", self.processed_series)

    def draw_chart(self, painter, rect, title, series):
        painter.save()
        painter.setPen(QPen(self._palette["frame"], 1))
        painter.setBrush(self._palette["panel"])
        painter.drawRoundedRect(rect, 5, 5)

        title_rect = QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 18)
        painter.setPen(self._palette["title"])
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

        plot_rect = QRectF(rect.left() + 12, rect.top() + 32, rect.width() - 24, rect.height() - 46)
        self.draw_grid(painter, plot_rect)
        self.draw_series(painter, plot_rect, series)
        self.draw_axis_labels(painter, plot_rect)
        painter.restore()

    def draw_grid(self, painter, rect, foreground=False):
        painter.save()
        grid_color = QColor(self._palette["grid"])
        if foreground:
            grid_color.setAlpha(150)
        painter.setPen(QPen(grid_color, 1))
        for i in range(5):
            y = rect.top() + rect.height() * i / 4
            painter.drawLine(rect.left(), y, rect.right(), y)
        for i in range(5):
            x = rect.left() + rect.width() * i / 4
            painter.drawLine(x, rect.top(), x, rect.bottom())
        painter.restore()

    def draw_series(self, painter, rect, series):
        if not series:
            painter.save()
            painter.setPen(self._palette["text"])
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "尚無直方圖資料")
            painter.restore()
            return

        hist_maxes = [float(hist.max()) for hist, _color, _label in series if hist.size]
        if not hist_maxes:
            return

        is_overlay = len(series) > 1
        max_value = max(hist_maxes)
        max_value = max(max_value, 1.0)
        for idx, (hist, color, label) in enumerate(series):
            if hist.size == 0:
                continue
            painter.save()
            line_color = QColor(color)
            line_color.setAlpha(145 if is_overlay else 120)
            if is_overlay:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            pen = QPen(line_color, 1.7 if is_overlay else 1.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            for index, value in enumerate(hist):
                x = rect.left() + rect.width() * index / 255.0
                y = rect.bottom() - rect.height() * (float(value) / max_value)
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.drawPath(path)
            painter.restore()

        self.draw_grid(painter, rect, foreground=True)
        if len(series) > 1:
            for idx, (_hist, color, label) in enumerate(series):
                self.draw_legend(painter, rect, color, label, idx)

    def draw_legend(self, painter, rect, color, label, index):
        legend_x = rect.left() + 8 + index * 58
        legend_y = rect.top() + 8
        painter.save()
        painter.setPen(QPen(color, 2))
        painter.drawLine(legend_x, legend_y, legend_x + 16, legend_y)
        painter.setPen(self._palette["text"])
        painter.drawText(QRectF(legend_x + 20, legend_y - 8, 34, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
        painter.restore()

    def draw_axis_labels(self, painter, rect):
        painter.save()
        painter.setPen(self._palette["text"])
        painter.drawText(QRectF(rect.left(), rect.bottom() + 2, 24, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "0")
        painter.drawText(QRectF(rect.right() - 24, rect.bottom() + 2, 24, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "255")
        painter.restore()


class HistogramPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("histogramPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.original = None
        self.processed = None
        self._released = False
        self._original_cache_key = None
        self._original_cache_series = []
        self._processed_cache_key = None
        self._processed_cache_series = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("直方圖")
        title.setObjectName("sectionTitle")
        self.original_mode = self.create_mode_combo()
        self.processed_mode = self.create_mode_combo()
        self.processed_mode.setCurrentText("RGB 合併")
        self.original_mode.currentTextChanged.connect(self.redraw)
        self.processed_mode.currentTextChanged.connect(self.redraw)
        self.canvas = HistogramCanvas()

        layout.addWidget(title)
        layout.addLayout(self.create_mode_row("原始", self.original_mode))
        layout.addLayout(self.create_mode_row("處理後", self.processed_mode))
        layout.addWidget(self.canvas, 1)

    def create_mode_combo(self):
        combo = QComboBox()
        combo.addItems(HISTOGRAM_MODES)
        return combo

    def create_mode_row(self, label_text, combo):
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(48)
        row.addWidget(label)
        row.addWidget(combo, 1)
        return row

    def update(self, original, processed):
        if self._released:
            return
        self.original = original
        self.processed = processed
        self.redraw()

    def redraw(self):
        if self._released:
            return
        if self.original is None or self.processed is None:
            self.canvas.clear()
            return
        original_series = self.cached_histogram_series(
            self.original,
            self.original_mode.currentText(),
            "_original_cache_key",
            "_original_cache_series",
        )
        processed_series = self.cached_histogram_series(
            self.processed,
            self.processed_mode.currentText(),
            "_processed_cache_key",
            "_processed_cache_series",
        )
        self.canvas.set_histograms(original_series, processed_series)

    def cached_histogram_series(self, img, mode, key_attr, series_attr):
        key = (id(img), mode)
        if getattr(self, key_attr) != key:
            setattr(self, key_attr, key)
            setattr(self, series_attr, self.build_histogram_series(img, mode))
        return getattr(self, series_attr)

    def build_histogram_series(self, img, mode):
        if mode == "RGB 合併":
            channels = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            colors = (QColor("#ef4444"), QColor("#22c55e"), QColor("#3b82f6"))
            labels = ("R", "G", "B")
            return [
                (cv2.calcHist([channel], [0], None, [256], [0, 256]).ravel(), color, label)
                for channel, color, label in zip(channels, colors, labels)
            ]

        channel, color = self.extract_channel(img, mode)
        hist = cv2.calcHist([channel], [0], None, [256], [0, 256]).ravel()
        return [(hist, color, "")]

    def extract_channel(self, img, mode):
        if mode == "紅色 R":
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)[:, :, 0], QColor("#ef4444")
        if mode == "綠色 G":
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)[:, :, 1], QColor("#22c55e")
        if mode == "藍色 B":
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)[:, :, 2], QColor("#3b82f6")
        if mode == "HSV 色相 H":
            return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 0], QColor("#a855f7")
        if mode == "HSV 飽和度 S":
            return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1], QColor("#f97316")
        if mode == "HSV 明度 V":
            return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2], QColor("#14b8a6")
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), QColor("#f8fafc")

    def clear(self):
        self.original = None
        self.processed = None
        self._clear_cache()
        if self._released:
            return
        self.canvas.clear()

    def _clear_cache(self):
        self._original_cache_key = None
        self._original_cache_series = []
        self._processed_cache_key = None
        self._processed_cache_series = []

    def release_resources(self):
        if self._released:
            return
        self._released = True
        try:
            self.original_mode.currentTextChanged.disconnect(self.redraw)
            self.processed_mode.currentTextChanged.disconnect(self.redraw)
        except (RuntimeError, TypeError):
            pass
        self.original = None
        self.processed = None
        self._clear_cache()
        self.canvas.clear()
