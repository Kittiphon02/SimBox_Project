# loading_widget.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

# ==================== IMPORT NEW STYLES ====================
from styles import LoadingWidgetStyles

class LoadingWidget(QWidget):
    finished = pyqtSignal(bool)  # True = สำเร็จ, False = ล้มเหลว
    
    def __init__(self, message="Loading...", parent=None):
        super().__init__(parent)
        self.progress = 0
        self.is_loading = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.current_step = 0
        self.steps = [
            {"progress": 15, "text": "เชื่อมต่อกับ Modem..."},
            {"progress": 30, "text": "ตั้งค่า AT Commands..."},
            {"progress": 50, "text": "เตรียมข้อความ..."},
            {"progress": 70, "text": "เข้ารหัสข้อมูล..."},
            {"progress": 85, "text": "ส่งข้อความ SMS..."},
            {"progress": 95, "text": "รอการยืนยัน..."},
            {"progress": 100, "text": "ส่งสำเร็จ!"}
        ]
        self.setup_ui()
        self.apply_styles()  # ใช้สไตล์ใหม่
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with Icon
        header_layout = QHBoxLayout()
        icon_label = QLabel("📱")
        icon_label.setFont(QFont("Arial", 24))
        icon_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon_label)
        
        self.title_label = QLabel("Sending SMS")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Arial", 15, QFont.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Subtitle
        self.subtitle_label = QLabel("ระบบส่งข้อความ SMS อัตโนมัติ")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.subtitle_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(25)
        layout.addWidget(self.progress_bar)
        
        # Progress Percentage
        self.percentage_label = QLabel("0%")
        self.percentage_label.setAlignment(Qt.AlignCenter)
        self.percentage_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.percentage_label)
        
        # Status Frame
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box)
        status_layout = QHBoxLayout()
        
        self.status_icon = QLabel("🔵")
        self.status_icon.setFont(QFont("Arial", 16))
        status_layout.addWidget(self.status_icon)
        
        self.status_label = QLabel("พร้อมส่งข้อความ")
        self.status_label.setFont(QFont("Arial", 11, QFont.Bold))
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_frame.setLayout(status_layout)
        layout.addWidget(status_frame)
        
        # Error Label (hidden initially)
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        self.setLayout(layout)
        
        # จัดเก็บ reference ไว้สำหรับใช้กับ styling
        self.status_frame = status_frame
    
    def apply_styles(self):
        """ใช้สไตล์ใหม่โทนสีแดงทางการ"""
        # Main Container
        self.setStyleSheet(LoadingWidgetStyles.get_main_container_style())
        
        # Title and Labels
        self.title_label.setStyleSheet(LoadingWidgetStyles.get_title_label_style())
        self.subtitle_label.setStyleSheet(LoadingWidgetStyles.get_subtitle_label_style())
        self.percentage_label.setStyleSheet(LoadingWidgetStyles.get_percentage_label_style())
        self.error_label.setStyleSheet(LoadingWidgetStyles.get_error_label_style())
        
        # Status Frame and Label
        self.status_frame.setStyleSheet(LoadingWidgetStyles.get_status_frame_style())
        self.status_label.setStyleSheet(LoadingWidgetStyles.get_status_label_style())
        
        # Progress Bar (default style)
        self.progress_bar.setStyleSheet(LoadingWidgetStyles.get_progress_bar_style())
    
    def start_sending(self):
        self.is_loading = True
        self.error_label.hide()
        self.progress = 0
        self.current_step = 0
        self.progress_bar.setValue(0)
        self.percentage_label.setText("0%")
        self.status_label.setText("เริ่มการส่ง...")
        self.status_icon.setText("🟡")
        
        # รีเซ็ตสไตล์ progress bar กลับเป็นปกติ
        self.progress_bar.setStyleSheet(LoadingWidgetStyles.get_progress_bar_style())
        self.subtitle_label.setText("ระบบส่งข้อความ SMS อัตโนมัติ")
        self.timer.start(150)
    
    def update_progress(self):
        if not self.is_loading:
            return
        self.progress += 3.7
        if self.progress >= 100:
            self.progress = 100
            self.complete_sending_success()
            return
        self.progress_bar.setValue(int(self.progress))
        self.percentage_label.setText(f"{int(self.progress)}%")
        for i, step in enumerate(self.steps):
            if self.progress >= step["progress"] and i > self.current_step:
                self.current_step = i
                self.status_label.setText(step["text"])
                break
    
    def update_status(self, status_text):
        self.status_label.setText(status_text)
    
    def complete_sending_success(self):
        self.timer.stop()
        self.is_loading = False
        self.error_label.hide()
        self.progress_bar.setValue(100)
        self.percentage_label.setText("100%")
        self.status_label.setText("ส่งข้อความสำเร็จ!")
        self.status_icon.setText("✅")
        
        # ใช้สไตล์สำเร็จ
        self.progress_bar.setStyleSheet(LoadingWidgetStyles.get_progress_bar_success_style())
        self.finished.emit(True)
    
    def complete_sending_error(self, error_msg):
        self.timer.stop()
        self.is_loading = False
        # แสดงข้อความผิดพลาด
        self.error_label.setText("SMS ไม่สำเร็จ: " + error_msg)
        self.error_label.show()
        self.status_label.setText("เกิดข้อผิดพลาด")
        self.status_icon.setText("❌")
        
        # ใช้สไตล์ข้อผิดพลาด
        self.progress_bar.setStyleSheet(LoadingWidgetStyles.get_progress_bar_error_style())
        self.finished.emit(False)