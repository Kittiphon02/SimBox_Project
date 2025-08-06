# loading_widget.py - Enhanced error handling
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
        
        # ⭐ Error Details Frame (hidden initially)
        self.error_frame = QFrame()
        self.error_frame.setFrameStyle(QFrame.Box)
        error_layout = QVBoxLayout()
        
        self.error_title = QLabel("❌ ข้อผิดพลาดในการส่ง SMS")
        self.error_title.setAlignment(Qt.AlignCenter)
        self.error_title.setFont(QFont("Arial", 12, QFont.Bold))
        error_layout.addWidget(self.error_title)
        
        self.error_detail = QLabel("")
        self.error_detail.setAlignment(Qt.AlignCenter)
        self.error_detail.setFont(QFont("Arial", 10))
        self.error_detail.setWordWrap(True)
        error_layout.addWidget(self.error_detail)
        
        self.error_suggestion = QLabel("")
        self.error_suggestion.setAlignment(Qt.AlignCenter)
        self.error_suggestion.setFont(QFont("Arial", 9))
        self.error_suggestion.setWordWrap(True)
        error_layout.addWidget(self.error_suggestion)
        
        self.error_frame.setLayout(error_layout)
        self.error_frame.hide()  # เริ่มต้นซ่อนไว้
        layout.addWidget(self.error_frame)
        
        # Error Label (old - for compatibility)
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
        
        # ⭐ Error Frame Styles
        self.error_frame.setStyleSheet("""
            QFrame {
                background-color: #fff5f5;
                border: 2px solid #dc3545;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)
        self.error_title.setStyleSheet(LoadingWidgetStyles.get_error_label_style())
        self.error_detail.setStyleSheet("""
            QLabel {
                color: #721c24;
                font-size: 11px;
                margin: 5px;
            }
        """)
        self.error_suggestion.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 9px;
                font-style: italic;
                margin: 5px;
            }
        """)
        
        # Status Frame and Label
        self.status_frame.setStyleSheet(LoadingWidgetStyles.get_status_frame_style())
        self.status_label.setStyleSheet(LoadingWidgetStyles.get_status_label_style())
        
        # Progress Bar (default style)
        self.progress_bar.setStyleSheet(LoadingWidgetStyles.get_progress_bar_style())
    
    def start_sending(self):
        self.is_loading = True
        self.error_label.hide()
        self.error_frame.hide()  # ⭐ ซ่อน error frame
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
        self.error_frame.hide()  # ⭐ ซ่อน error frame
        self.progress_bar.setValue(100)
        self.percentage_label.setText("100%")
        self.status_label.setText("ส่งข้อความสำเร็จ!")
        self.status_icon.setText("✅")
        
        # ใช้สไตล์สำเร็จ
        self.progress_bar.setStyleSheet(LoadingWidgetStyles.get_progress_bar_success_style())
        self.finished.emit(True)
    
    def complete_sending_error(self, error_msg):
        """⭐ Enhanced error handling with detailed information"""
        self.timer.stop()
        self.is_loading = False
        
        # ซ่อน error label เก่า แสดง error frame ใหม่
        self.error_label.hide()
        
        # แสดงข้อมูลข้อผิดพลาดแบบละเอียด
        self._show_detailed_error(error_msg)
        
        self.status_label.setText("เกิดข้อผิดพลาด")
        self.status_icon.setText("❌")
        
        # ใช้สไตล์ข้อผิดพลาด
        self.progress_bar.setStyleSheet(LoadingWidgetStyles.get_progress_bar_error_style())
        self.finished.emit(False)
    
    def _show_detailed_error(self, error_msg):
        """⭐ แสดงข้อผิดพลาดแบบละเอียด"""
        # แยกประเภทข้อผิดพลาดและให้คำแนะนำ
        error_type, suggestion = self._categorize_error(error_msg)
        
        self.error_detail.setText(error_type)
        self.error_suggestion.setText(suggestion)
        self.error_frame.show()
    
    def _categorize_error(self, error_msg):
        """⭐ จำแนกประเภทข้อผิดพลาดและให้คำแนะนำ"""
        error_lower = error_msg.lower()
        
        if 'sim' in error_lower:
            if 'ไม่มี' in error_msg or 'no sim' in error_lower:
                return (
                    "🔴 ไม่พบ SIM Card หรือ SIM ไม่พร้อมใช้งาน",
                    "💡 แนะนำ: ตรวจสอบ SIM Card • คลิก 'Refresh Ports' • ลอง 'SIM Recovery'"
                )
            elif 'not ready' in error_lower or 'ไม่พร้อม' in error_msg:
                return (
                    "🟠 SIM Card ไม่พร้อมใช้งาน",
                    "💡 แนะนำ: รอสักครู่แล้วลองใหม่ • คลิก 'SIM Recovery' • เช็คสัญญาณ"
                )
            else:
                return (
                    "🔴 SIM Card มีปัญหา",
                    "💡 แนะนำ: ตรวจสอบ SIM Card • คลิก 'SIM Recovery' • เปลี่ยน SIM"
                )
        
        elif 'serial' in error_lower or 'connection' in error_lower or 'เชื่อมต่อ' in error_msg:
            return (
                "🔴 การเชื่อมต่อขาดหาย",
                "💡 แนะนำ: ตรวจสอบสาย USB • คลิก 'Refresh Ports' • เสียบใหม่"
            )
        
        elif 'signal' in error_lower or 'network' in error_lower or 'สัญญาณ' in error_msg:
            return (
                "🟠 สัญญาณอ่อนหรือไม่มีเครือข่าย",
                "💡 แนะนำ: ย้ายไปที่มีสัญญาณดี • เช็คเครือข่าย • ลองใหม่อีกครั้ง"
            )
        
        elif 'timeout' in error_lower or 'หมดเวลา' in error_msg:
            return (
                "🟡 หมดเวลารอการตอบสนอง",
                "💡 แนะนำ: ลองส่งใหม่ • ตรวจสอบสัญญาณ • รีสตาร์ทโมเด็ม"
            )
        
        elif 'at+' in error_lower or 'command' in error_lower:
            return (
                "🔴 คำสั่ง AT ผิดพลาด",
                "💡 แนะนำ: คลิก 'Refresh Ports' • เช็ค Baudrate • รีสตาร์ทโมเด็ม"
            )
        
        else:
            return (
                f"🔴 {error_msg}",
                "💡 แนะนำ: คลิก 'Refresh Ports' • ตรวจสอบการเชื่อมต่อ • ลองใหม่"
            )