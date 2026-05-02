import gc
import json
import sys

import cv2
import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QWidget

from histogram_panel import HistogramPanel
from image_panel import ImagePanel
from tool_panel import ToolPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("影像前處理流程工具")
        self.resize(1700, 900)
        self.setStyleSheet(APP_STYLE)

        self.original = None
        self._resources_released = False
        self.pipeline_timer = QTimer(self)
        self.pipeline_timer.setSingleShot(True)
        self.pipeline_timer.timeout.connect(self.run_pipeline)

        central = QWidget()
        central.setObjectName("centralPanel")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.tool_panel = ToolPanel(on_change=self.schedule_pipeline)
        self.image_panel = ImagePanel()
        self.hist_panel = HistogramPanel()

        layout.addWidget(self.tool_panel, 3)
        layout.addWidget(self.image_panel, 6)
        layout.addWidget(self.hist_panel, 3)
        self.setCentralWidget(central)

        btn = QPushButton("載入影像")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.load_image)
        import_btn = QPushButton("匯入流程")
        import_btn.setObjectName("actionButton")
        import_btn.clicked.connect(self.import_pipeline)
        export_btn = QPushButton("匯出流程")
        export_btn.setObjectName("actionButton")
        export_btn.clicked.connect(self.export_pipeline)
        exit_btn = QPushButton("結束程式")
        exit_btn.setObjectName("exitButton")
        exit_btn.clicked.connect(self.close)
        toolbar = self.addToolBar("檔案")
        toolbar.setMovable(False)
        toolbar.addWidget(btn)
        toolbar.addSeparator()
        toolbar.addWidget(import_btn)
        toolbar.addWidget(export_btn)
        toolbar.addSeparator()
        toolbar.addWidget(exit_btn)

    def load_image(self):
        if self._resources_released:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "開啟影像",
            "",
            "影像檔 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;所有檔案 (*)",
        )
        if not path:
            return

        self.original = self.read_image(path)
        if self.original is not None:
            self.run_pipeline()

    def export_pipeline(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出處理流程",
            "pipeline.json",
            "JSON 檔案 (*.json);;所有檔案 (*)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"

        data = {
            "format": "image-processing-pipeline",
            "version": 1,
            "pipeline": self.tool_panel.get_pipeline_data(),
        }
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.warning(self, "匯出失敗", f"無法寫入流程檔案：\n{exc}")

    def import_pipeline(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入處理流程",
            "",
            "JSON 檔案 (*.json);;所有檔案 (*)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            pipeline_items = data.get("pipeline", data) if isinstance(data, dict) else data
            if not isinstance(pipeline_items, list):
                raise ValueError("JSON 內容不是有效的處理流程格式")
            self.tool_panel.set_pipeline_data(pipeline_items)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            QMessageBox.warning(self, "匯入失敗", f"無法讀取流程檔案：\n{exc}")

    def read_image(self, path):
        data = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if image is None:
            return None

        if image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        return image

    def schedule_pipeline(self):
        if self._resources_released or self.original is None:
            return
        if not self.tool_panel.get_pipeline():
            if self.pipeline_timer.isActive():
                self.pipeline_timer.stop()
            self.run_pipeline()
            return
        self.pipeline_timer.start(90)

    def run_pipeline(self):
        if self._resources_released or self.original is None:
            return

        img = self.original.copy()
        for tool_id, params in self.tool_panel.get_pipeline():
            img = self.apply_tool(img, tool_id, params)

        self.image_panel.show(self.original, img)
        self.hist_panel.update(self.original, img)

    def apply_tool(self, img, tool_id, params):
        if tool_id == "Grayscale":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return self.gray_to_bgr(gray)

        if tool_id == "Color Negative":
            return cv2.bitwise_not(img)

        if tool_id == "Normalize Intensity":
            normalized = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
            return normalized.astype(np.uint8, copy=False)

        if tool_id == "Red Channel":
            return self.gray_to_bgr(img[:, :, 2])

        if tool_id == "Green Channel":
            return self.gray_to_bgr(img[:, :, 1])

        if tool_id == "Blue Channel":
            return self.gray_to_bgr(img[:, :, 0])

        if tool_id == "Binary Threshold":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, params["threshold"], params["max_value"], cv2.THRESH_BINARY)
            return self.gray_to_bgr(binary)

        if tool_id == "Otsu Threshold":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, params["max_value"], cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return self.gray_to_bgr(binary)

        if tool_id == "Adaptive Threshold":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            block_size = max(3, params["block_size"] | 1)
            binary = cv2.adaptiveThreshold(
                gray,
                params["max_value"],
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size,
                params["c"],
            )
            return self.gray_to_bgr(binary)

        if tool_id == "Histogram Equalization":
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
            return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

        if tool_id == "CLAHE":
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            tile_size = max(2, params["tile_size"])
            clahe = cv2.createCLAHE(
                clipLimit=max(0.1, params["clip_limit"] / 10),
                tileGridSize=(tile_size, tile_size),
            )
            ycrcb[:, :, 0] = clahe.apply(ycrcb[:, :, 0])
            return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

        if tool_id == "Gamma Correction":
            gamma = max(0.1, params["gamma"] / 100)
            table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)], dtype=np.uint8)
            return cv2.LUT(img, table)

        if tool_id == "Brightness / Contrast":
            return cv2.convertScaleAbs(img, alpha=max(0.1, params["alpha"] / 100), beta=params["beta"])

        if tool_id == "HSV Mask":
            return self.apply_hsv_mask(img, params)

        if tool_id == "Canny Edge":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            threshold1 = min(params["threshold1"], params["threshold2"])
            threshold2 = max(params["threshold1"], params["threshold2"])
            aperture = params["aperture"] if params["aperture"] in (3, 5, 7) else 3
            edges = cv2.Canny(gray, threshold1, threshold2, apertureSize=aperture)
            return self.gray_to_bgr(edges)

        if tool_id == "Sobel Edge":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            kernel_size = params["kernel_size"] | 1
            scale = params["scale"] / 10
            grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=kernel_size, scale=scale, delta=params["delta"])
            grad_y = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=kernel_size, scale=scale, delta=params["delta"])
            sobel = cv2.addWeighted(cv2.convertScaleAbs(grad_x), 0.5, cv2.convertScaleAbs(grad_y), 0.5, 0)
            return self.gray_to_bgr(sobel)

        if tool_id == "Scharr Edge":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            scale = params["scale"] / 10
            grad_x = cv2.Scharr(gray, cv2.CV_16S, 1, 0, scale=scale, delta=params["delta"])
            grad_y = cv2.Scharr(gray, cv2.CV_16S, 0, 1, scale=scale, delta=params["delta"])
            scharr = cv2.addWeighted(cv2.convertScaleAbs(grad_x), 0.5, cv2.convertScaleAbs(grad_y), 0.5, 0)
            return self.gray_to_bgr(scharr)

        if tool_id == "Prewitt Edge":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            scale = max(0.1, params["scale"] / 10)
            kernel_x = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32)
            kernel_y = np.array([[1, 1, 1], [0, 0, 0], [-1, -1, -1]], dtype=np.float32)
            grad_x = cv2.filter2D(gray, cv2.CV_32F, kernel_x)
            grad_y = cv2.filter2D(gray, cv2.CV_32F, kernel_y)
            magnitude = cv2.magnitude(grad_x, grad_y)
            return self.gray_to_bgr(cv2.convertScaleAbs(magnitude, alpha=scale))

        if tool_id == "Laplacian Edge":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            kernel_size = params["kernel_size"] | 1
            scale = params["scale"] / 10
            lap = cv2.Laplacian(gray, cv2.CV_16S, ksize=kernel_size, scale=scale, delta=params["delta"])
            return self.gray_to_bgr(cv2.convertScaleAbs(lap))

        if tool_id == "Hough Lines":
            return self.apply_hough_lines(img, params)

        if tool_id == "Hough Circles":
            return self.apply_hough_circles(img, params)

        if tool_id == "Average Blur":
            ksize = max(3, params["kernel_size"] | 1)
            return cv2.blur(img, (ksize, ksize))

        if tool_id == "Gaussian Blur":
            ksize = max(3, params["kernel_size"] | 1)
            return cv2.GaussianBlur(img, (ksize, ksize), params["sigma"] / 10)

        if tool_id == "Median Blur":
            ksize = max(3, params["kernel_size"] | 1)
            return cv2.medianBlur(img, ksize)

        if tool_id == "Bilateral Filter":
            diameter = max(1, params["diameter"] | 1)
            return cv2.bilateralFilter(img, diameter, params["sigma_color"], params["sigma_space"])

        if tool_id == "Frequency Low Pass":
            return self.apply_fft_filter(img, params["radius"], high_pass=False)

        if tool_id == "Frequency High Pass":
            return self.apply_fft_filter(img, params["radius"], high_pass=True)

        if tool_id == "Non-local Means":
            template_size = max(3, params["template_size"] | 1)
            search_size = max(template_size + 2, params["search_size"] | 1)
            if search_size % 2 == 0:
                search_size += 1
            return cv2.fastNlMeansDenoisingColored(
                img,
                None,
                params["h"],
                params["h"],
                template_size,
                search_size,
            )

        if tool_id == "Sharpen":
            amount = params["amount"] / 100
            blur_kernel = max(3, params["blur_kernel"] | 1)
            blurred = cv2.GaussianBlur(img, (blur_kernel, blur_kernel), 0)
            return cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)

        if tool_id in ("Erode", "Dilate", "Opening", "Closing", "Morph Gradient", "Top Hat", "Black Hat"):
            return self.apply_morphology(img, tool_id, params)

        if tool_id == "Resize Scale":
            scale = max(0.1, params["scale"] / 100)
            interpolations = (cv2.INTER_AREA, cv2.INTER_LINEAR, cv2.INTER_CUBIC)
            interpolation = interpolations[self.choice_index(params["interpolation"], interpolations)]
            return cv2.resize(img, None, fx=scale, fy=scale, interpolation=interpolation)

        if tool_id == "Rotate":
            return self.rotate_image(img, params["angle"])

        if tool_id == "Flip":
            flip_codes = (1, 0, -1)
            return cv2.flip(img, flip_codes[self.choice_index(params["direction"], flip_codes)])

        if tool_id == "FFT High Pass":
            return self.apply_fft_filter(img, params["radius"], high_pass=True)

        if tool_id == "FFT Low Pass":
            return self.apply_fft_filter(img, params["radius"], high_pass=False)

        return img

    def gray_to_bgr(self, gray):
        if gray.dtype != np.uint8:
            gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def choice_index(self, value, choices):
        return max(0, min(int(value), len(choices) - 1))

    def apply_hsv_mask(self, img, params):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h_min = max(0, min(179, params["h_min"]))
        h_max = max(0, min(179, params["h_max"]))
        s_min, s_max = sorted((max(0, min(255, params["s_min"])), max(0, min(255, params["s_max"]))))
        v_min, v_max = sorted((max(0, min(255, params["v_min"])), max(0, min(255, params["v_max"]))))

        if h_min <= h_max:
            lower = np.array([h_min, s_min, v_min], dtype=np.uint8)
            upper = np.array([h_max, s_max, v_max], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower, upper)
        else:
            lower_1 = np.array([h_min, s_min, v_min], dtype=np.uint8)
            upper_1 = np.array([179, s_max, v_max], dtype=np.uint8)
            lower_2 = np.array([0, s_min, v_min], dtype=np.uint8)
            upper_2 = np.array([h_max, s_max, v_max], dtype=np.uint8)
            mask = cv2.bitwise_or(cv2.inRange(hsv, lower_1, upper_1), cv2.inRange(hsv, lower_2, upper_2))
        return cv2.bitwise_and(img, img, mask=mask)

    def apply_morphology(self, img, tool_id, params):
        kernel = self.morph_kernel(params)
        iterations = max(1, int(params["iterations"]))
        if tool_id == "Erode":
            return cv2.erode(img, kernel, iterations=iterations)
        if tool_id == "Dilate":
            return cv2.dilate(img, kernel, iterations=iterations)

        operations = {
            "Opening": cv2.MORPH_OPEN,
            "Closing": cv2.MORPH_CLOSE,
            "Morph Gradient": cv2.MORPH_GRADIENT,
            "Top Hat": cv2.MORPH_TOPHAT,
            "Black Hat": cv2.MORPH_BLACKHAT,
        }
        return cv2.morphologyEx(img, operations[tool_id], kernel, iterations=iterations)

    def morph_kernel(self, params):
        shapes = (cv2.MORPH_RECT, cv2.MORPH_ELLIPSE, cv2.MORPH_CROSS)
        shape = shapes[self.choice_index(params.get("shape", 1), shapes)]
        size = max(3, params["kernel_size"] | 1)
        return cv2.getStructuringElement(shape, (size, size))

    def apply_hough_lines(self, img, params):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        low = min(params["canny_low"], params["canny_high"])
        high = max(params["canny_low"], params["canny_high"])
        edges = cv2.Canny(gray, low, high, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=params["threshold"],
            minLineLength=params["min_line_length"],
            maxLineGap=params["max_line_gap"],
        )

        output = img.copy()
        if lines is None:
            return output
        for x1, y1, x2, y2 in lines[:, 0]:
            cv2.line(output, (x1, y1), (x2, y2), (0, 255, 255), params["line_width"], cv2.LINE_AA)
        return output

    def apply_hough_circles(self, img, params):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        min_radius = int(params["min_radius"])
        max_radius = int(params["max_radius"])
        if max_radius > 0 and min_radius > max_radius:
            min_radius, max_radius = max_radius, min_radius

        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=max(1.0, params["dp"] / 10),
            minDist=max(1, params["min_dist"]),
            param1=params["canny_high"],
            param2=params["threshold"],
            minRadius=min_radius,
            maxRadius=max_radius,
        )

        output = img.copy()
        if circles is None:
            return output
        circles = np.uint16(np.around(circles[0]))
        for x, y, radius in circles:
            center = (int(x), int(y))
            cv2.circle(output, center, int(radius), (0, 255, 255), params["line_width"], cv2.LINE_AA)
            cv2.circle(output, center, 2, (0, 0, 255), -1, cv2.LINE_AA)
        return output

    def rotate_image(self, img, angle):
        if angle % 360 == 0:
            return img.copy()

        h, w = img.shape[:2]
        center = (w / 2, h / 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = abs(matrix[0, 0])
        sin = abs(matrix[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        matrix[0, 2] += (new_w / 2) - center[0]
        matrix[1, 2] += (new_h / 2) - center[1]
        return cv2.warpAffine(img, matrix, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def apply_fft_filter(self, img, radius, high_pass):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2
        max_radius = max(1, min(crow, ccol))
        radius = min(max(1, int(radius)), max_radius)

        spectrum = np.fft.fftshift(np.fft.fft2(gray))
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.circle(mask, (ccol, crow), radius, 1, -1)
        if high_pass:
            spectrum[mask == 1] = 0
        else:
            spectrum[mask == 0] = 0

        filtered = np.abs(np.fft.ifft2(np.fft.ifftshift(spectrum)))
        filtered = cv2.normalize(filtered, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return self.gray_to_bgr(filtered)

    def closeEvent(self, event):
        self.release_resources()
        super().closeEvent(event)

    def release_resources(self):
        if self._resources_released:
            return

        self._resources_released = True
        if self.pipeline_timer.isActive():
            self.pipeline_timer.stop()
        try:
            self.pipeline_timer.timeout.disconnect(self.run_pipeline)
        except (RuntimeError, TypeError):
            pass

        self.original = None
        if hasattr(self, "tool_panel"):
            self.tool_panel.release_resources()
        if hasattr(self, "image_panel"):
            self.image_panel.release_resources()
        if hasattr(self, "hist_panel"):
            self.hist_panel.release_resources()

        cv2.destroyAllWindows()
        gc.collect()


APP_STYLE = """
QMainWindow {
    background: #0e1110;
    color: #e8f1ef;
    font-family: "Microsoft JhengHei UI", "Microsoft JhengHei", "Segoe UI";
    font-size: 13px;
}

QToolBar {
    background: #1b2638;
    border: 0;
    border-bottom: 1px solid #26384f;
    padding: 6px;
    spacing: 8px;
}

QWidget#centralPanel,
QWidget#toolPanel,
QWidget#imagePanel,
QWidget#histogramPanel {
    background: #0e1110;
}

QLabel#sectionTitle {
    color: #69b7e6;
    font-size: 15px;
    font-weight: 700;
    padding: 0 0 4px 0;
}

QLabel#hintLabel {
    color: #8b9b96;
}

QLabel#valueLabel {
    color: #eaf6f3;
    font-weight: 700;
    background: #2b3431;
    border-radius: 4px;
    padding: 2px 6px;
}

QLineEdit#valueEditor {
    color: #eaf6f3;
    font-weight: 700;
    background: #151a18;
    border: 1px solid #4ba3d1;
    border-radius: 4px;
    padding: 2px 6px;
    selection-background-color: #0f7fb3;
    selection-color: #ffffff;
}

QLabel {
    color: #dce7e4;
}

QGroupBox {
    background: #1b201e;
    border: 1px solid #34403b;
    border-radius: 5px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #69b7e6;
    background: #0e1110;
}

QCheckBox {
    color: #dce7e4;
    spacing: 10px;
    min-height: 22px;
    padding-left: 2px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    margin-left: 1px;
}

QPushButton {
    background: #252d2a;
    color: #e8f1ef;
    border: 1px solid #3b4742;
    border-radius: 4px;
    padding: 5px 9px;
}

QPushButton:hover {
    background: #2f5f78;
    border-color: #4ba3d1;
}

QPushButton#primaryButton {
    background: #0f7fb3;
    color: white;
    border: 1px solid #1aa7df;
    font-weight: 700;
    padding: 7px 14px;
}

QPushButton#primaryButton:hover {
    background: #1596d1;
}

QPushButton#actionButton,
QPushButton#clearButton {
    background: #22313a;
    color: #e8f1ef;
    border: 1px solid #3e5968;
    font-weight: 700;
}

QPushButton#actionButton:hover,
QPushButton#clearButton:hover {
    background: #2f5f78;
    border-color: #4ba3d1;
}

QPushButton#exitButton {
    background: #3a262a;
    color: #fff1f2;
    border: 1px solid #7f3945;
    font-weight: 700;
    padding: 7px 14px;
}

QPushButton#exitButton:hover {
    background: #7f1d2d;
    border-color: #be4257;
}

QPushButton#moveButton {
    min-width: 42px;
    min-height: 28px;
    max-width: 42px;
    max-height: 28px;
    padding: 0;
    font-size: 14px;
    font-weight: 700;
}

QScrollArea,
QListWidget,
QGraphicsView#imageView {
    background: #151a18;
    color: #e8f1ef;
    border: 1px solid #34403b;
    border-radius: 5px;
}

QScrollArea#toolScroll,
QScrollArea#toolScroll QWidget#toolContainer,
QScrollArea#toolScroll > QWidget > QWidget {
    background: #151a18;
    color: #e8f1ef;
}

QScrollArea#toolScroll QCheckBox {
    min-height: 24px;
}

QListWidget {
    padding: 6px;
}

QListWidget::item {
    background: transparent;
    border: 0;
}

QWidget#pipelineItem {
    background: #1b201e;
    border: 1px solid #34403b;
    border-radius: 5px;
}

QWidget#pipelineItem QCheckBox {
    min-height: 24px;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #303a36;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #1aa7df;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #eaf6f3;
    border: 2px solid #1aa7df;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QComboBox {
    background: #151a18;
    border: 1px solid #34403b;
    border-radius: 4px;
    padding: 6px 8px;
    color: #e8f1ef;
    selection-background-color: #0f7fb3;
    selection-color: #ffffff;
}

QComboBox QAbstractItemView {
    background: #1b201e;
    color: #e8f1ef;
    selection-background-color: #0f7fb3;
    selection-color: #ffffff;
    border: 1px solid #34403b;
    outline: 0;
}

QScrollBar:vertical {
    background: #151a18;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3b4742;
    border-radius: 5px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #4b5a54;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #151a18;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #3b4742;
    border-radius: 5px;
    min-width: 28px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}
"""


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    app.aboutToQuit.connect(window.release_resources)
    window.show()
    try:
        sys.exit(app.exec())
    finally:
        window.release_resources()
        cv2.destroyAllWindows()
        app.processEvents()
