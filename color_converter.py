import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGroupBox, QSlider, QLineEdit, 
                               QLabel, QPushButton, QColorDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

class ColorConverter:
    @staticmethod
    def rgb_to_cmyk(r, g, b):
        if r == 0 and g == 0 and b == 0:
            return 0, 0, 0, 100
        
        r_norm = r / 255.0
        g_norm = g / 255.0
        b_norm = b / 255.0
        
        k = 1 - max(r_norm, g_norm, b_norm)
        c = (1 - r_norm - k) / (1 - k) if (1 - k) != 0 else 0
        m = (1 - g_norm - k) / (1 - k) if (1 - k) != 0 else 0
        y = (1 - b_norm - k) / (1 - k) if (1 - k) != 0 else 0
        
        return round(c * 100), round(m * 100), round(y * 100), round(k * 100)
    
    @staticmethod
    def cmyk_to_rgb(c, m, y, k):
        c_norm = c / 100.0
        m_norm = m / 100.0
        y_norm = y / 100.0
        k_norm = k / 100.0
        
        r = 255 * (1 - c_norm) * (1 - k_norm)
        g = 255 * (1 - m_norm) * (1 - k_norm)
        b = 255 * (1 - y_norm) * (1 - k_norm)
        
        r = max(0, min(255, round(r)))
        g = max(0, min(255, round(g)))
        b = max(0, min(255, round(b)))
        
        return r, g, b
    
    @staticmethod
    def rgb_to_hls(r, g, b):
        r_norm = r / 255.0
        g_norm = g / 255.0
        b_norm = b / 255.0
        
        cmax = max(r_norm, g_norm, b_norm)
        cmin = min(r_norm, g_norm, b_norm)
        delta = cmax - cmin
        
        l = (cmax + cmin) / 2.0
        
        if delta == 0:
            h = 0
            s = 0
        else:
            s = delta / (1 - abs(2 * l - 1)) if l != 0.5 else 1
            
            if cmax == r_norm:
                h = 60 * (((g_norm - b_norm) / delta) % 6)
            elif cmax == g_norm:
                h = 60 * (((b_norm - r_norm) / delta) + 2)
            else:
                h = 60 * (((r_norm - g_norm) / delta) + 4)
        
        return round(h % 360), round(s * 100), round(l * 100)
    
    @staticmethod
    def hls_to_rgb(h, l, s):
        h_norm = h / 360.0
        s_norm = s / 100.0
        l_norm = l / 100.0
        
        if s_norm == 0:
            r = g = b = l_norm
        else:
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1/6: return p + (q - p) * 6 * t
                if t < 1/2: return q
                if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                return p
            
            q = l_norm * (1 + s_norm) if l_norm < 0.5 else l_norm + s_norm - l_norm * s_norm
            p = 2 * l_norm - q
            
            r = hue_to_rgb(p, q, h_norm + 1/3)
            g = hue_to_rgb(p, q, h_norm)
            b = hue_to_rgb(p, q, h_norm - 1/3)
        
        r = max(0, min(255, round(r * 255)))
        g = max(0, min(255, round(g * 255)))
        b = max(0, min(255, round(b * 255)))
        
        return r, g, b

class ColorSliderGroup(QWidget):
    valueChanged = Signal(int, int)
    
    def __init__(self, label, min_val, max_val, default_val, parent=None):
        super().__init__(parent)
        self.index = -1
        self.min_val = min_val
        self.max_val = max_val
        self.setup_ui(label, min_val, max_val, default_val)
    
    def setup_ui(self, label, min_val, max_val, default_val):
        layout = QVBoxLayout()
        
        self.label = QLabel(label)
        layout.addWidget(self.label)
        
        h_layout = QHBoxLayout()
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(default_val)
        self.slider.valueChanged.connect(self.on_slider_changed)
        
        self.input = QLineEdit(str(default_val))
        self.input.editingFinished.connect(self.on_input_changed)
        self.input.setFixedWidth(50)
        
        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.input)
        
        layout.addLayout(h_layout)
        self.setLayout(layout)
    
    def set_index(self, index):
        self.index = index
    
    def on_slider_changed(self, value):
        self.input.setText(str(value))
        self.valueChanged.emit(self.index, value)
    
    def on_input_changed(self):
        try:
            value = int(self.input.text())
            clamped_value = max(self.min_val, min(self.max_val, value))
            if value != clamped_value:
                self.slider.setValue(clamped_value)
                self.input.setText(str(clamped_value))
                self.valueChanged.emit(self.index, clamped_value)
            else:
                self.valueChanged.emit(self.index, value)
        except ValueError:
            self.input.setText(str(self.slider.value()))
    
    def set_value(self, value):
        self.slider.blockSignals(True)
        self.input.blockSignals(True)
        
        self.slider.setValue(value)
        self.input.setText(str(value))
        
        self.slider.blockSignals(False)
        self.input.blockSignals(False)

class ColorModelGroup(QGroupBox):
    valuesChanged = Signal(list)
    
    def __init__(self, title, labels, ranges, parent=None):
        super().__init__(title, parent)
        self.sliders = []
        self.setup_ui(labels, ranges)
    
    def setup_ui(self, labels, ranges):
        layout = QVBoxLayout()
        
        for i, (label, (min_val, max_val, default_val)) in enumerate(zip(labels, ranges)):
            slider_group = ColorSliderGroup(label, min_val, max_val, default_val)
            slider_group.set_index(i)
            slider_group.valueChanged.connect(self.on_slider_changed)
            self.sliders.append(slider_group)
            layout.addWidget(slider_group)
        
        self.setLayout(layout)
    
    def on_slider_changed(self, index, value):
        values = [slider.slider.value() for slider in self.sliders]
        self.valuesChanged.emit(values)
    
    def set_values(self, values):
        for slider, value in zip(self.sliders, values):
            slider.set_value(value)

class ColorPickerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_rgb = (128, 128, 128)
        self.setup_ui()
        self.update_color_display()
    
    def setup_ui(self):
        self.setWindowTitle("Color Converter - RGB ↔ CMYK ↔ HLS")
        self.setGeometry(100, 100, 900, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        left_layout = QVBoxLayout()
        
        rgb_labels = ["Red", "Green", "Blue"]
        rgb_ranges = [(0, 255, 128), (0, 255, 128), (0, 255, 128)]
        self.rgb_group = ColorModelGroup("RGB Model", rgb_labels, rgb_ranges)
        self.rgb_group.valuesChanged.connect(self.on_rgb_changed)
        left_layout.addWidget(self.rgb_group)
        
        cmyk_labels = ["Cyan", "Magenta", "Yellow", "Black"]
        cmyk_ranges = [(0, 100, 0), (0, 100, 0), (0, 100, 0), (0, 100, 0)]
        self.cmyk_group = ColorModelGroup("CMYK Model", cmyk_labels, cmyk_ranges)
        self.cmyk_group.valuesChanged.connect(self.on_cmyk_changed)
        left_layout.addWidget(self.cmyk_group)
        
        hls_labels = ["Hue", "Lightness", "Saturation"]
        hls_ranges = [(0, 360, 0), (0, 100, 50), (0, 100, 0)]
        self.hls_group = ColorModelGroup("HLS Model", hls_labels, hls_ranges)
        self.hls_group.valuesChanged.connect(self.on_hls_changed)
        left_layout.addWidget(self.hls_group)
        
        right_layout = QVBoxLayout()
        
        self.color_display = QLabel()
        self.color_display.setMinimumSize(200, 200)
        self.color_display.setStyleSheet("background-color: rgb(128, 128, 128); border: 2px solid black;")
        self.color_display.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.color_display)
        
        self.color_info = QLabel("RGB: (128, 128, 128)\nCMYK: (0, 0, 0, 50)\nHLS: (0, 50, 0)")
        self.color_info.setAlignment(Qt.AlignCenter)
        self.color_info.setStyleSheet("padding: 10px;")
        right_layout.addWidget(self.color_info)
        
        self.pick_color_btn = QPushButton("Pick Color")
        self.pick_color_btn.clicked.connect(self.pick_color)
        right_layout.addWidget(self.pick_color_btn)
        
        right_layout.addStretch()
        
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)
        
        central_widget.setLayout(main_layout)
    
    def on_rgb_changed(self, values):
        r, g, b = values
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        self.current_rgb = (r, g, b)
        
        c, m, y, k = ColorConverter.rgb_to_cmyk(r, g, b)
        h, l, s = ColorConverter.rgb_to_hls(r, g, b)
        
        self.cmyk_group.blockSignals(True)
        self.cmyk_group.set_values([c, m, y, k])
        self.cmyk_group.blockSignals(False)
        
        self.hls_group.blockSignals(True)
        self.hls_group.set_values([h, l, s])
        self.hls_group.blockSignals(False)
        
        self.update_color_display()
    
    def on_cmyk_changed(self, values):
        c, m, y, k = values
        c = max(0, min(100, c))
        m = max(0, min(100, m))
        y = max(0, min(100, y))
        k = max(0, min(100, k))
        
        r, g, b = ColorConverter.cmyk_to_rgb(c, m, y, k)
        self.current_rgb = (r, g, b)
        
        h, l, s = ColorConverter.rgb_to_hls(r, g, b)
        
        self.rgb_group.blockSignals(True)
        self.rgb_group.set_values([r, g, b])
        self.rgb_group.blockSignals(False)
        
        self.hls_group.blockSignals(True)
        self.hls_group.set_values([h, l, s])
        self.hls_group.blockSignals(False)
        
        self.update_color_display()
    
    def on_hls_changed(self, values):
        h, l, s = values
        h = max(0, min(360, h))
        l = max(0, min(100, l))
        s = max(0, min(100, s))
        
        r, g, b = ColorConverter.hls_to_rgb(h, l, s)
        self.current_rgb = (r, g, b)
        
        c, m, y, k = ColorConverter.rgb_to_cmyk(r, g, b)
        
        self.rgb_group.blockSignals(True)
        self.rgb_group.set_values([r, g, b])
        self.rgb_group.blockSignals(False)
        
        self.cmyk_group.blockSignals(True)
        self.cmyk_group.set_values([c, m, y, k])
        self.cmyk_group.blockSignals(False)
        
        self.update_color_display()
    
    def update_color_display(self):
        r, g, b = self.current_rgb
        c, m, y, k = ColorConverter.rgb_to_cmyk(r, g, b)
        h, l, s = ColorConverter.rgb_to_hls(r, g, b)
        
        color = QColor(r, g, b)
        self.color_display.setStyleSheet(f"background-color: {color.name()}; border: 2px solid black;")
        
        info_text = f"RGB: ({r}, {g}, {b})\nCMYK: ({c}, {m}, {y}, {k})\nHLS: ({h}, {l}, {s})"
        self.color_info.setText(info_text)
    
    def pick_color(self):
        color = QColorDialog.getColor(QColor(*self.current_rgb), self, "Select Color")
        if color.isValid():
            r, g, b = color.red(), color.green(), color.blue()
            self.rgb_group.set_values([r, g, b])
            self.on_rgb_changed([r, g, b])

def main():
    app = QApplication(sys.argv)
    window = ColorPickerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()