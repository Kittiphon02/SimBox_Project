
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QComboBox, QGroupBox, QSizePolicy, QMessageBox,
    QSpacerItem, QTextEdit, QShortcut, QDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QKeySequence

# core, managers, services, widgets, styles
from core import list_serial_ports, safe_get_attr, SettingsManager, ThemeManager
from managers import (
    ATCommandManager, SpecialCommandHandler,
    PortManager, SerialConnectionManager, SimRecoveryManager,
    SMSHandler, SMSInboxManager, DialogManager, SyncManager
)
from services import load_sim_data, SerialMonitorThread
from widgets import SimTableWidget
from styles import MainWindowStyles
from windows.at_command_helper import ATCommandHelper
from services.sms_log import log_sms_sent
from widgets.sms_log_dialog import SmsLogDialog
from windows.enhanced_sim_signal_quality_window import show_enhanced_sim_signal_quality_window
from managers.smart_command_manager import SmartCommandManager
from datetime import datetime
import types
from collections import deque
from time import monotonic
from widgets.loading_widget import LoadingWidget
from pathlib import Path

class SimInfoWindow(QMainWindow):
    """หน้าต่างหลักของโปรแกรม SIM Management System"""
    at_manual_signal  = pyqtSignal(str)   # สำหรับผล AT ที่ผู้ใช้กดเอง → ไปช่อง Response หน้าแรก
    at_monitor_signal = pyqtSignal(str)   # สำหรับข้อความ real-time/URC → ไปหน้าต่าง SMS Monitor
    
    def __init__(self):
        super().__init__()
        
        self.setup_keyboard_shortcuts()
        
        # ==================== 1. INITIALIZATION ====================
        self.init_variables()
        self.init_managers()
        
        # โหลดการตั้งค่าและสร้าง UI
        self.load_application_settings()
        self.setup_window()
        self.setup_ui()
        self.setup_styles()
        self.setup_connections()
        
        # เริ่มต้นการทำงาน
        self.initialize_application()

        # self.setup_enhanced_display_separation()
        if self.serial_thread and hasattr(self.serial_thread, 'at_response_signal'):
            # self.serial_thread.at_response_signal.connect(self.update_at_result_display)
            self.serial_thread.new_sms_signal.connect(self.sms_handler.process_new_sms_signal)

    def setup_enhanced_display_separation(self):
        """ตั้งค่าระบบแยกการแสดงผลแบบ Enhanced"""
        
        # สร้าง Enhanced Display Manager
        self.display_manager = EnhancedDisplayFilterManager(self)
        
        # เชื่อมต่อกับ Serial Thread ถ้ามี
        if hasattr(self, 'serial_thread') and self.serial_thread:
            self._setup_enhanced_serial_connection()
            
        print("✅ Enhanced Display Separation setup completed")
    
    def _setup_enhanced_serial_connection(self):
        """ตั้งค่าการเชื่อมต่อ Serial แบบ Enhanced"""
        try:
            # ❌ เดิม: ตัดทุก slot ออกหมด จน Monitor โดนตัดด้วย
            # self.serial_thread.at_response_signal.disconnect()

            # ✅ ใหม่: ตัดเฉพาะ slot เดิมของ "หน้าหลัก" เท่านั้น
            self.serial_thread.at_response_signal.disconnect(self.update_at_result_display)
        except Exception:
            pass

        # แล้วค่อยเชื่อมใหม่เข้าระบบกรอง
        self.serial_thread.at_response_signal.connect(self.handle_enhanced_response)
        print("✅ Enhanced Serial connection established")

    def handle_enhanced_response(self, response):
        """จัดการ response ผ่านระบบ Enhanced Display Separation"""
        if hasattr(self, 'display_manager'):
            self.display_manager.process_response(response)
        else:
            # fallback ถ้าไม่มี display manager
            self.update_at_result_display(response)
    
    def init_variables(self):
        """เริ่มต้นตัวแปรสำคัญ"""
        self.serial_thread = None
        self.netqual_mgr = None

        self.sims = []
        
        # SMS processing variables
        self._cmt_buffer = None
        self._notified_sms = set()
        
        # Recovery และ monitoring variables
        self.sim_recovery_in_progress = False
        self.auto_sms_monitor = True
        self._is_sending_sms = False
        
        # Dialog references
        self.sms_monitor_dialog = None
        self.loading_dialog = None
        self.loading_widget = None
        self.open_dialogs = []

        # SMS processing variables
        self._cmt_buffer = None
        self._notified_sms = set()

        self.incoming_sms_count = 0

    def write_manual_response(self, text: str):
        self.write_manual_response(text)

        # self.at_result_display.append(text)   # ช่อง Response ของหน้าหลัก

    def write_monitor_response(self, text: str):
        self.write_monitor_response(text)

        # self.at_monitor_signal.emit(text)     # ส่งต่อไป SMS Monitor

    def init_managers(self):
        """เริ่มต้น manager classes ต่างๆ"""
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager(self.settings_manager)
        self.at_command_manager = ATCommandManager(self)
        self.special_command_handler = SpecialCommandHandler(self)
        # self.sms_manager = SMSManager(self)
        self.sms_handler = SMSHandler(self)
        self.sms_inbox_manager = SMSInboxManager(self)
        self.port_manager = PortManager(self)
        self.serial_connection_manager = SerialConnectionManager(self)
        self.sim_recovery_manager = SimRecoveryManager(self)
        self.dialog_manager = DialogManager(self)
        self.sync_manager = SyncManager(self)

    def load_application_settings(self):
        """โหลดการตั้งค่าโปรแกรม"""
        try:
            settings = self.settings_manager.load_settings()
            self.auto_sms_monitor = settings.get('auto_sms_monitor', True)
            
        except Exception as e:
            print(f"Error loading application settings: {e}")
            self.auto_sms_monitor = True

    # ==================== 2. WINDOW & UI SETUP ====================
    def setup_window(self):
        """ตั้งค่าหน้าต่างหลัก"""
        self.setWindowTitle("SIM Management System")
        
        # ใช้การตั้งค่าที่บันทึกไว้
        geometry = self.settings_manager.get_window_geometry()
        self.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
        
        self.setStyleSheet(MainWindowStyles.get_main_window_style())
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
                           Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
    
    def setup_ui(self):
        """สร้าง UI components"""
        main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        main_widget.setLayout(self.main_layout)
        self.setCentralWidget(main_widget)
        
        self.create_header()
        self.create_modem_controls()
        self.create_at_command_display()
        self.create_sim_table()
    
    def create_header(self): 
        """สร้างส่วนหัวของแอปพลิเคชัน"""
        header = QLabel("SIM Management System")
        header.setAlignment(Qt.AlignHCenter)
        self.main_layout.addWidget(header)
        self.header = header
    
    def create_modem_controls(self):
        """สร้างส่วนควบคุมโมเด็ม"""
        modem_group = QGroupBox()
        modem_group.setTitle(" Set up modem connection ")
        modem_layout = QHBoxLayout()
        
        # Port Selection
        modem_layout.addWidget(QLabel("USB Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setFixedWidth(220)
        modem_layout.addWidget(self.port_combo)
        
        # Baudrate Selection
        modem_layout.addSpacing(14)
        modem_layout.addWidget(QLabel("Baudrate:"))
        self.baud_combo = QComboBox()
        baudrates = ['9600', '19200', '38400', '57600', '115200']
        self.baud_combo.addItems(baudrates)
        self.baud_combo.setCurrentText('115200')
        self.baud_combo.setFixedWidth(110)
        modem_layout.addWidget(self.baud_combo)
        
        # Control Buttons
        self.create_control_buttons(modem_layout)
        
        modem_layout.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        modem_group.setLayout(modem_layout)
        self.main_layout.addWidget(modem_group)
        self.main_layout.addSpacing(16)
        
        self.modem_group = modem_group
    
    def create_control_buttons(self, layout):
        """สร้างปุ่มควบคุมต่างๆ - Updated version with improved Signal Quality button"""
        layout.addSpacing(16)
        
        button_width = 120
        
        # ปุ่ม Refresh Ports
        self.btn_refresh = QPushButton("Refresh Ports")
        self.btn_refresh.setFixedWidth(button_width)
        layout.addWidget(self.btn_refresh)
        
        # ปุ่ม ดูประวัติ SMS
        self.btn_smslog = QPushButton("ดูประวัติ SMS")
        self.btn_smslog.setFixedWidth(button_width)
        layout.addWidget(self.btn_smslog)
        
        # ปุ่ม SMS Monitor
        self.btn_realtime_monitor = QPushButton("SMS Monitor")
        self.btn_realtime_monitor.setFixedWidth(button_width)
        layout.addWidget(self.btn_realtime_monitor)

        # ปุ่ม SIM Recovery
        self.btn_sim_recovery = QPushButton("SIM Recovery")
        self.btn_sim_recovery.setFixedWidth(button_width)
        self.btn_sim_recovery.clicked.connect(self.sim_recovery_manager.manual_sim_recovery)
        self.btn_sim_recovery.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(self.btn_sim_recovery)
        
        # ปุ่ม Signal Quality - ปรับแต่งใหม่
        self.btn_signal_quality = QPushButton("📶 Signal Quality")
        self.btn_signal_quality.setFixedWidth(button_width + 20)  # กว้างขึ้นเล็กน้อย
        self.btn_signal_quality.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9b59b6, stop:1 #8e44ad);
                color: white;
                border: 1px solid #7d3c98;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8e44ad, stop:1 #7d3c98);
                border: 1px solid #6c3483;
            }
            QPushButton:pressed {
                background: #7d3c98;
                padding-top: 9px;
                padding-bottom: 7px;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
                border: 1px solid #95a5a6;
            }
        """)
        layout.addWidget(self.btn_signal_quality)
        
        # ปุ่ม Sync
        self.btn_sync = QPushButton("🔄 Sync")
        self.btn_sync.setFixedWidth(100)
        self.btn_sync.clicked.connect(self.sync_manager.manual_sync)
        self.btn_sync.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(self.btn_sync)
        
        # SMS Inbox Badge Container (เหมือนเดิม)
        sms_container = QWidget()
        sms_container.setFixedSize(160, 40)
        sms_layout = QHBoxLayout()
        sms_layout.setContentsMargins(0, 0, 0, 0)
        sms_layout.setSpacing(0)
        
        self.sms_inbox_badge = QLabel("SMS Inbox")
        self.sms_inbox_badge.setAlignment(Qt.AlignCenter)
        self.sms_inbox_badge.setFixedSize(110, 35)
        self.sms_inbox_badge.setStyleSheet("""
            QLabel {
                background-color: #3498db;
                color: white;
                border: 2px solid #2980b9;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 8px;
            }
        """)
        sms_layout.addWidget(self.sms_inbox_badge)
        
        self.sms_count_badge = QLabel("0")
        self.sms_count_badge.setAlignment(Qt.AlignCenter)
        self.sms_count_badge.setFixedSize(28, 28)
        self.sms_count_badge.setStyleSheet("""
            QLabel {
                background-color: #e74c3c;
                color: white;
                border: 2px solid white;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
        """)
        
        sms_layout.addWidget(self.sms_count_badge)
        sms_layout.setAlignment(self.sms_count_badge, Qt.AlignTop | Qt.AlignRight)
        sms_layout.setContentsMargins(-15, 0, 5, 0)
        
        sms_container.setLayout(sms_layout)
        layout.addWidget(sms_container)

    def update_sms_inbox_counter(self, count):
        """อัพเดทจำนวน SMS ใน inbox แบบ Badge"""
        if hasattr(self, 'sms_count_badge'):
            if count == 0:
                # ซ่อน badge เมื่อไม่มี SMS
                self.sms_count_badge.hide()
                # เปลี่ยนสี SMS Inbox เป็นสีเทา
                self.sms_inbox_badge.setStyleSheet("""
                    QLabel {
                        background-color: #95a5a6;
                        color: white;
                        border: 2px solid #7f8c8d;
                        border-radius: 8px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 6px 8px;
                    }
                """)
            else:
                # แสดง badge และอัพเดทจำนวน
                self.sms_count_badge.show()
                
                # จำกัดแสดงไม่เกิน 99+
                display_count = str(count) if count <= 99 else "99+"
                self.sms_count_badge.setText(display_count)
                
                # เปลี่ยนสี Badge ตามจำนวน
                if count >= 10:
                    # สีแดงเข้มเมื่อมีเยอะ
                    badge_style = """
                        QLabel {
                            background-color: #c0392b;
                            color: white;
                            border: 2px solid white;
                            border-radius: 14px;
                            font-size: 11px;
                            font-weight: bold;
                            text-align: center;
                        }
                    """
                else:
                    # สีแดงปกติ
                    badge_style = """
                        QLabel {
                            background-color: #e74c3c;
                            color: white;
                            border: 2px solid white;
                            border-radius: 14px;
                            font-size: 12px;
                            font-weight: bold;
                            text-align: center;
                        }
                    """
                
                self.sms_count_badge.setStyleSheet(badge_style)
                
                # เปลี่ยนสี SMS Inbox เป็นสีฟ้าเมื่อมี SMS
                self.sms_inbox_badge.setStyleSheet("""
                    QLabel {
                        background-color: #3498db;
                        color: white;
                        border: 2px solid #2980b9;
                        border-radius: 8px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 6px 8px;
                    }
                """)
    
    def animate_new_sms_badge(self):
        """แอนิเมชันเมื่อมี SMS ใหม่"""
        if hasattr(self, 'sms_count_badge') and self.sms_count_badge.isVisible():
            # แอนิเมชันกระพริบ
            original_style = self.sms_count_badge.styleSheet()
            
            # สีแอนิเมชัน (เขียว)
            animation_style = """
                QLabel {
                    background-color: #27ae60;
                    color: white;
                    border: 2px solid white;
                    border-radius: 14px;
                    font-size: 12px;
                    font-weight: bold;
                    text-align: center;
                }
            """
            
            # เปลี่ยนเป็นสีเขียว
            self.sms_count_badge.setStyleSheet(animation_style)
            
            # กลับเป็นสีเดิมหลัง 1.5 วินาที
            QTimer.singleShot(1500, lambda: self.sms_count_badge.setStyleSheet(original_style))

    def on_new_sms_received(self):
        """เมื่อได้รับ SMS ใหม่"""
        # เพิ่มจำนวน SMS
        self.incoming_sms_count += 1
        new_count = self.incoming_sms_count
        
        # อัพเดทจำนวน
        self.update_sms_inbox_counter(new_count)
        
        # แอนิเมชันแจ้งเตือน
        self.animate_new_sms_badge()
        
        # แสดงข้อความใน log
        self.update_at_result_display(f"[NEW SMS] 📩 New SMS received!")

    def on_sms_read_or_deleted(self):
        """เมื่อ SMS ถูกอ่านหรือลบ"""
        # อัพเดทจำนวนใหม่
        current_count = self.get_sms_inbox_count()
        self.update_sms_inbox_counter(current_count)
        
        # แสดงข้อความใน log  
        self.update_at_result_display(f"[SMS UPDATE] 📬 SMS count updated: {current_count}")


    def get_sms_inbox_count(self):
        """นับจำนวน SMS ใน inbox (ตัวอย่าง - ปรับตาม SMS handler ของคุณ)"""
        try:
            # เชื่อมต่อกับ SMS handler เพื่อนับ SMS ใน inbox
            if hasattr(self, 'sms_inbox_manager'):
                return self.sms_inbox_manager.get_sms_count()
            else:
                # วิธีสำรอง - นับจากไฟล์หรือฐานข้อมูล
                return 0
        except Exception as e:
            print(f"Error getting SMS count: {e}")
            return 0

    def refresh_sms_inbox_counter(self):
        """รีเฟรชจำนวน SMS inbox"""
        count = self.get_sms_inbox_count()
        self.incoming_sms_count = count
        self.update_sms_inbox_counter(self.incoming_sms_count)
        self.update_at_result_display(f"[SMS INBOX] 📬 Current inbox count: {count} messages")

    def get_message_text(self):
        """ดึงข้อความจากกล่องข้อความ"""
        if hasattr(self, 'sync_message_box'):
            return self.sync_message_box.text().strip()
        return ""

    def clear_message_text(self):
        """ล้างข้อความในกล่องข้อความ"""
        if hasattr(self, 'sync_message_box'):
            self.sync_message_box.clear()

    # อัพเดทเมธอดแสดงสถานะเมื่อไม่มี SIM
    def update_no_sim_status(self):
        """อัพเดทสถานะเมื่อไม่มี SIM"""
        self.update_at_result_display("[SIM STATUS] ❌ No SIM card detected")
        self.update_at_result_display("[SIM STATUS] ⚠️ SMS sending will fail without SIM")
        
        # อัพเดทปุ่มให้แสดงสถานะ
        if hasattr(self, 'btn_send_sms_main'):
            self.btn_send_sms_main.setText("📵 No SIM")
            self.btn_send_sms_main.setEnabled(True) 

    # เพิ่มเมธอดตรวจสอบสถานะ SIM แบบ manual
    def check_sim_status_manual(self):
        """ตรวจสอบสถานะ SIM แบบ manual"""
        try:
            if not hasattr(self, 'sims') or not self.sims:
                self.update_at_result_display("[SIM CHECK] ❌ No SIM data available")
                return False
            
            sim = self.sims[0]
            
            if not hasattr(sim, 'imsi') or not sim.imsi or sim.imsi == '-':
                self.update_at_result_display("[SIM CHECK] ❌ No SIM card or SIM not ready")
                return False
            
            if not sim.imsi.isdigit() or len(sim.imsi) < 15:
                self.update_at_result_display("[SIM CHECK] ❌ Invalid or corrupted SIM card")
                return False
            
            if hasattr(sim, 'carrier') and sim.carrier in ['Unknown', 'No SIM']:
                self.update_at_result_display("[SIM CHECK] ❌ Cannot identify network provider")
                return False
            
            if hasattr(sim, 'signal'):
                signal_str = str(sim.signal).upper()
                if any(keyword in signal_str for keyword in ['NO SIM', 'NO SIGNAL', 'ERROR', 'PIN REQUIRED']):
                    self.update_at_result_display(f"[SIM CHECK] ❌ SIM problem: {sim.signal}")
                    return False
            
            self.update_at_result_display("[SIM CHECK] ✅ SIM card is ready for SMS")
            self.update_at_result_display(f"[SIM CHECK] 📞 Phone: {sim.phone}")
            self.update_at_result_display(f"[SIM CHECK] 📡 Carrier: {sim.carrier}")
            self.update_at_result_display(f"[SIM CHECK] 📶 Signal: {sim.signal}")
            return True
            
        except Exception as e:
            self.update_at_result_display(f"[SIM CHECK] ❌ Error checking SIM: {e}")
            return False

    def create_at_command_display(self):
        """สร้างส่วนแสดง AT Command และผลลัพธ์ - Fixed Layout Version"""
        at_group = QGroupBox(" AT Command Display ")
        main_at_layout = QVBoxLayout()
        main_at_layout.setContentsMargins(8, 8, 8, 8)
        main_at_layout.setSpacing(10)

        # ส่วนบน: ป้อนคำสั่ง AT
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        input_layout.addWidget(QLabel("AT Command:"))

        self.at_combo_main = QComboBox()
        self.at_combo_main.setEditable(True)
        self.at_combo_main.setFixedWidth(300)
        input_layout.addWidget(self.at_combo_main)

        self.btn_del_cmd = QPushButton("DELETE")
        self.btn_del_cmd.setFixedWidth(100)
        input_layout.addWidget(self.btn_del_cmd)

        self.btn_help = QPushButton("Help")
        self.btn_help.setFixedWidth(70)
        input_layout.addWidget(self.btn_help)

        # เพิ่ม stretch เพื่อดันเนื้อหาไปทางซ้าย
        input_layout.addStretch()

        # โหลดประวัติคำสั่ง AT
        self.at_command_manager.load_command_history(self.at_combo_main)
        main_at_layout.addLayout(input_layout)
        main_at_layout.addSpacing(10)

        # ส่วนกลาง: ซ้าย (SMS) + ขวา (Response)
        middle_layout = QHBoxLayout()

        # ซ้าย: SMS input + ปุ่ม
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("SMS messages:"))
        self.input_sms_main = QTextEdit()
        self.input_sms_main.setFixedHeight(50)
        left_layout.addWidget(self.input_sms_main)

        left_layout.addWidget(QLabel("Telephone number:"))
        self.input_phone_main = QLineEdit()
        self.input_phone_main.setPlaceholderText("Enter destination number...")
        self.input_phone_main.setFixedHeight(35)
        left_layout.addWidget(self.input_phone_main)
        left_layout.addSpacing(10)

        btn_at_layout = QHBoxLayout()
        self.btn_send_at = QPushButton("Send AT")
        self.btn_send_at.setFixedWidth(120)
        self.btn_send_sms_main = QPushButton("Send SMS")
        self.btn_send_sms_main.setFixedWidth(100)
        self.btn_show_sms = QPushButton("SMS inbox")
        self.btn_show_sms.setFixedWidth(120)
        self.btn_clear_sms_main = QPushButton("Delete SMS")
        self.btn_clear_sms_main.setFixedWidth(130)
        
        for btn in (self.btn_send_at, self.btn_send_sms_main, self.btn_show_sms, self.btn_clear_sms_main):
            btn_at_layout.addWidget(btn)
        btn_at_layout.addStretch()
        left_layout.addLayout(btn_at_layout)
        left_layout.addSpacing(10)

        left_layout.addWidget(QLabel("AT Command:"))
        self.at_command_display = QTextEdit()
        self.at_command_display.setFixedHeight(80)
        self.at_command_display.setReadOnly(True)
        self.at_command_display.setPlaceholderText("The AT commands sent will be displayed here...")
        left_layout.addWidget(self.at_command_display)
        middle_layout.addLayout(left_layout, stretch=1)

        # ขวา: Result Display + Toggle (FIXED LAYOUT)
        result_layout = QVBoxLayout()

        # ==================== FIXED HEADER LAYOUT ====================
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8) 

        # Label "Response:"
        lbl = QLabel("Response:")
        lbl.setStyleSheet("font-weight: bold;")
        lbl.setMinimumWidth(70) 
        header_layout.addWidget(lbl)

        # Spacer เพื่อดันปุ่ม Hide ไปขวา
        header_layout.addStretch()

        # Toggle Button
        self.btn_toggle_response = QPushButton("Hide")
        self.btn_toggle_response.setCheckable(True)
        self.btn_toggle_response.setFixedWidth(60)
        self.btn_toggle_response.toggled.connect(self.on_toggle_response)
        header_layout.addWidget(self.btn_toggle_response)

        result_layout.addLayout(header_layout)

        # Response Display Area
        self.at_result_display = QTextEdit()
        self.at_result_display.setMinimumHeight(250)
        self.at_result_display.setReadOnly(True)
        self.at_result_display.setPlaceholderText("The results from the modem will be displayed here...")
        result_layout.addWidget(self.at_result_display)

        # Clear Response Button
        self.btn_clear_response = QPushButton("Clear Response")
        self.btn_clear_response.setFixedWidth(120)
        self.btn_clear_response.clicked.connect(self.clear_at_displays)
        result_layout.addWidget(self.btn_clear_response, 0, Qt.AlignRight)

        middle_layout.addLayout(result_layout, stretch=1)
        main_at_layout.addLayout(middle_layout)

        at_group.setLayout(main_at_layout)
        self.main_layout.addWidget(at_group)
        self.main_layout.addSpacing(16)
        self.at_group = at_group

    def show_at_command_helper(self):
        """แสดงหน้าต่าง AT Command Helper"""
        try:
            helper_dialog = ATCommandHelper(self)
            helper_dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot open AT Command Helper: {e}")

    def create_sim_table(self):
        """สร้างตารางแสดงข้อมูลซิม"""
        self.table = SimTableWidget(self.sims, history_callback=self.show_sms_log_for_phone)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # ตั้งค่า font monospace สำหรับ Unicode bars
        from PyQt5.QtGui import QFont
        monospace_font = QFont("Consolas", 12)
        if not monospace_font.exactMatch():
            monospace_font = QFont("Courier New", 12)
        self.table.setFont(monospace_font)
        
        self.main_layout.addWidget(self.table, stretch=1)
        
    def setup_styles(self):
        """ตั้งค่า CSS styles"""
        # Apply current theme
        current_theme = self.theme_manager.get_current_theme()
        self.theme_manager.apply_theme_to_widget(self, current_theme)
        
        # Apply specific styles
        self.header.setStyleSheet(MainWindowStyles.get_header_style())
        
        self.modem_group.setStyleSheet(MainWindowStyles.get_modem_group_style())
        self.at_group.setStyleSheet(MainWindowStyles.get_at_group_style())
        
        self.at_combo_main.setStyleSheet(MainWindowStyles.get_at_combo_style())
        self.input_sms_main.setStyleSheet(MainWindowStyles.get_sms_input_style())
        self.input_phone_main.setStyleSheet(MainWindowStyles.get_phone_input_style())
        
        self.btn_del_cmd.setStyleSheet(MainWindowStyles.get_delete_button_style())
        self.btn_help.setStyleSheet(MainWindowStyles.get_help_button_style())
        self.btn_send_at.setStyleSheet(MainWindowStyles.get_send_at_button_style())
        self.btn_show_sms.setStyleSheet(MainWindowStyles.get_show_sms_button_style())
        self.btn_send_sms_main.setStyleSheet(MainWindowStyles.get_send_sms_button_style())
        self.btn_clear_sms_main.setStyleSheet(MainWindowStyles.get_clear_sms_button_style())
        self.btn_clear_response.setStyleSheet(MainWindowStyles.get_clear_response_button_style())
        self.btn_refresh.setStyleSheet(MainWindowStyles.get_refresh_button_style())
        self.btn_smslog.setStyleSheet(MainWindowStyles.get_smslog_button_style())
        self.btn_realtime_monitor.setStyleSheet(MainWindowStyles.get_realtime_monitor_style())
        self.btn_toggle_response.setStyleSheet(MainWindowStyles.get_toggle_button_style())
        
        self.at_command_display.setStyleSheet(MainWindowStyles.get_command_display_style())
        self.at_result_display.setStyleSheet(MainWindowStyles.get_result_display_style())
        
        self.table.setStyleSheet(MainWindowStyles.get_table_style())
    
    def setup_connections(self):
        """เชื่อมต่อ signals และ slots - Updated version"""
        # Port management
        self.btn_refresh.clicked.connect(self.refresh_ports)
        
        # Dialog management
        self.btn_smslog.clicked.connect(self.dialog_manager.show_sms_log_dialog)
        self.btn_realtime_monitor.clicked.connect(self.open_realtime_monitor)
        
        # Signal Quality - ต้องเชื่อมต่อ
        self.btn_signal_quality.clicked.connect(self.show_signal_quality_checker)
        
        # AT Command management
        self.btn_send_at.clicked.connect(self.send_at_command_main)
        self.btn_del_cmd.clicked.connect(self.remove_at_command_main)
        self.btn_help.clicked.connect(self.show_at_command_helper)
        
        # SMS management
        self.btn_send_sms_main.clicked.connect(self.send_sms_main)
        self.btn_show_sms.clicked.connect(self.sms_inbox_manager.show_inbox_sms)
        self.btn_clear_sms_main.clicked.connect(self.sms_inbox_manager.clear_all_sms)
    
        # ⭐ เพิ่มการเชื่อมต่อปุ่ม SMS ที่ส่งไม่สำเร็จ
        if hasattr(self, 'btn_failed_sms'):
            self.btn_failed_sms.clicked.connect(self.show_failed_sms_dialog)
        
        # AT Command management
        self.btn_send_at.clicked.connect(self.send_at_command_main)
        self.btn_del_cmd.clicked.connect(self.remove_at_command_main)
        self.btn_help.clicked.connect(self.show_at_command_helper)
        
        # SMS management - ใช้เมธอดที่อัพเดทแล้ว
        self.btn_send_sms_main.clicked.connect(self.send_sms_main)
        self.btn_show_sms.clicked.connect(self.sms_inbox_manager.show_inbox_sms)
        self.btn_clear_sms_main.clicked.connect(self.sms_inbox_manager.clear_all_sms)
        
        # แก้ไข Enter key connections - ใช้วิธีที่ปลอดภัยกว่า
        try:
            # สำหรับ AT Command ComboBox
            if hasattr(self.at_combo_main, 'lineEdit'):
                line_edit = self.at_combo_main.lineEdit()
                if line_edit:
                    line_edit.returnPressed.connect(self.send_at_command_main)
                    print("✅ AT Command Enter key connected successfully")
            else:
                # วิธีสำรอง - ใช้ QComboBox signal
                self.at_combo_main.editTextChanged.connect(self._handle_at_combo_change)
                print("✅ AT Command fallback connection established")
                    
        except Exception as e:
            print(f"❌ AT Command Enter key connection failed: {e}")
            # วิธีสำรองสุดท้าย - ใช้ key event
            self.at_combo_main.installEventFilter(self)

        try:
            # สำหรับ Phone number input
            self.input_phone_main.returnPressed.connect(self.send_sms_main)
            print("✅ Phone input Enter key connected successfully")
        except Exception as e:
            print(f"❌ Phone input Enter key connection failed: {e}")
            
        try:
            # สำหรับ SMS text input - ใช้ Ctrl+Enter
            from PyQt5.QtWidgets import QShortcut
            from PyQt5.QtGui import QKeySequence
            sms_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.input_sms_main)
            sms_shortcut.activated.connect(self.send_sms_main)
            print("✅ SMS Ctrl+Enter shortcut connected successfully")
        except Exception as e:
            print(f"❌ SMS shortcut connection failed: {e}")

    def _handle_at_combo_change(self, text):
        """Handle AT combo text change for fallback Enter key support"""
        # เก็บข้อความล่าสุด
        self._last_at_text = text

    def eventFilter(self, obj, event):
        """Event filter สำหรับ Enter key fallback"""
        if obj == self.at_combo_main:
            if event.type() == event.KeyPress:
                if event.key() == 16777220:
                    self.send_at_command_main()
                    return True
        return super().eventFilter(obj, event)

    def setup_keyboard_shortcuts(self):
        """ตั้งค่า keyboard shortcuts"""
        
        # Ctrl+Enter สำหรับส่ง AT Command
        at_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        at_shortcut.activated.connect(self.send_at_command_main)
        
        # F1 สำหรับ Help
        help_shortcut = QShortcut(QKeySequence("F1"), self)
        help_shortcut.activated.connect(self.show_at_command_helper)
        
        # F5 สำหรับ Refresh
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.refresh_ports)
        
        # Ctrl+L สำหรับ Clear Response
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_at_displays)
        
    # ==================== 3. APPLICATION INITIALIZATION ====================
    def initialize_application(self):
        """เริ่มต้นการทำงานของโปรแกรม - Enhanced with SMS setup"""
        # รีเฟรชพอร์ต
        self.refresh_ports()
        self.refresh_sms_inbox_counter()

        # ทดสอบ network connection
        self.sync_manager.test_network_connection()
        
        # เริ่ม Auto Sync เมื่อเริ่มโปรแกรม
        self.sync_manager.auto_sync_on_startup()

        # ถ้าเปิด auto ให้สตาร์ท monitor
        if self.auto_sms_monitor:
            self.start_sms_monitor()
        
        # เรียกเชื่อมต่อ serial และเริ่ม monitor
        port = self.port_combo.currentData()
        baudrate = int(self.baud_combo.currentText())

        if port and port != "Device not found":
            from managers.port_manager import SerialConnectionManager
            self.connection_manager = SerialConnectionManager(self)
            self.connection_manager.start_sms_monitor(port, baudrate)
            
            # ตั้งค่า SMS เพิ่มเติมหลังจากเชื่อมต่อ
            if hasattr(self, 'serial_thread') and self.serial_thread:
                # ใช้ QTimer เพื่อรอให้การเชื่อมต่อสมบูรณ์
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(2000, self.delayed_sms_setup)
        else:
            self.update_at_result_display("[INIT] No valid serial port to start monitoring")

    def delayed_sms_setup(self):
        """ตั้งค่า SMS หลังจากเชื่อมต่อแล้วสักครู่"""
        if hasattr(self, 'serial_thread') and self.serial_thread and self.serial_thread.isRunning():
            try:
                self.update_at_result_display("[DELAYED SETUP] Configuring SMS settings...")
                self.setup_sms_notifications()
            except Exception as e:
                self.update_at_result_display(f"[DELAYED SETUP ERROR] {e}")

    # ==================== 4. PORT & CONNECTION MANAGEMENT ====================
    def refresh_ports(self):
        """รีเฟรชรายการพอร์ต Serial"""
        self.port_manager.refresh_ports(self.port_combo)
        self.reload_sim_with_progress()
    
    def reload_sim_with_progress(self):
        """โหลดข้อมูล SIM ใหม่พร้อมการแสดงสถานะ"""
        self.sims = self.port_manager.reload_sim_with_progress(self.port_combo, self.baud_combo)
        
        # อัพเดทตาราง
        if hasattr(self.table, 'set_data'):
            self.table.set_data(self.sims)
        
        # อัพเดทสถานะปุ่ม
        port = self.port_combo.currentData()
        port_ok = bool(port and port != "Device not found")
        
        if hasattr(self.table, 'update_sms_button_enable'):
            self.table.update_sms_button_enable(port_ok)

        if port_ok:
            self.setup_serial_monitor()
            self.update_at_result_display("[REFRESH] ✅ Refresh completed successfully!")
        else:
            self.update_at_result_display("[REFRESH] ❌ Refresh failed - no valid port")

    def setup_serial_monitor(self):
        """ตั้งค่า Serial Monitor Thread - Enhanced with SMS setup"""
        port = self.port_combo.currentData()
        baudrate = int(self.baud_combo.currentText())
        
        self.serial_thread = self.serial_connection_manager.setup_serial_monitor(port, baudrate)
        
        if self.serial_thread:
            self._cmt_buffer = None
            self._is_sending_sms = False

            # Setup enhanced display connection
            self._setup_enhanced_serial_connection()
            
            # เชื่อมต่อ SMS signals
            self.setup_sms_signal_connections()
            
            # Setup SMS notification commands
            self.setup_sms_notifications()

            # เปิด SMS monitor อัตโนมัติ
            self.auto_open_sms_monitor()

    def setup_sms_signal_connections(self):
        """เชื่อมต่อ SMS signals กับ handlers"""
        if self.serial_thread:
            try:
                # เชื่อมต่อ SMS signal กับ SMS handler
                self.serial_thread.new_sms_signal.connect(self.sms_handler.process_new_sms_signal)
                
                # เชื่อมต่อ SIM recovery signals
                self.serial_thread.sim_failure_detected.connect(self.on_sim_failure_detected)
                self.serial_thread.sim_ready_signal.connect(self.on_sim_ready_auto)
                self.serial_thread.cpin_ready_detected.connect(self.on_cpin_ready_detected)
                self.serial_thread.cpin_status_signal.connect(self.on_cpin_status_received)
                
                print("SMS signal connections established successfully")
                
            except Exception as e:
                print(f"Error setting up SMS signal connections: {e}")
    
    def test_sms_configuration(self):
        """ทดสอบการตั้งค่า SMS"""
        if self.serial_thread:
            try:
                import time
                time.sleep(0.5)
                
                # ตรวจสอบการตั้งค่า SMS
                test_commands = [
                    "AT+CMGF?",      # Check SMS mode
                    "AT+CNMI?",      # Check notification settings
                    "AT+CPMS?",      # Check storage settings
                ]
                
                self.update_at_result_display("[SMS TEST] Testing SMS configuration...")
                
                for cmd in test_commands:
                    self.serial_thread.send_command(cmd)
                    time.sleep(0.3)
                    
            except Exception as e:
                self.update_at_result_display(f"[SMS TEST ERROR] {e}")


    def setup_sms_notifications(self):
        """Setup AT commands สำหรับ SMS notifications"""
        if self.serial_thread and self.serial_thread.isRunning():
            try:
                # รอให้ serial thread พร้อม
                import time
                time.sleep(0.5)
                
                # ส่งคำสั่งตั้งค่า SMS notifications
                commands = [
                    ("AT+CMGF=1", "Set SMS text mode"),
                    ("AT+CNMI=2,2,0,1,0", "Enable SMS notifications"),
                    ("AT+CPMS=\"SM\",\"SM\",\"SM\"", "Set SMS storage")
                ]
                
                for cmd, description in commands:
                    success = self.serial_thread.send_command(cmd)
                    if success:
                        self.update_at_result_display(f"[SMS SETUP] {description}: {cmd}")
                    else:
                        self.update_at_result_display(f"[SMS SETUP ERROR] Failed to send: {cmd}")
                    time.sleep(0.2)
                
                self.update_at_result_display("[SMS SETUP] SMS notifications configured successfully")
                
                # ทดสอบการตั้งค่า
                self.test_sms_configuration()
                
            except Exception as e:
                self.update_at_result_display(f"[SMS SETUP ERROR] Failed to configure SMS: {e}")

    def start_sms_monitor(self):
        """เริ่ม SMS monitoring"""
        port = self.port_combo.currentData()
        baudrate = int(self.baud_combo.currentText())
        
        if port and port != "Device not found":
            self.serial_connection_manager.start_sms_monitor(port, baudrate)

    def test_sms_receiving(self):
        """ทดสอบการรับ SMS"""
        if self.serial_thread:
            # Test commands
            self.serial_thread.send_command("AT+CNMI?")  # Check SMS notification settings
            self.serial_thread.send_command("AT+CMGL=\"ALL\"")  # List all SMS
            self.update_at_result_display("[TEST] Testing SMS receiving setup...")

    def auto_open_sms_monitor(self):
        """เปิด SMS Real-time Monitor อัตโนมัติ"""
        if not self.auto_sms_monitor:
            return
            
        port = self.port_combo.currentData()
        baudrate = int(self.baud_combo.currentText())
        
        if port and port != "Device not found" and self.serial_thread:
            self.dialog_manager.auto_open_sms_monitor(port, baudrate, self.serial_thread)

    # ==================== 5. AT COMMAND HANDLING ====================
    def send_at_command_main(self):
        """ส่งคำสั่ง AT จากหน้าหลัก - แก้ไขหลัก"""
        # ตรวจสอบการเชื่อมต่อ serial
        if not hasattr(self, 'serial_thread') or not self.serial_thread:
            QMessageBox.warning(
                self, 
                "No Connection", 
                "❌ No serial connection found!\n\n"
                "Please:\n"
                "1. Select correct USB Port\n"
                "2. Click 'Refresh Ports'\n"
                "3. Make sure the modem is connected"
            )
            return
        
        # ตรวจสอบว่า thread ยังทำงานอยู่
        if not self.serial_thread.isRunning():
            QMessageBox.warning(
                self, 
                "Connection Lost", 
                "❌ Serial connection is not active!\n\n"
                "Please click 'Refresh Ports' to reconnect."
            )
            return
        
        # ดึงคำสั่ง AT
        cmd = self.at_combo_main.currentText().strip()
        if not cmd:
            QMessageBox.warning(self, "Empty Command", "📵 Please enter an AT command")
            return
        
        # ตรวจจับคำสั่งพิเศษ
        if cmd.upper() == "AT+RUN":
            self.special_command_handler.handle_at_run_command()
            self.update_at_command_display(cmd)
            return
        elif cmd.upper() == "AT+STOP":
            self.special_command_handler.handle_at_stop_command()
            self.update_at_command_display(cmd)
            return
        elif cmd.upper() == "AT+CLEAR":
            self.special_command_handler.handle_at_clear_command()
            self.update_at_command_display(cmd)
            return
        
        # ล้างหน้าจอผลลัพธ์
        self.clear_at_displays()
        
        # เพิ่มคำสั่งลงประวัติ
        self.at_command_manager.add_command_to_history(self.at_combo_main, cmd)
        
        # แสดงคำสั่งที่ส่ง
        self.update_at_command_display(cmd)
        
        # ส่งคำสั่งผ่าน serial thread
        try:
            success = self.serial_thread.send_command(cmd)
            if not success:
                self.update_at_result_display("[ERROR] ❌ Failed to send command - serial connection issue")
        except Exception as e:
            self.update_at_result_display(f"[ERROR] ❌ Exception while sending command: {e}")


    def remove_at_command_main(self):
        self.at_command_manager.remove_command_from_history(self.at_combo_main)

    # ==================== 6. SMS HANDLING ====================
    def send_sms_main(self):
        """ส่ง SMS จากหน้าหลัก (ไม่ใช้ animation)"""
        # ป้องกันคลิกซ้ำ
        if getattr(self, '_sms_button_disabled', False):
            self.update_at_result_display("[SMS] กำลังส่ง SMS อยู่ กรุณารอสักครู่...")
            return

        phone_number = self.input_phone_main.text().strip()
        message = self.input_sms_main.toPlainText().strip()

        # ตรวจสอบข้อมูลที่ป้อน
        if not phone_number:
            QMessageBox.warning(self, "Missing Phone Number", "📵 Please enter a phone number")
            self.input_phone_main.setFocus()
            return

        if not message:
            QMessageBox.warning(self, "Missing Message", "📵 Please enter a message to send")
            self.input_sms_main.setFocus()
            return

        # ตั้งแฟลก & เปลี่ยนปุ่ม
        self._sms_button_disabled = True
        original_text = self.btn_send_sms_main.text()
        self.btn_send_sms_main.setText("กำลังส่ง...")
        self.btn_send_sms_main.setEnabled(False)

        try:
            if hasattr(self, 'sms_handler') and self.sms_handler:
                # หมายเหตุ: sms_handler.send_sms_main() ภายในจะเรียก self.show_loading_dialog() ให้เองแล้ว
                # จึงไม่ต้องเปิด loading ซ้ำที่นี่
                success = self.sms_handler.send_sms_main(phone_number, message)

                # อัปเดต log dialog/monitor ถ้ามี
                mon = getattr(self, 'sms_monitor_dialog', None)
                if mon:
                    try:
                        mon.log_updated.emit()
                    except Exception:
                        pass

                if success:
                    self.update_at_result_display(f"[SMS] ✅ SMS sent successfully to {phone_number}")
                    # ล้างฟอร์ม
                    self.input_phone_main.clear()
                    self.input_sms_main.clear()
                else:
                    # ข้อผิดพลาดและการแจ้งเตือนรายละเอียดถูกจัดการใน sms_handler แล้ว
                    self.update_at_result_display("[SMS ERROR] ❌ Send failed")
            else:
                self.update_at_result_display("[SMS ERROR] ❌ SMS handler not available")

        except Exception as e:
            self.update_at_result_display(f"[SMS ERROR] ❌ Exception while sending SMS: {e}")

        finally:
            # รีเซ็ตปุ่มหลัง 3 วินาที
            def reset_sms_button():
                self._sms_button_disabled = False
                self.btn_send_sms_main.setText(original_text)
                self.btn_send_sms_main.setEnabled(True)
                self.update_at_result_display("[SMS] พร้อมส่งข้อความถัดไป")

            QTimer.singleShot(3000, reset_sms_button)

    def show_loading_dialog(self):
        """แสดง Loading Dialog"""
        self.dialog_manager.show_loading_dialog()

    # เพิ่มเมธอดใหม่สำหรับแสดงรายการ SMS ที่ส่งไม่สำเร็จ
    def show_failed_sms_dialog(self):
        """แสดงหน้าต่างรายการ SMS ที่ส่งไม่สำเร็จ"""
        try:
            # ใช้ค่า index 2 สำหรับ SMS Fail
            dlg = SmsLogDialog(parent=self)
            dlg.combo.setCurrentIndex(2)
            dlg.load_log() 
            
            dlg.setModal(False)
            dlg.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
                            Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            dlg.show()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot open Failed SMS dialog: {e}")

    def on_sms_sending_finished(self, success: bool):
        if success:
            self.update_at_result_display("[SMS] ✅ Completed")
            # ปิด dialog โหลด (ถ้าเปิดอยู่)
            if getattr(self, 'dialog_manager', None) and hasattr(self.dialog_manager, 'close_loading_dialog'):
                QTimer.singleShot(500, self.dialog_manager.close_loading_dialog)
            # ล้างฟอร์ม
            if hasattr(self, 'input_phone_main'): self.input_phone_main.clear()
            if hasattr(self, 'input_sms_main'): self.input_sms_main.clear()
        else:
            self.update_at_result_display("[SMS ERROR] ❌ Failed")
            if getattr(self, 'dialog_manager', None) and hasattr(self.dialog_manager, 'close_loading_dialog'):
                QTimer.singleShot(1500, self.dialog_manager.close_loading_dialog)

    def on_new_sms_signal(self, data_line):
        """จัดการสัญญาณ SMS ใหม่"""
        self.sms_handler.process_new_sms_signal(data_line)
        self.on_new_sms_received()

    def on_realtime_sms_received(self, sender, message, datetime_str):
        """จัดการเมื่อได้รับ SMS real-time"""
        try:
            key = (datetime_str, sender, message)
            if key in self._notified_sms:
                return
            self._notified_sms.add(key)
            
            # 1) แสดงในหน้าหลัก
            display_text = f"[REAL-TIME SMS] {datetime_str} | {sender}: {message}"
            self.update_at_result_display(display_text)

            # 2) ✅ บันทึกลง log ด้วยฟังก์ชันที่คุณมีอยู่แล้ว
            self._save_sms_to_inbox_log(sender, message, datetime_str)

            # 3) แจ้ง LogDialog ให้โหลดข้อมูลใหม่
            self.on_sms_log_updated()

        except Exception as e:
            print(f"Error handling real-time SMS: {e}")
    
    def on_sms_log_updated(self):
        """จัดการเมื่อ SMS log ได้รับการอัพเดท"""
        # วนดู dialog ที่เปิดอยู่ ถ้าเป็น SmsLogDialog ให้สั่งโหลด log ใหม่
        for dlg in self.dialog_manager.open_dialogs:
            if isinstance(dlg, SmsLogDialog):
                dlg.load_log()
        try:
            self.update_at_result_display("[LOG UPDATE] SMS inbox log has been updated")
        except Exception as e:
            print(f"Error handling log update: {e}")

    # ==================== 7. SIM RECOVERY HANDLING ====================
    def on_sim_failure_detected(self):
        """จัดการเมื่อตรวจพบ SIM failure"""
        self.sim_recovery_in_progress = True
        self.update_at_result_display("[SIM FAILURE] 🚨 SIM failure detected! Auto-recovery starting...")
        
        self.show_non_blocking_message(
            "SIM Failure Detected",
            "⚠️ SIM failure detected!\n\nSystem is performing automatic recovery...\n\nPlease wait for the process to complete."
        )
        
        # เริ่มนับเวลา recovery
        QTimer.singleShot(10000, self.sim_recovery_manager.on_recovery_timeout)

    def on_cpin_ready_detected(self):
        """จัดการเมื่อตรวจพบ CPIN READY"""
        if self.sim_recovery_in_progress:
            self.update_at_result_display("[MANUAL] ✅ SIM card ready detected!")
            QTimer.singleShot(2000, self.finalize_manual_recovery)
        else:
            self.update_at_result_display("[AUTO] ✅ SIM ready detected - refreshing data...")

    def on_sim_ready_auto(self):
        """จัดการ SIM ready ในโหมดอัตโนมัติ"""
        if not self.sim_recovery_in_progress:
            self.update_at_result_display("[AUTO] SIM ready signal received")

            # เพิ่มตรงนี้: refresh ข้อมูล SIM อัตโนมัติ
            QTimer.singleShot(1500, self.auto_refresh_sim_data)
    
    def auto_refresh_sim_data(self):
        """รีเฟรชข้อมูล SIM อัตโนมัติเมื่อ SIM พร้อม"""
        self.update_at_result_display("[AUTO] ✅ SIM ready detected - refreshing SIM data...")
        self.reload_sim_with_progress()


    def on_cpin_status_received(self, status):
        """จัดการสถานะ CPIN ที่ได้รับ"""
        self.update_at_result_display(f"[CPIN STATUS] {status}")
        
        if status == "READY" and self.sim_recovery_in_progress:
            QTimer.singleShot(1500, self.finalize_manual_recovery)
        elif status in ["PIN_REQUIRED", "PUK_REQUIRED"]:
            if self.sim_recovery_in_progress:
                self.sim_recovery_in_progress = False
                self.show_non_blocking_message(
                    "SIM Recovery Failed",
                    f"📵 SIM recovery failed!\n\nSIM status: {status}\n\nPlease enter PIN/PUK manually."
                )

    def finalize_manual_recovery(self):
        """จบกระบวนการ recovery และรีเฟรชข้อมูล"""
        if not self.sim_recovery_in_progress:
            return
            
        self.sim_recovery_in_progress = False
        self.update_at_result_display("[MANUAL] Finalizing recovery and refreshing SIM data...")
        
        # รีเฟรชข้อมูล SIM
        self.sims = self.port_manager.reload_sim_with_progress(self.port_combo, self.baud_combo)
        self.table.set_data(self.sims)
        
        if self.sims and self.sims[0].imsi != "-":
            self.update_at_result_display(f"[MANUAL] ✅ Recovery successful! SIM data refreshed")
            self.show_non_blocking_message(
                "SIM Recovery Successful",
                f"✅ SIM recovery completed successfully!\n\nSIM Information:\n• Phone: {self.sims[0].phone}\n• Carrier: {self.sims[0].carrier}\n• Signal: {self.sims[0].signal}"
            )
        else:
            self.update_at_result_display(f"[MANUAL] 📵 Recovery completed but SIM data not fully available")

    # ==================== 8. DIALOG MANAGEMENT ====================
    def open_realtime_monitor(self):
        if not self.sms_monitor_dialog:
            port = self.current_port   # หรือค่าพอร์ตที่คุณใช้จริง
            baud = self.current_baud   # หรือค่า baudrate ที่คุณใช้จริง
            self.sms_monitor_dialog = SmsRealtimeMonitor(
                port, baud, parent=self, serial_thread=self.serial_thread
            )
            self.at_monitor_signal.connect(self.sms_monitor_dialog.append_from_main)   # ★

        self.sms_monitor_dialog.show()
        self.sms_monitor_dialog.raise_()
        self.sms_monitor_dialog.activateWindow()

    def show_sms_log_for_phone(self, phone):
        """แสดงประวัติ SMS สำหรับเบอร์ที่ระบุ"""
        self.dialog_manager.show_sms_log_dialog(filter_phone=phone)

    def on_sms_monitor_closed(self):
        """จัดการเมื่อ SMS Monitor ถูกปิด"""
        try:
            self.sms_monitor_dialog = None
            self.update_at_result_display("[SMS MONITOR] Real-time SMS monitor closed")
        except Exception as e:
            print(f"Error handling SMS monitor close: {e}")

    def show_non_blocking_message(self, title, message):
        """แสดง message box แบบ non-blocking"""
        self.dialog_manager.show_non_blocking_message(title, message)

    def prefill_sms_to_send(self, phone, message):
        """เติมข้อมูลเบอร์และข้อความลงในช่องส่ง SMS"""
        self.input_phone_main.setText(phone)
        self.input_sms_main.setPlainText(message)
        self.input_sms_main.setFocus()
        self.activateWindow()

    # ==================== 9. DISPLAY MANAGEMENT ====================
    def update_at_command_display(self, command):
        """อัพเดทการแสดงคำสั่ง AT"""
        current_text = self.at_command_display.toPlainText()
        if current_text:
            self.at_command_display.setPlainText(current_text + "\n" + command)
        else:
            self.at_command_display.setPlainText(command)
        
        cursor = self.at_command_display.textCursor()
        cursor.movePosition(cursor.End)
        self.at_command_display.setTextCursor(cursor)
    
    def update_at_result_display(self, result):
        """อัพเดทการแสดงผลลัพธ์ AT"""
        
        current_text = self.at_result_display.toPlainText()
        if current_text:
            self.at_result_display.setPlainText(current_text + "\n" + result)
        else:
            self.at_result_display.setPlainText(result)
        
        cursor = self.at_result_display.textCursor()
        cursor.movePosition(cursor.End)
        self.at_result_display.setTextCursor(cursor)

    def clear_at_displays(self):
        """ล้างการแสดง AT Command และผลลัพธ์"""
        self.at_command_display.clear()
        self.at_result_display.clear()
        # ถ้ากด Clear Response ให้รีเซ็ต SMS Inbox counter ด้วย
        self.incoming_sms_count = 0
        self.update_sms_inbox_counter(0)

    def on_toggle_response(self, hidden: bool):
        """จัดการการซ่อน/แสดง response display"""
        if hidden:
            self.at_result_display.hide()
            self.btn_clear_response.hide()
            self.btn_toggle_response.setText("Show")
        else:
            self.at_result_display.show()
            self.btn_clear_response.show()
            self.btn_toggle_response.setText("Hide")

    # ==================== 10. WINDOW EVENT HANDLERS ====================
    def closeEvent(self, event):
        """จัดการเมื่อปิดหน้าต่างหลัก"""
        try:
            # บันทึกการตั้งค่า
            geometry = self.geometry()
            self.settings_manager.update_window_geometry(
                geometry.x(), geometry.y(), geometry.width(), geometry.height()
            )
            
            # บันทึกการเชื่อมต่อล่าสุด
            port = self.port_combo.currentData() or ""
            baudrate = self.baud_combo.currentText()
            self.settings_manager.update_last_connection(port, baudrate)
            
            # หยุด serial thread
            self.serial_connection_manager.stop_serial_monitor()
                
            # ปิด dialogs ทั้งหมด
            self.dialog_manager.close_all_dialogs()
                        
        except Exception as e:
            print(f"Error during close: {e}")
        
        event.accept()

    def show_signal_quality_checker(self):
        """เปิดหน้าต่าง Enhanced Signal Quality Checker - Enhanced version"""
        try:
            port = self.port_combo.currentData()
            baudrate = int(self.baud_combo.currentText())
            
            if not port or port == "Device not found":
                QMessageBox.warning(self, "No Port Selected", 
                                "⚠ Please select a valid COM port first!")
                return
            
            if not self.serial_thread or not self.serial_thread.isRunning():
                QMessageBox.warning(self, "No Connection", 
                                "⚠ No active serial connection!")
                return
            
            self.update_at_result_display("[SIGNAL QUALITY] 🚀 Opening Signal Quality Checker...")
            
            if hasattr(self, 'display_manager'):
                self.display_manager.set_signal_monitoring_active(True)
            
            quality_window = show_enhanced_sim_signal_quality_window(
                port=port, 
                baudrate=baudrate, 
                parent=self, 
                serial_thread=self.serial_thread
            )
            
            if quality_window:
                # เพิ่มใน dialog manager
                if hasattr(self, 'dialog_manager'):
                    self.dialog_manager.open_dialogs.append(quality_window)
                
                quality_window.finished.connect(
                    lambda: self._on_signal_quality_window_closed()
                )

                self.update_at_result_display("[SIGNAL QUALITY] ✅ Signal Quality Checker opened!")
                return quality_window
            else:
                self.update_at_result_display("[SIGNAL QUALITY] ❌ Failed to open Signal Quality Checker")
                
        except Exception as e:
            self.update_at_result_display(f"[SIGNAL QUALITY] ❌ Error: {e}")

    def _on_signal_quality_window_closed(self):
        """เมื่อ Signal Quality window ปิด"""
        if hasattr(self, 'display_manager'):
            self.display_manager.set_signal_monitoring_active(False)
        
        self.update_at_result_display("[SIGNAL QUALITY] Signal Quality Checker closed - Enhanced Display Separation disabled")
    
    def create_enhanced_control_buttons(self, layout):
        """สร้างปุ่มควบคุมต่างๆ พร้อม Signal Filter Toggle"""
        layout.addSpacing(16)
        
        button_width = 120
        
        # ปุ่ม Signal Quality
        self.btn_signal_quality = QPushButton("📶 Signal Quality")
        self.btn_signal_quality.setFixedWidth(button_width + 20)
        layout.addWidget(self.btn_signal_quality)
        
        # ⭐ ปุ่ม Toggle Signal Filter
        self.btn_signal_filter = QPushButton("🔇 Filter: OFF")
        self.btn_signal_filter.setCheckable(True)
        self.btn_signal_filter.setFixedWidth(100)
        self.btn_signal_filter.clicked.connect(self.toggle_signal_filter)
        self.btn_signal_filter.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #28a745;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:checked:hover {
                background-color: #218838;
            }
        """)
        layout.addWidget(self.btn_signal_filter)
        
        # ปุ่มอื่นๆ...
        layout.addStretch()

    def toggle_signal_filter(self, checked):
        """Toggle การกรอง Signal Quality responses"""
        if hasattr(self, 'display_manager') and hasattr(self.display_manager, 'filter_manager'):
            self.display_manager.filter_manager.set_signal_monitoring(checked)
            
            if checked:
                self.btn_signal_filter.setText("🔇 Filter: ON")
                self.update_at_result_display("[FILTER] Signal monitoring filter enabled")
            else:
                self.btn_signal_filter.setText("🔇 Filter: OFF") 
                self.update_at_result_display("[FILTER] Signal monitoring filter disabled")
        else:
            self.update_at_result_display("[FILTER] Display manager not available")

    def on_signal_quality_window_closed(self):
        """เมื่อ Signal Quality window ปิด - ปิดการกรอง"""
        if hasattr(self, 'display_manager') and hasattr(self.display_manager, 'filter_manager'):
            self.display_manager.filter_manager.set_signal_monitoring(False)
        
        self.update_at_result_display("[SIGNAL QUALITY] Signal Quality Checker closed - filtering disabled")

    def test_signal_filtering(self):
        """ทดสอบระบบกรองสัญญาณ"""
        if not hasattr(self, 'display_manager'):
            self.update_at_result_display("[TEST] Display manager not available")
            return
        
        self.update_at_result_display("[TEST] Testing signal filtering system...")
        
        # ทดสอบ 1: เปิดการกรอง
        self.display_manager.filter_manager.set_signal_monitoring(True)
        self.update_at_result_display("[TEST] ✅ Signal monitoring filter enabled")
        
        # ทดสอบ 2: ทดสอบการกรอง background responses
        test_responses = [
            "+CSQ: 14,99",
            "+CESQ: 99,99,255,255,15,44", 
            "OK",
            "Manual command response should show",
            "+COPS: 0,0,\"AIS\""
        ]
        
        for response in test_responses:
            should_show = self.display_manager.filter_manager.should_show_in_manual_display(response)
            status = "SHOW" if should_show else "HIDE"
            self.update_at_result_display(f"[TEST] {response} → {status}")
        
        # ทดสอบ 3: ทดสอบ manual command
        self.display_manager.register_manual_command("AT+CIMI")
        should_show_cimi = self.display_manager.filter_manager.should_show_in_manual_display("+CIMI: 520010012345678")
        should_show_ok = self.display_manager.filter_manager.should_show_in_manual_display("OK")
        
        self.update_at_result_display(f"[TEST] Manual CIMI response → {'SHOW' if should_show_cimi else 'HIDE'}")
        self.update_at_result_display(f"[TEST] Manual OK response → {'SHOW' if should_show_ok else 'HIDE'}")
        
        self.update_at_result_display("[TEST] Signal filtering test completed")

    def debug_display_filter_status(self):
        """แสดงสถานะปัจจุบันของ display filter"""
        if not hasattr(self, 'display_manager'):
            self.update_at_result_display("[DEBUG] No display manager")
            return
            
        filter_mgr = self.display_manager.filter_manager
        
        self.update_at_result_display("[DEBUG] === Display Filter Status ===")
        self.update_at_result_display(f"[DEBUG] Signal monitoring: {filter_mgr.signal_monitoring_active}")
        self.update_at_result_display(f"[DEBUG] Manual AT pending: {filter_mgr.manual_at_pending}")
        self.update_at_result_display(f"[DEBUG] Last manual command: {filter_mgr.last_manual_command}")
        self.update_at_result_display(f"[DEBUG] Background commands count: {len(filter_mgr.background_commands)}")
        self.update_at_result_display("[DEBUG] === End Status ===")

    def add_custom_filter_commands(self, commands_list):
        """เพิ่มคำสั่งที่ต้องการกรองเพิ่มเติม"""
        if hasattr(self, 'display_manager') and hasattr(self.display_manager, 'filter_manager'):
            filter_mgr = self.display_manager.filter_manager
            
            for cmd in commands_list:
                filter_mgr.background_commands.add(cmd.upper())
                # เพิ่ม response pattern ด้วย
                if cmd.startswith('AT+'):
                    response_pattern = '+' + cmd[3:] + ':'
                    filter_mgr.background_responses.add(response_pattern)
            
            self.update_at_result_display(f"[FILTER] Added {len(commands_list)} custom filter commands")
        else:
            self.update_at_result_display("[FILTER] Cannot add custom commands - filter manager not available")

    def test_signal_quality_button(self):
        """ทดสอบการทำงานของปุ่ม Signal Quality"""
        try:
            print("🧪 Testing Signal Quality button...")
            
            # ตรวจสอบว่าปุ่มถูกสร้างแล้ว
            if hasattr(self, 'btn_signal_quality'):
                print("✅ Button exists")
                print(f"✅ Button enabled: {self.btn_signal_quality.isEnabled()}")
                print(f"✅ Button visible: {self.btn_signal_quality.isVisible()}")
                
                # จำลองการคลิก
                self.btn_signal_quality.click()
                print("✅ Button click simulated")
            else:
                print("❌ Button does not exist")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")

# ใน sim_info_window.py - เพิ่มก่อน class SimInfoWindow
class EnhancedDisplayFilterManager:
    """จัดการการแยกการแสดงผลแบบ Enhanced"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        
        # แยกประเภทการแสดงผล
        self.display_targets = {
            'MANUAL': 'main_display',      # หน้าหลัก
            'SMS': 'sms_monitor',          # SMS Monitor
            'SIGNAL_QUALITY': 'signal_display',  # Signal Quality Checker
            'BACKGROUND': 'nowhere'        # ไม่แสดงเลย
        }
        
        # Response patterns  
        self.response_patterns = {
            'SIGNAL_QUALITY': ['+CSQ:', '+CESQ:', '+COPS:', '+CREG:'],
            'SMS': ['+CMTI:', '+CMT:', '+CMGR:', '+CMGL:', '+CMGS:', '+CMS ERROR:'],
            'SIM_INFO': ['+CIMI:', '+CCID:', '+CNUM:']
        }
        
        self.active_modes = {
            'signal_monitoring': False,
            'sms_monitoring': True,
            'manual_commands': True
        }
        
        print("✅ EnhancedDisplayFilterManager initialized")
    
    def process_response(self, data_line, source_hint=None):
        """ประมวลผล response และส่งไปยังปลายทางที่เหมาะสม"""
        data = (data_line or "").strip()
        if not data:
            return
        
        # กำหนดประเภท response
        response_type = self._classify_response(data, source_hint)
        
        # ส่งไปยังปลายทางที่เหมาะสม
        if response_type == 'MANUAL':
            self._send_to_main_display(data)
        elif response_type == 'SMS':
            self._send_to_sms_monitor(data)
        elif response_type == 'SIGNAL_QUALITY':
            # ไม่ต้องส่งไปไหน เพราะ Signal Quality จัดการเอง
            print(f"🔇 Signal Quality response filtered: {data[:50]}")
            pass
        elif response_type == 'BACKGROUND':
            # ไม่แสดงเลย
            print(f"🔇 Background response filtered: {data[:50]}")
            pass
    
    def _classify_response(self, data, source_hint=None):
        """จำแนกประเภท response"""
        data_upper = data.upper()
        
        # ใช้ source hint ถ้ามี
        if source_hint:
            return source_hint
        
        # ตรวจสอบ SMS responses
        if any(pattern in data_upper for pattern in self.response_patterns['SMS']):
            return 'SMS'
        
        # ตรวจสอบ Signal Quality responses
        if any(pattern in data_upper for pattern in self.response_patterns['SIGNAL_QUALITY']):
            if self.active_modes['signal_monitoring']:
                return 'SIGNAL_QUALITY'
            else:
                return 'MANUAL'  # ถ้าไม่ได้เปิด signal monitoring ให้แสดงในหน้าหลัก
        
        # ตรวจสอบ OK/ERROR ที่ตามหลัง Signal Quality commands
        if data_upper in ['OK', 'ERROR'] and self.active_modes['signal_monitoring']:
            return 'SIGNAL_QUALITY'
        
        # Default เป็น Manual
        return 'MANUAL'
    
    def _send_to_main_display(self, data):
        """ส่งไปแสดงในหน้าหลัก"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_data = f"[{timestamp}] {data}"
        self.parent_window.update_at_result_display(formatted_data)
    
    def _send_to_sms_monitor(self, data):
        """ส่งไป SMS Monitor"""
        if hasattr(self.parent_window, 'at_monitor_signal'):
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_data = f"[{timestamp}] {data}"
            self.parent_window.at_monitor_signal.emit(formatted_data)
    
    def set_signal_monitoring_active(self, active):
        """เปิด/ปิด signal monitoring mode"""
        self.active_modes['signal_monitoring'] = active
        status = "ON" if active else "OFF"
        print(f"🎯 Signal monitoring mode: {status}")

class DisplayFilterManager:
    """จัดการการกรองการแสดงผล - ไม่กระทบ SMS processing"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.manual_at_pending = False  # รอ response จาก manual command
        self.last_manual_command = None
        self.manual_command_timestamp = None

        # บันทึก command ที่ user ส่งเอง
        self.user_commands = set()

        # ติดตาม background/monitoring commands
        self.background_commands = {
            'AT+CESQ', 'AT+COPS', 'AT+CREG', 'AT+CIMI',
            'AT+CNUM',
        }

        # ติดตาม responses ที่ไม่ต้องการแสดง (prefix ของบรรทัดผลลัพธ์)
        self.background_responses = {
            '+CSQ:', '+CESQ:', '+COPS:', '+CREG:', '+CIMI:',
            '+CCID:', '+CNUM:', '+CPIN:', '+CGMI:', '+CGMM:',
            '+CGMR:', '+CGSN:',
        }

        self.background_command_echos = {
            'AT+CSQ', 'AT+CESQ', 'AT+COPS?', 'AT+CREG?'
        }

        # ใช้จำว่าเพิ่งซ่อนบรรทัดจาก monitor → เพื่อซ่อน OK/ERROR ถัดมา
        self._suppress_next_ok = False

        # อนุญาตให้ส่งไปแสดงที่ SMS Monitor เฉพาะ “เหตุการณ์ SMS” เท่านั้น
        self.sms_only_prefixes = {
            '+CMTI:',   # มี SMS ใหม่
            '+CMT:',    # ข้อความส่งถึงเครื่อง (deliver)
            '+CMGR:',   # อ่านจากกล่อง
            '+CMGL:',   # list กล่อง
            '+CMGS:',   # ส่งสำเร็จ
            '+CMSS:',   # ส่งจาก storage
            '+CMS ERROR:',
        }

        # ติดตามสถานะ Signal Quality monitoring
        self.signal_monitoring_active = False
        
    def register_manual_command(self, command):
        """บันทึกว่า user ส่งคำสั่ง manual"""
        self.manual_at_pending = True
        self.last_manual_command = command.upper()
        self.manual_command_timestamp = datetime.now()
        self.user_commands.add(command.upper())
        
        print(f"[DISPLAY FILTER] Manual command registered: {command}")
    
    def set_signal_monitoring(self, active: bool):
        """ตั้งค่าสถานะการ monitoring สัญญาณ"""
        self.signal_monitoring_active = active
        if active:
            print("[DISPLAY FILTER] Signal monitoring mode: ON")
        else:
            print("[DISPLAY FILTER] Signal monitoring mode: OFF")
    
    def should_show_in_manual_display(self, data):
        data_clean = (data or "").strip()
        upper = data_clean.upper()

        # 1) ถ้าเป็นคำสั่งที่ผู้ใช้กดเอง → แสดงทุกบรรทัดจนจบ (OK/ERROR)
        if self.manual_at_pending:
            if self._is_end_response(data_clean):
                self.manual_at_pending = False
            return True

        # 2) ระหว่าง monitoring สัญญาณ → ซ่อนทุกอย่างของฝั่ง monitor
        if self.signal_monitoring_active:
            # 2.1 ซ่อน echo ของคำสั่ง monitoring
            if upper in self.background_command_echos:
                self._suppress_next_ok = True
                return False

            # 2.2 ซ่อน response กลุ่มสัญญาณ/เครือข่าย
            if any(resp in data_clean for resp in self.background_responses):
                self._suppress_next_ok = True
                return False

            # 2.3 ซ่อน OK/ERROR ต่อจากสิ่งที่ซ่อน
            if upper in ['OK', 'ERROR'] and self._suppress_next_ok:
                self._suppress_next_ok = False
                return False

        # 3) กรณีไม่ใช่ manual → ไม่โชว์ในหน้าหลัก
        return False

    def should_show_in_monitor(self, data):
        data_clean = (data or "").strip()

        # ไม่ส่งซ้ำสิ่งที่ผู้ใช้กดเอง (manual) ไป SMS Monitor
        if self.manual_at_pending:
            return False

        # ให้ผ่านเฉพาะข้อความบ่งชี้เหตุการณ์ SMS เท่านั้น
        if any(data_clean.startswith(p) for p in self.sms_only_prefixes):
            return True

        # นอกนั้น (รวมทั้ง CSQ/CESQ/COPS/CREG, echo, OK/ERROR) ไม่ต้องส่งเข้า SMS Monitor
        return False
    
    def _is_end_response(self, data):
        """ตรวจสอบว่าเป็น response ท้ายสุด"""
        end_indicators = ['OK', 'ERROR', '+CME ERROR:', '+CMS ERROR:']
        return any(data.startswith(indicator) for indicator in end_indicators)
    
    def _is_background_response(self, data):
        """ตรวจสอบว่าเป็น response จาก background monitoring"""
        return any(resp in data for resp in self.background_responses)
    
    def _is_manual_response(self, data):
        """ตรวจสอบ response ที่เป็น Manual แน่นอน"""
        # Response ที่มักจะเป็น Manual command
        manual_responses = [
            '+CPIN:', '+CSQ:', '+COPS:', '+CCID:', '+CIMI:', '+CNUM:',
            '+CMGL:', '+CMGR:', '+CGMI:', '+CGMM:', '+CGMR:', '+CGSN:',
            'OK', 'ERROR', '+CME ERROR:', '+CMS ERROR:', '>'
        ]
        
        return any(data.startswith(resp) for resp in manual_responses)

class EnhancedResponseDisplayManager:
    """จัดการการแสดงผลแบบแยก - ไม่กระทบ SMS"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.filter_manager = DisplayFilterManager(parent_window)
        self._recent = deque(maxlen=50)    # (text, t)
        self._dedup_window = 1.2           # วินาที

        self.signal_monitoring_active = False
    
    def set_signal_monitoring_active(self, active):
        """เปิด/ปิด signal monitoring mode"""
        self.signal_monitoring_active = active
        
        # อัพเดท filter manager ด้วย
        if hasattr(self.filter_manager, 'set_signal_monitoring'):
            self.filter_manager.set_signal_monitoring(active)
        
        status = "ON" if active else "OFF"
        print(f"🎯 Signal monitoring mode: {status}")
    
        
    def process_response(self, data_line):
        """ประมวลผล response แล้วส่งไปแสดงผลที่ถูกต้อง (พร้อม de-dup)"""
        try:
            data = (data_line or "").strip()
            if not data:
                return

            # de-dup: ข้ามถ้าบรรทัดเดียวกันเพิ่งแสดงไปในช่วงสั้น ๆ
            now = monotonic()
            for txt, t in list(self._recent):
                if data == txt and (now - t) <= self._dedup_window:
                    return
            self._recent.append((data, now))

            # ตัดสินใจการแสดงผล
            show_in_manual  = self.filter_manager.should_show_in_manual_display(data)
            show_in_monitor = self.filter_manager.should_show_in_monitor(data)

            if show_in_manual:
                self._display_in_manual(data)

            if show_in_monitor:
                self._display_in_monitor(data)

        except Exception as e:
            print(f"Error in response processing: {e}")
            self._display_in_manual(f"[ERROR] {data_line}")
    
    def _display_in_manual(self, data):
        """แสดงใน Manual Response (หน้าหลัก)"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_data = f"[{timestamp}] {data}"
        self.parent_window.update_at_result_display(formatted_data)
        print(f"[MANUAL DISPLAY] {data}")
    
    def _display_in_monitor(self, data):
        """แสดงใน SMS Monitor"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_data = f"[{timestamp}] {data}"
        
        # ส่งไป SMS Monitor ถ้ามี
        if hasattr(self.parent_window, 'at_monitor_signal'):
            self.parent_window.at_monitor_signal.emit(formatted_data)
        
        print(f"[MONITOR DISPLAY] {data}")
    
    def register_manual_command(self, command):
        """บันทึก manual command ที่ user ส่ง"""
        self.filter_manager.register_manual_command(command)
