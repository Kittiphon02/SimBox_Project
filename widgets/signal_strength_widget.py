# widgets/signal_strength_widget.py
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QWidget

class SignalStrengthWidget(QWidget):
    """
    แสดงแท่งสัญญาณ 5 แท่ง + อนิเมชัน "pulse"
    - set_level(0..5) เพื่อกำหนดจำนวนแท่งที่ติด
    - set_rssi_dbm(-dBm) แล้วจะ map เป็นระดับอัตโนมัติ
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0          # 0..5
        self._pulse = 0.0        # ใช้ทำอนิเมชัน
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)    # 60 ms = ~16 FPS
        self.setMinimumSize(90, 50)
        self.setMaximumHeight(60)
        self._up = True

        # สีตามสถานะ
        self.colors = {
            "good": QColor("#2ecc71"),
            "fair": QColor("#f39c12"),
            "poor": QColor("#e74c3c"),
            "off":  QColor("#bdc3c7")
        }

    # ----- public API -----
    def set_level(self, level:int):
        self._level = max(0, min(5, level))
        self.update()

    def set_rssi_dbm(self, rssi_dbm: int):
        """
        mapping ตัวอย่าง:
        >= -65 -> 5, -66..-75 -> 4, -76..-85 -> 3, -86..-95 -> 2, -96..-105 -> 1, ต่ำกว่านั้น -> 0
        """
        d = int(rssi_dbm)
        if d >= -65: lvl = 5
        elif d >= -75: lvl = 4
        elif d >= -85: lvl = 3
        elif d >= -95: lvl = 2
        elif d >= -105: lvl = 1
        else: lvl = 0
        self.set_level(lvl)

    # ----- animation tick -----
    def _tick(self):
        # ทำ breathing/pulse เบาๆ
        step = 0.05
        self._pulse += step if self._up else -step
        if self._pulse >= 1.0:
            self._pulse, self._up = 1.0, False
        elif self._pulse <= 0.0:
            self._pulse, self._up = 0.0, True
        self.update()

    # ----- paint -----
    def paintEvent(self, _):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        margin = 8
        gap = 6
        bars = 5
        bar_w = (w - margin*2 - gap*(bars-1)) / bars

        # base line
        pen = QPen(Qt.NoPen)
        painter.setPen(pen)

        # คำนวณสีรวมตามระดับ
        if self._level >= 4:
            on_color = self.colors["good"]
        elif self._level == 3:
            on_color = self.colors["fair"]
        elif self._level in (1,2):
            on_color = self.colors["poor"]
        else:
            on_color = self.colors["off"]

        for i in range(bars):
            # ความสูงแท่งแบบขั้นบันได
            ratio = (i+1)/bars
            bar_h = (h - margin*2) * ratio

            x = margin + i*(bar_w + gap)
            y = h - margin - bar_h

            # ทำ pulse: ขยายความสูงนิดหน่อยเฉพาะแท่งที่ "ติด"
            active = i < self._level
            grow = 1.0 + (0.08*self._pulse if active else 0.0)
            adj_h = bar_h * grow
            adj_y = h - margin - adj_h

            rect = QRectF(x, adj_y, bar_w, adj_h)

            # สีแท่ง
            if active:
                brush = QBrush(on_color)
            else:
                brush = QBrush(self.colors["off"])

            painter.setBrush(brush)
            painter.drawRoundedRect(rect, 3, 3)
