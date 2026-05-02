from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)


TOOL_GROUPS = [
    ("閾值與色調", [
        ("Grayscale", "灰階轉換"),
        ("Color Negative", "負片反相"),
        ("Normalize Intensity", "強度正規化"),
        ("Binary Threshold", "二值化閾值"),
        ("Otsu Threshold", "Otsu 自動閾值"),
        ("Adaptive Threshold", "自適應閾值"),
        ("Histogram Equalization", "直方圖均衡化"),
        ("CLAHE", "CLAHE 局部均衡"),
        ("Gamma Correction", "Gamma 校正"),
        ("Brightness / Contrast", "亮度 / 對比"),
    ]),
    ("色彩與通道", [
        ("Red Channel", "紅色通道"),
        ("Green Channel", "綠色通道"),
        ("Blue Channel", "藍色通道"),
        ("HSV Mask", "HSV 範圍遮罩"),
    ]),
    ("邊緣偵測", [
        ("Canny Edge", "Canny 邊緣"),
        ("Sobel Edge", "Sobel 邊緣"),
        ("Scharr Edge", "Scharr 邊緣"),
        ("Prewitt Edge", "Prewitt 邊緣"),
        ("Laplacian Edge", "Laplacian 邊緣"),
        ("Hough Lines", "霍夫線段"),
        ("Hough Circles", "霍夫圓形"),
    ]),
    ("模糊與降噪", [
        ("Average Blur", "平均模糊"),
        ("Gaussian Blur", "高斯模糊"),
        ("Median Blur", "中值濾波"),
        ("Bilateral Filter", "雙邊濾波"),
        ("Frequency Low Pass", "頻率域低通濾波器"),
        ("Frequency High Pass", "頻率域高通濾波器"),
        ("Non-local Means", "非局部平均降噪"),
        ("Sharpen", "銳化"),
    ]),
    ("形態學處理", [
        ("Erode", "侵蝕"),
        ("Dilate", "膨脹"),
        ("Opening", "開運算"),
        ("Closing", "閉運算"),
        ("Morph Gradient", "形態梯度"),
        ("Top Hat", "頂帽"),
        ("Black Hat", "黑帽"),
    ]),
    ("幾何轉換", [
        ("Resize Scale", "縮放"),
        ("Rotate", "旋轉"),
        ("Flip", "翻轉"),
    ]),
    ("頻域處理", [
        ("FFT High Pass", "FFT 高通濾波"),
        ("FFT Low Pass", "FFT 低通濾波"),
    ]),
]


KERNEL_SHAPE_CHOICES = ["矩形", "橢圓", "十字"]
INTERPOLATION_CHOICES = ["區域", "線性", "三次"]
FLIP_DIRECTION_CHOICES = ["水平", "垂直", "水平 + 垂直"]

MORPH_PARAMS = [
    {"key": "kernel_size", "label": "核心大小", "min": 3, "max": 51, "default": 5, "odd": True},
    {"key": "iterations", "label": "次數", "min": 1, "max": 10, "default": 1},
    {"key": "shape", "label": "核心形狀", "min": 0, "max": 2, "default": 1, "choices": KERNEL_SHAPE_CHOICES},
]


TOOL_PARAMS = {
    "Grayscale": [],
    "Color Negative": [],
    "Normalize Intensity": [],
    "Histogram Equalization": [],
    "Red Channel": [],
    "Green Channel": [],
    "Blue Channel": [],
    "Binary Threshold": [
        {"key": "threshold", "label": "閾值", "min": 0, "max": 255, "default": 127},
        {"key": "max_value", "label": "最大值", "min": 1, "max": 255, "default": 255},
    ],
    "Otsu Threshold": [
        {"key": "max_value", "label": "最大值", "min": 1, "max": 255, "default": 255},
    ],
    "Adaptive Threshold": [
        {"key": "block_size", "label": "區塊大小", "min": 3, "max": 51, "default": 11, "odd": True},
        {"key": "c", "label": "偏移 C", "min": -20, "max": 20, "default": 2},
        {"key": "max_value", "label": "最大值", "min": 1, "max": 255, "default": 255},
    ],
    "CLAHE": [
        {"key": "clip_limit", "label": "裁切限制", "min": 10, "max": 100, "default": 20, "scale": 10},
        {"key": "tile_size", "label": "網格大小", "min": 2, "max": 32, "default": 8},
    ],
    "Gamma Correction": [
        {"key": "gamma", "label": "Gamma", "min": 10, "max": 300, "default": 100, "scale": 100},
    ],
    "Brightness / Contrast": [
        {"key": "alpha", "label": "對比", "min": 10, "max": 300, "default": 100, "scale": 100},
        {"key": "beta", "label": "亮度", "min": -100, "max": 100, "default": 0},
    ],
    "HSV Mask": [
        {"key": "h_min", "label": "H 下限", "min": 0, "max": 179, "default": 0},
        {"key": "h_max", "label": "H 上限", "min": 0, "max": 179, "default": 179},
        {"key": "s_min", "label": "S 下限", "min": 0, "max": 255, "default": 0},
        {"key": "s_max", "label": "S 上限", "min": 0, "max": 255, "default": 255},
        {"key": "v_min", "label": "V 下限", "min": 0, "max": 255, "default": 0},
        {"key": "v_max", "label": "V 上限", "min": 0, "max": 255, "default": 255},
    ],
    "Canny Edge": [
        {"key": "threshold1", "label": "低閾值", "min": 0, "max": 500, "default": 50},
        {"key": "threshold2", "label": "高閾值", "min": 0, "max": 500, "default": 150},
        {"key": "aperture", "label": "核心大小", "min": 3, "max": 7, "default": 3, "odd": True},
    ],
    "Sobel Edge": [
        {"key": "kernel_size", "label": "核心大小", "min": 1, "max": 7, "default": 3, "odd": True},
        {"key": "scale", "label": "縮放", "min": 1, "max": 50, "default": 10, "scale": 10},
        {"key": "delta", "label": "偏移", "min": 0, "max": 100, "default": 0},
    ],
    "Scharr Edge": [
        {"key": "scale", "label": "縮放", "min": 1, "max": 50, "default": 10, "scale": 10},
        {"key": "delta", "label": "偏移", "min": 0, "max": 100, "default": 0},
    ],
    "Prewitt Edge": [
        {"key": "scale", "label": "縮放", "min": 1, "max": 50, "default": 10, "scale": 10},
    ],
    "Laplacian Edge": [
        {"key": "kernel_size", "label": "核心大小", "min": 1, "max": 7, "default": 3, "odd": True},
        {"key": "scale", "label": "縮放", "min": 1, "max": 50, "default": 10, "scale": 10},
        {"key": "delta", "label": "偏移", "min": 0, "max": 100, "default": 0},
    ],
    "Hough Lines": [
        {"key": "canny_low", "label": "Canny 低閾值", "min": 0, "max": 500, "default": 50},
        {"key": "canny_high", "label": "Canny 高閾值", "min": 0, "max": 500, "default": 150},
        {"key": "threshold", "label": "投票閾值", "min": 1, "max": 300, "default": 80},
        {"key": "min_line_length", "label": "最短線段", "min": 1, "max": 500, "default": 50},
        {"key": "max_line_gap", "label": "最大間隔", "min": 0, "max": 200, "default": 10},
        {"key": "line_width", "label": "線寬", "min": 1, "max": 10, "default": 2},
    ],
    "Hough Circles": [
        {"key": "dp", "label": "解析比例", "min": 10, "max": 30, "default": 12, "scale": 10},
        {"key": "min_dist", "label": "最小距離", "min": 1, "max": 300, "default": 40},
        {"key": "canny_high", "label": "Canny 高閾值", "min": 1, "max": 500, "default": 120},
        {"key": "threshold", "label": "投票閾值", "min": 1, "max": 100, "default": 30},
        {"key": "min_radius", "label": "最小半徑", "min": 0, "max": 300, "default": 0},
        {"key": "max_radius", "label": "最大半徑", "min": 0, "max": 500, "default": 0},
        {"key": "line_width", "label": "線寬", "min": 1, "max": 10, "default": 2},
    ],
    "Average Blur": [
        {"key": "kernel_size", "label": "核心大小", "min": 3, "max": 51, "default": 5, "odd": True},
    ],
    "Gaussian Blur": [
        {"key": "kernel_size", "label": "核心大小", "min": 3, "max": 51, "default": 5, "odd": True},
        {"key": "sigma", "label": "Sigma", "min": 0, "max": 100, "default": 0, "scale": 10},
    ],
    "Median Blur": [
        {"key": "kernel_size", "label": "核心大小", "min": 3, "max": 51, "default": 5, "odd": True},
    ],
    "Bilateral Filter": [
        {"key": "diameter", "label": "直徑", "min": 1, "max": 31, "default": 9, "odd": True},
        {"key": "sigma_color", "label": "色彩 Sigma", "min": 1, "max": 200, "default": 75},
        {"key": "sigma_space", "label": "空間 Sigma", "min": 1, "max": 200, "default": 75},
    ],
    "Frequency Low Pass": [
        {"key": "radius", "label": "半徑", "min": 1, "max": 200, "default": 30},
    ],
    "Frequency High Pass": [
        {"key": "radius", "label": "半徑", "min": 1, "max": 200, "default": 10},
    ],
    "Non-local Means": [
        {"key": "h", "label": "降噪強度", "min": 1, "max": 30, "default": 10},
        {"key": "template_size", "label": "樣板大小", "min": 3, "max": 15, "default": 7, "odd": True},
        {"key": "search_size", "label": "搜尋大小", "min": 7, "max": 31, "default": 21, "odd": True},
    ],
    "Sharpen": [
        {"key": "amount", "label": "銳化量", "min": 0, "max": 300, "default": 100, "scale": 100},
        {"key": "blur_kernel", "label": "模糊核心", "min": 3, "max": 21, "default": 3, "odd": True},
    ],
    "Erode": MORPH_PARAMS,
    "Dilate": MORPH_PARAMS,
    "Opening": MORPH_PARAMS,
    "Closing": MORPH_PARAMS,
    "Morph Gradient": MORPH_PARAMS,
    "Top Hat": MORPH_PARAMS,
    "Black Hat": MORPH_PARAMS,
    "Resize Scale": [
        {"key": "scale", "label": "比例", "min": 10, "max": 200, "default": 100, "scale": 100},
        {"key": "interpolation", "label": "插值", "min": 0, "max": 2, "default": 1, "choices": INTERPOLATION_CHOICES},
    ],
    "Rotate": [
        {"key": "angle", "label": "角度", "min": -180, "max": 180, "default": 0},
    ],
    "Flip": [
        {"key": "direction", "label": "方向", "min": 0, "max": 2, "default": 0, "choices": FLIP_DIRECTION_CHOICES},
    ],
    "FFT High Pass": [
        {"key": "radius", "label": "半徑", "min": 1, "max": 200, "default": 10},
    ],
    "FFT Low Pass": [
        {"key": "radius", "label": "半徑", "min": 1, "max": 200, "default": 30},
    ],
}


def default_params(tool_id):
    return {param["key"]: param["default"] for param in TOOL_PARAMS.get(tool_id, [])}


def tool_labels():
    labels = {}
    for _group_title, entries in TOOL_GROUPS:
        for tool_id, label in entries:
            labels[tool_id] = label
    return labels


TOOL_LABELS = tool_labels()


def display_value(param, value):
    if "choices" in param:
        choices = param["choices"]
        if 0 <= value < len(choices):
            return choices[value]
        return str(value)
    if "scale" not in param:
        return str(value)
    scaled = value / param["scale"]
    return f"{scaled:.2f}".rstrip("0").rstrip(".")


class EditableValueLabel(QLabel):
    def __init__(self, text, activate_callback):
        super().__init__(text)
        self.activate_callback = activate_callback

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activate_callback()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class PipelineItemWidget(QWidget):
    def __init__(self, step_number, tool_id, label, params, changed_callback):
        super().__init__()
        self.tool_id = tool_id
        self.label = label
        self.params = deepcopy(params)
        self.changed_callback = changed_callback
        self.param_widgets = {}
        self.setObjectName("pipelineItem")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(7)
        top = QHBoxLayout()

        self.cb = QCheckBox(f"{step_number}. {label}")
        self.cb.setMinimumHeight(24)
        self.cb.setChecked(True)
        self.cb.stateChanged.connect(lambda _: self.changed_callback())

        self.up = QPushButton("上")
        self.down = QPushButton("下")
        self.up.setObjectName("moveButton")
        self.down.setObjectName("moveButton")
        self.up.setFixedSize(42, 28)
        self.down.setFixedSize(42, 28)

        top.addWidget(self.cb)
        top.addStretch()
        top.addWidget(self.up)
        top.addWidget(self.down)
        layout.addLayout(top)

        params_config = TOOL_PARAMS.get(tool_id, [])
        if not params_config:
            empty = QLabel("無可調參數")
            empty.setObjectName("hintLabel")
            layout.addWidget(empty)
            return

        for param in params_config:
            row = QHBoxLayout()
            label_widget = QLabel(param["label"])
            label_widget.setMinimumWidth(74)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(param["min"], param["max"])
            slider.setSingleStep(2 if param.get("odd") else 1)
            slider.setPageStep(2 if param.get("odd") else 10)
            slider.setValue(self.params[param["key"]])

            value = EditableValueLabel(
                display_value(param, self.params[param["key"]]),
                lambda key=param["key"]: self.start_value_edit(key),
            )
            value.setObjectName("valueLabel")
            value.setMinimumWidth(44)

            editor = QLineEdit(str(self.params[param["key"]]))
            editor.setObjectName("valueEditor")
            editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
            editor.setMinimumWidth(44)
            editor.hide()
            if "choices" in param:
                editor.setReadOnly(True)
            else:
                editor.setValidator(QIntValidator(param["min"], param["max"], editor))
                editor.editingFinished.connect(lambda key=param["key"]: self.finish_value_edit(key))
                editor.returnPressed.connect(lambda key=param["key"]: self.finish_value_edit(key))

            row.addWidget(label_widget)
            row.addWidget(slider)
            row.addWidget(value)
            row.addWidget(editor)
            layout.addLayout(row)

            self.param_widgets[param["key"]] = {
                "slider": slider,
                "label": value,
                "editor": editor,
                "param": param,
            }
            slider.valueChanged.connect(lambda v, key=param["key"]: self.on_param_changed(key, v))

    def on_param_changed(self, key, value):
        widgets = self.param_widgets[key]
        slider = widgets["slider"]
        value_label = widgets["label"]
        value_editor = widgets["editor"]
        param = widgets["param"]
        if param.get("odd") and value % 2 == 0:
            value = value + 1 if value < param["max"] else value - 1
            previous = slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(previous)

        self.params[key] = value
        value_label.setText(display_value(param, value))
        value_editor.setText(str(value))
        self.changed_callback()

    def start_value_edit(self, key):
        widgets = self.param_widgets[key]
        param = widgets["param"]
        if "choices" in param:
            return

        widgets["label"].hide()
        widgets["editor"].setText(str(self.params[key]))
        widgets["editor"].show()
        widgets["editor"].setFocus()
        widgets["editor"].selectAll()

    def finish_value_edit(self, key):
        widgets = self.param_widgets[key]
        editor = widgets["editor"]
        if editor.isHidden():
            return

        param = widgets["param"]
        raw_text = editor.text().strip()
        try:
            value = int(raw_text)
        except ValueError:
            value = self.params[key]

        value = max(param["min"], min(param["max"], value))
        if param.get("odd") and value % 2 == 0:
            value = value + 1 if value < param["max"] else value - 1

        previous = widgets["slider"].blockSignals(True)
        widgets["slider"].setValue(value)
        widgets["slider"].blockSignals(previous)
        self.params[key] = value
        widgets["label"].setText(display_value(param, value))
        editor.setText(str(value))
        editor.hide()
        widgets["label"].show()
        self.changed_callback()


class ToolPanel(QWidget):
    def __init__(self, on_change):
        super().__init__()
        self.on_change = on_change
        self.library_checks = {}
        self.pipeline_items = []
        self.setObjectName("toolPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        title = QLabel("工具庫")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setObjectName("toolScroll")
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("toolContainer")
        tools = QVBoxLayout(container)
        tools.setContentsMargins(14, 14, 14, 14)
        tools.setSpacing(10)

        for title_text, entries in TOOL_GROUPS:
            box = QGroupBox(title_text)
            group_layout = QVBoxLayout(box)
            group_layout.setContentsMargins(18, 18, 14, 12)
            group_layout.setSpacing(6)
            for tool_id, label in entries:
                cb = QCheckBox(label)
                cb.setMinimumHeight(23)
                cb.stateChanged.connect(
                    lambda state, tid=tool_id, text=label: self.toggle_tool(tid, text, state)
                )
                self.library_checks[tool_id] = cb
                group_layout.addWidget(cb)
            tools.addWidget(box)

        tools.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, 3)

        pipeline_header = QHBoxLayout()
        pipeline_title = QLabel("處理流程")
        pipeline_title.setObjectName("sectionTitle")
        self.clear_button = QPushButton("全部清除")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.clear_pipeline)
        pipeline_header.addWidget(pipeline_title)
        pipeline_header.addStretch()
        pipeline_header.addWidget(self.clear_button)
        root.addLayout(pipeline_header)

        self.pipeline = QListWidget()
        self.pipeline.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.pipeline.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        root.addWidget(self.pipeline, 2)

    def toggle_tool(self, tool_id, label, state):
        if state == Qt.CheckState.Checked or state == Qt.CheckState.Checked.value:
            self.add_tool(tool_id, label)
        else:
            self.remove_tool(tool_id)
        self.on_change()

    def add_tool(self, tool_id, label):
        if self.find_index(tool_id) is not None:
            return

        self.pipeline_items.append({
            "tool_id": tool_id,
            "label": label,
            "enabled": True,
            "params": default_params(tool_id),
        })
        self.rebuild_pipeline()

    def remove_tool(self, tool_id):
        index = self.find_index(tool_id)
        if index is None:
            return
        self.pipeline_items.pop(index)
        self.rebuild_pipeline()

    def find_index(self, tool_id):
        for index, data in enumerate(self.pipeline_items):
            if data["tool_id"] == tool_id:
                return index
        return None

    def rebuild_pipeline(self):
        self.pipeline.clear()
        for index, data in enumerate(self.pipeline_items, start=1):
            self.add_pipeline_row(index, data)

    def add_pipeline_row(self, step_number, data):
        item = QListWidgetItem()
        widget = PipelineItemWidget(
            step_number,
            data["tool_id"],
            data["label"],
            data["params"],
            self.pipeline_item_changed,
        )
        previous_cb = widget.cb.blockSignals(True)
        widget.cb.setChecked(data["enabled"])
        widget.cb.blockSignals(previous_cb)
        item.setSizeHint(widget.sizeHint())
        self.pipeline.addItem(item)
        self.pipeline.setItemWidget(item, widget)
        widget.up.clicked.connect(lambda _, tid=data["tool_id"]: self.move(tid, -1))
        widget.down.clicked.connect(lambda _, tid=data["tool_id"]: self.move(tid, 1))

    def pipeline_item_changed(self):
        for row in range(self.pipeline.count()):
            item = self.pipeline.item(row)
            widget = self.pipeline.itemWidget(item)
            if not widget:
                continue
            index = self.find_index(widget.tool_id)
            if index is not None:
                self.pipeline_items[index]["enabled"] = widget.cb.isChecked()
                self.pipeline_items[index]["params"] = deepcopy(widget.params)
        self.on_change()

    def move(self, tool_id, direction):
        row = self.find_index(tool_id)
        if row is None:
            return
        new_row = row + direction
        if not (0 <= new_row < len(self.pipeline_items)):
            return

        self.pipeline_items[row], self.pipeline_items[new_row] = self.pipeline_items[new_row], self.pipeline_items[row]
        self.rebuild_pipeline()
        self.on_change()

    def get_pipeline(self):
        result = []
        for data in self.pipeline_items:
            if data["enabled"]:
                result.append((data["tool_id"], deepcopy(data["params"])))
        return result

    def get_pipeline_data(self):
        self.pipeline_item_changed_without_notify()
        return deepcopy(self.pipeline_items)

    def pipeline_item_changed_without_notify(self):
        for row in range(self.pipeline.count()):
            item = self.pipeline.item(row)
            widget = self.pipeline.itemWidget(item)
            if not widget:
                continue
            index = self.find_index(widget.tool_id)
            if index is not None:
                self.pipeline_items[index]["enabled"] = widget.cb.isChecked()
                self.pipeline_items[index]["params"] = deepcopy(widget.params)

    def set_pipeline_data(self, pipeline_items):
        cleaned = []
        seen = set()
        for raw_item in pipeline_items:
            if not isinstance(raw_item, dict):
                continue
            tool_id = raw_item.get("tool_id")
            if tool_id not in TOOL_PARAMS or tool_id in seen:
                continue
            seen.add(tool_id)
            cleaned.append({
                "tool_id": tool_id,
                "label": TOOL_LABELS.get(tool_id, raw_item.get("label", tool_id)),
                "enabled": bool(raw_item.get("enabled", True)),
                "params": self.normalize_params(tool_id, raw_item.get("params", {})),
            })

        self.pipeline_items = cleaned
        self.sync_library_checks()
        self.rebuild_pipeline()
        self.on_change()

    def normalize_params(self, tool_id, params):
        normalized = default_params(tool_id)
        for param in TOOL_PARAMS.get(tool_id, []):
            key = param["key"]
            value = params.get(key, normalized[key])
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = normalized[key]
            value = max(param["min"], min(param["max"], value))
            if param.get("odd") and value % 2 == 0:
                value = value + 1 if value < param["max"] else value - 1
            normalized[key] = value
        return normalized

    def sync_library_checks(self):
        active_tools = {data["tool_id"] for data in self.pipeline_items}
        for tool_id, cb in self.library_checks.items():
            previous = cb.blockSignals(True)
            cb.setChecked(tool_id in active_tools)
            cb.blockSignals(previous)

    def clear_pipeline(self, notify=True):
        for cb in self.library_checks.values():
            previous = cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(previous)
        self.pipeline_items.clear()
        self.pipeline.clear()
        if notify:
            self.on_change()

    def release_resources(self):
        self.clear_pipeline(notify=False)
