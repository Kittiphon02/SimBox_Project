# from PyQt5.QtWidgets import (
#     QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit,
#     QPushButton, QLabel, QComboBox, QGroupBox, QSizePolicy, QMessageBox, QSpacerItem, QTextEdit,
#     QSystemTrayIcon, QDialog
# )
# from PyQt5.QtCore import Qt, QTimer
# import serial.tools.list_ports
# import serial
# import time
# import sys
# import re
# import csv
# import os
# from datetime import datetime

# from services.sim_model import load_sim_data
# from widgets.sim_table_widget import SimTableWidget
# from widgets.sms_log_dialog import SmsLogDialog
# from services.sms_log import append_sms_log
# from v1.serial_service import SerialMonitorThread
# from v1.loading_widget import LoadingWidget

# # ==================== IMPORT NEW STYLES ====================
# from styles import MainWindowStyles, GlobalColorScheme


# # ==================== UTILITY FUNCTIONS ====================
# def list_serial_ports():
#     """ดึงรายชื่อพอร์ต Serial ที่มีในระบบ [("COM9", "Simcom HS-USB AT PORT 9001"), ...]"""
#     return [(p.device, p.description) for p in serial.tools.list_ports.comports()]


# # ==================== MAIN APPLICATION CLASS ====================
# class SimInfoWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
        
#         # ==================== 1. INITIALIZATION ====================
#         self.serial_thread = None
#         self.sims = []
        
#         # buffer สำหรับเก็บ header ของ +CMT: จนกว่าจะได้ body
#         self._cmt_buffer = None
#         # เซ็ตเก็บ SMS ที่แจ้งเตือนไปแล้ว (timestamp, sender, message)
#         self._notified_sms = set()
        
#         # ตัวแปรควบคุมการเปิด SMS Monitor อัตโนมัติ
#         self.auto_sms_monitor = True

#         # ตัวแปรสำหรับจัดการ SIM recovery
#         self.sim_recovery_in_progress = False
        
#         # เริ่มต้นการตั้งค่าโปรแกรม
#         self.load_settings()
#         self.setup_window()
#         self.setup_ui()
#         self.setup_styles()
#         self.setup_connections()
#         self.refresh_ports()

#         # ทดสอบ network connection เมื่อเริ่มโปรแกรม
#         self.test_network_connection()
#         # เพิ่ม Auto Sync เมื่อเริ่มโปรแกรม
#         self.auto_sync_on_startup()

#         # ==== ถ้าเปิด auto ให้สตาร์ท monitor ====
#         if self.auto_sms_monitor:
#             self.start_sms_monitor()

#     def auto_sync_on_startup(self):
#         """ซิงค์ log files เมื่อเริ่มโปรแกรม"""
#         try:
#             from services.sms_log import sync_logs_from_network_to_local, sync_logs_from_local_to_network
            
#             self.update_at_result_display("[SYNC] Starting auto-sync on startup...")
            
#             # ลองซิงค์จาก network มา local ก่อน (ดึงข้อมูลล่าสุด)
#             if sync_logs_from_network_to_local():
#                 self.update_at_result_display("[SYNC] ✅ Synced from network to local")
            
#             # แล้วซิงค์จาก local ไป network (push ข้อมูลใหม่)
#             if sync_logs_from_local_to_network():
#                 self.update_at_result_display("[SYNC] ✅ Synced from local to network")
                
#         except Exception as e:
#             self.update_at_result_display(f"[SYNC ERROR] Auto-sync failed: {e}")

#     def setup_periodic_sync(self):
#         """ตั้งค่า sync อัตโนมัติทุกๆ 5 นาที"""
#         try:
#             sync_timer = QTimer(self)
#             sync_timer.timeout.connect(self.periodic_sync)
#             sync_timer.start(300000)  # 5 นาที = 300,000 ms
#             self.update_at_result_display("[SYNC] ⏰ Periodic sync enabled (every 5 minutes)")
#         except Exception as e:
#             self.update_at_result_display(f"[SYNC ERROR] Failed to setup periodic sync: {e}")

#     def periodic_sync(self):
#         """ซิงค์แบบ periodic"""
#         try:
#             from services.sms_log import sync_logs_from_local_to_network
#             if sync_logs_from_local_to_network():
#                 self.update_at_result_display("[SYNC] 🔄 Periodic sync completed")
#         except Exception as e:
#             self.update_at_result_display(f"[SYNC ERROR] Periodic sync failed: {e}")
            
#     def test_network_connection(self):
#         """ทดสอบการเชื่อมต่อ network share"""
#         try:
#             from services.sms_log import get_log_directory
#             log_dir = get_log_directory()
            
#             if '\\\\' in log_dir or '//' in log_dir:
#                 self.update_at_result_display(f"[NETWORK] Using network share: {log_dir}")
#             else:
#                 self.update_at_result_display(f"[LOCAL] Using local directory: {log_dir}")
                
#         except Exception as e:
#             self.update_at_result_display(f"[NETWORK ERROR] {e}")

#     def on_toggle_response(self, hidden: bool):
#         if hidden:
#             self.at_result_display.hide()
#             self.btn_clear_response.hide()
#             self.btn_toggle_response.setText("Show")
#         else:
#             self.at_result_display.show()
#             self.btn_clear_response.show()
#             self.btn_toggle_response.setText("Hide")

#     # ==================== 2. SETTINGS MANAGEMENT ====================
#     def load_settings(self):
#         """โหลดการตั้งค่าโปรแกรม"""
#         try:
#             import json
#             with open('settings.json', 'r', encoding='utf-8') as f:
#                 settings = json.load(f)
                
#             self.auto_sms_monitor = settings.get('auto_sms_monitor', True)
            
#         except FileNotFoundError:
#             self.auto_sms_monitor = True
#         except Exception as e:
#             print(f"Error loading settings: {e}")
#             self.auto_sms_monitor = True

#     def save_settings(self):
#         """บันทึกการตั้งค่าโปรแกรม"""
#         try:
#             settings = {
#                 'auto_sms_monitor': getattr(self, 'auto_sms_monitor', True),
#                 'last_port': self.port_combo.currentText(),
#                 'last_baudrate': self.baud_combo.currentText()
#             }
            
#             import json
#             if not os.path.exists('settings.json'):
#                 with open('settings.json','w',encoding='utf-8') as f:
#                     json.dump(default_settings, f, indent=2)
                
#         except Exception as e:
#             print(f"Error saving settings: {e}")

#     # ==================== 3. WINDOW & UI SETUP ====================
#     def setup_window(self):
#         """ตั้งค่าหน้าต่างหลัก"""
#         self.setWindowTitle("SIM Management System")
#         self.resize(1050, 700)
#         self.setStyleSheet(MainWindowStyles.get_main_window_style())
        
#         self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
#         self.setAttribute(Qt.WA_DeleteOnClose, False)
    
#     def setup_ui(self):
#         """สร้าง UI components"""
#         main_widget = QWidget()
#         self.main_layout = QVBoxLayout()
#         main_widget.setLayout(self.main_layout)
#         self.setCentralWidget(main_widget)
        
#         self.create_header()
#         self.create_modem_controls()
#         self.create_at_command_display()
#         self.create_sim_table()
    
#     def create_header(self): 
#         """สร้างส่วนหัวของแอพพลิเคชัน"""
#         header = QLabel("SIM Management System")
#         header.setAlignment(Qt.AlignHCenter)
#         self.main_layout.addWidget(header)
#         self.header = header
    
#     def create_modem_controls(self):
#         """สร้างส่วนควบคุมโมเด็ม"""
#         modem_group = QGroupBox()
#         modem_group.setTitle(" Set up modem connection ")
#         modem_layout = QHBoxLayout()
        
#         # Port Selection
#         modem_layout.addWidget(QLabel("USB Port:"))
#         self.port_combo = QComboBox()
#         self.port_combo.setEditable(True)
#         self.port_combo.setFixedWidth(220)
#         modem_layout.addWidget(self.port_combo)
        
#         # Baudrate Selection
#         modem_layout.addSpacing(14)
#         modem_layout.addWidget(QLabel("Baudrate:"))
#         self.baud_combo = QComboBox()
#         baudrates = ['9600', '19200', '38400', '57600', '115200']
#         self.baud_combo.addItems(baudrates)
#         self.baud_combo.setCurrentText('115200')
#         self.baud_combo.setFixedWidth(110)
#         modem_layout.addWidget(self.baud_combo)
        
#         # Control Buttons
#         self.create_control_buttons(modem_layout)
        
#         modem_layout.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
#         modem_group.setLayout(modem_layout)
#         self.main_layout.addWidget(modem_group)
#         self.main_layout.addSpacing(16)
        
#         self.modem_group = modem_group
    
#     def create_control_buttons(self, layout):
#         """สร้างปุ่มควบคุมต่างๆ (เพิ่มปุ่ม Sync)"""
#         layout.addSpacing(16)
        
#         button_width = 120
        
#         self.btn_refresh = QPushButton("Refresh Ports")
#         self.btn_refresh.setFixedWidth(button_width)
#         layout.addWidget(self.btn_refresh)
        
#         self.btn_smslog = QPushButton("ดูประวัติ SMS")
#         self.btn_smslog.setFixedWidth(button_width)
#         layout.addWidget(self.btn_smslog)
        
#         self.btn_realtime_monitor = QPushButton("SMS Monitor")
#         self.btn_realtime_monitor.setFixedWidth(button_width)
#         layout.addWidget(self.btn_realtime_monitor)

#         # เพิ่มปุ่ม SIM Recovery
#         sim_recovery_btn = self.add_sim_recovery_button()
#         layout.addWidget(sim_recovery_btn)
        
#         # เพิ่มปุ่ม Sync
#         sync_btn = self.add_sync_button()
#         layout.addWidget(sync_btn)
        
#     def add_sync_button(self):
#         """เพิ่มปุ่ม Sync SMS Logs"""
#         self.btn_sync = QPushButton("🔄 Sync")
#         self.btn_sync.setFixedWidth(100)
#         self.btn_sync.clicked.connect(self.manual_sync)
#         self.btn_sync.setStyleSheet("""
#             QPushButton {
#                 background-color: #3498db;
#                 color: white;
#                 border: none;
#                 padding: 8px 16px;
#                 border-radius: 4px;
#                 font-weight: bold;
#             }
#             QPushButton:hover {
#                 background-color: #2980b9;
#             }
#             QPushButton:pressed {
#                 background-color: #21618c;
#             }
#             QPushButton:disabled {
#                 background-color: #bdc3c7;
#                 color: #7f8c8d;
#             }
#         """)
#         return self.btn_sync

#     def manual_sync(self):
#         """ซิงค์แบบ manual"""
#         try:
#             self.update_at_result_display("[MANUAL SYNC] Starting manual sync...")
            
#             from services.sms_log import sync_logs_from_network_to_local, sync_logs_from_local_to_network
            
#             # ซิงค์ทั้งสองทิศทาง
#             network_to_local = sync_logs_from_network_to_local()
#             local_to_network = sync_logs_from_local_to_network()
            
#             if network_to_local or local_to_network:
#                 self.update_at_result_display("[MANUAL SYNC] ✅ Sync completed successfully")
#                 self.show_non_blocking_message(
#                     "Sync Completed", 
#                     "🔄 SMS logs synchronized successfully!\n\n" +
#                     f"Network → Local: {'✅' if network_to_local else '➖'}\n" +
#                     f"Local → Network: {'✅' if local_to_network else '➖'}"
#                 )
#             else:
#                 self.update_at_result_display("[MANUAL SYNC] ℹ️ No sync needed - files are up to date")
                
#         except Exception as e:
#             self.update_at_result_display(f"[MANUAL SYNC ERROR] {e}")
#             self.show_non_blocking_message(
#                 "Sync Error", 
#                 f"❌ Manual sync failed:\n\n{e}\n\nPlease check network connection and permissions."
#             )

#     def create_at_command_display(self):
#         """สร้างส่วนแสดง AT Command และผลลัพธ์"""
#         at_group = QGroupBox(" AT Command Display ")
#         main_at_layout = QVBoxLayout()
#         main_at_layout.setContentsMargins(8, 8, 8, 8)
#         main_at_layout.setSpacing(10)

#         # ส่วนบน: ป้อนคำสั่ง AT
#         input_layout = QHBoxLayout()
#         input_layout.addWidget(QLabel("AT Command:"))

#         self.at_combo_main = QComboBox()
#         self.at_combo_main.addItems([
#             "AT", "ATI", "AT+CNUM", "AT+CIMI", "AT+CCID", "AT+CSQ",
#             "AT+CMGF=1", "AT+CPIN?", "AT+CGSN", "AT+CMGL=\"STO SENT\"",
#             "AT+CMGW=\"0653988461\"", "AT+CMSS=3", "AT+CMGL=\"REC READ\"",
#             "AT+CMGL=\"STO UNSENT\"", "AT+CMGL=\"REC UNREAD\"", "AT+CMGL=\"ALL\"",
#             "AT+NETOPEN", "AT+CNMI=2,2,0,0,0,", "AT+RUN", "AT+STOP", "AT+CLEAR"
#         ])
#         self.at_combo_main.setEditable(True)
#         self.at_combo_main.setFixedWidth(300)
#         input_layout.addWidget(self.at_combo_main)

#         self.btn_del_cmd = QPushButton("DELETE")
#         self.btn_del_cmd.setFixedWidth(100)
#         input_layout.addWidget(self.btn_del_cmd)

#         self.input_cmd_main = QTextEdit()
#         self.input_cmd_main.setPlainText(self.at_combo_main.currentText())
#         self.input_cmd_main.setFixedHeight(40)
#         input_layout.addWidget(self.input_cmd_main)

#         self.at_combo_main.currentTextChanged.connect(self.input_cmd_main.setPlainText)

#         self.load_at_command_history()
#         main_at_layout.addLayout(input_layout)
#         main_at_layout.addSpacing(10)

#         # ส่วนกลาง: ซ้าย (SMS) + ขวา (Response)
#         middle_layout = QHBoxLayout()

#         # ซ้าย: SMS input + ปุ่ม + คำสั่งเก่า
#         left_layout = QVBoxLayout()
#         left_layout.addWidget(QLabel("SMS messages:"))
#         self.input_sms_main = QTextEdit()
#         self.input_sms_main.setFixedHeight(50)
#         left_layout.addWidget(self.input_sms_main)

#         left_layout.addWidget(QLabel("Telephone number:"))
#         self.input_phone_main = QLineEdit()
#         self.input_phone_main.setPlaceholderText("Enter destination number...")
#         self.input_phone_main.setFixedHeight(35)
#         left_layout.addWidget(self.input_phone_main)
#         left_layout.addSpacing(10)

#         btn_at_layout = QHBoxLayout()
#         self.btn_send_at = QPushButton("Send AT")
#         self.btn_send_at.setFixedWidth(120)
#         self.btn_send_sms_main = QPushButton("Send SMS")
#         self.btn_send_sms_main.setFixedWidth(100)
#         self.btn_show_sms = QPushButton("SMS inbox")
#         self.btn_show_sms.setFixedWidth(120)
#         self.btn_clear_sms_main = QPushButton("Delete SMS")
#         self.btn_clear_sms_main.setFixedWidth(130)
        
#         for btn in (self.btn_send_at, self.btn_send_sms_main, self.btn_show_sms, self.btn_clear_sms_main):
#             btn_at_layout.addWidget(btn)
#         btn_at_layout.addStretch()
#         left_layout.addLayout(btn_at_layout)
#         left_layout.addSpacing(10)

#         left_layout.addWidget(QLabel("AT Command:"))
#         self.at_command_display = QTextEdit()
#         self.at_command_display.setFixedHeight(80)
#         self.at_command_display.setReadOnly(True)
#         self.at_command_display.setPlaceholderText("The AT commands sent will be displayed here...")
#         left_layout.addWidget(self.at_command_display)
#         middle_layout.addLayout(left_layout, stretch=1)

#         # ขวา: Result Display + Toggle
#         result_layout = QVBoxLayout()

#         header_layout = QHBoxLayout()
#         header_layout.setContentsMargins(0,0,0,0)
#         header_layout.setSpacing(4)
#         lbl = QLabel("Response:")
#         lbl.setStyleSheet("font-weight: bold;")
#         header_layout.addWidget(lbl)

#         self.btn_toggle_response = QPushButton("Hide")
#         self.btn_toggle_response.setCheckable(True)
#         self.btn_toggle_response.setMaximumWidth(60)
#         self.btn_toggle_response.toggled.connect(self.on_toggle_response)
#         header_layout.addWidget(self.btn_toggle_response)
#         header_layout.addStretch()
#         result_layout.addLayout(header_layout)

#         self.at_result_display = QTextEdit()
#         self.at_result_display.setMinimumHeight(250)
#         self.at_result_display.setReadOnly(True)
#         self.at_result_display.setPlaceholderText("The results from the modem will be displayed here...")
#         result_layout.addWidget(self.at_result_display)

#         self.btn_clear_response = QPushButton("Clear Response")
#         self.btn_clear_response.setFixedWidth(120)
#         self.btn_clear_response.clicked.connect(self.clear_at_displays)
#         result_layout.addWidget(self.btn_clear_response, 0, Qt.AlignRight)

#         middle_layout.addLayout(result_layout, stretch=1)
#         main_at_layout.addLayout(middle_layout)

#         at_group.setLayout(main_at_layout)
#         self.main_layout.addWidget(at_group)
#         self.main_layout.addSpacing(16)
#         self.at_group = at_group

#     def create_sim_table(self):
#         """สร้างตารางแสดงข้อมูลซิม"""
#         self.table = SimTableWidget(self.sims, history_callback=self.show_sms_log_for_phone)
#         self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
#         # ตั้งค่า font monospace สำหรับ Unicode bars
#         from PyQt5.QtGui import QFont
#         monospace_font = QFont("Consolas", 12)
#         if not monospace_font.exactMatch():
#             monospace_font = QFont("Courier New", 12)
#         self.table.setFont(monospace_font)
        
#         self.main_layout.addWidget(self.table, stretch=1)
    
#     # ==================== 7. การปรับแต่งสีตามระดับสัญญาณ ====================
#     def get_signal_color_enhanced(self, signal_text):
#         """กำหนดสีตามความแรงสัญญาณ - Enhanced version"""
#         try:
#             # ตรวจสอบ bars pattern
#             if '▁▃▅█' in signal_text:
#                 return '#27ae60'  # เขียวสด - Excellent
#             elif '▁▃▅▇' in signal_text:
#                 return '#2ecc71'  # เขียว - Good
#             elif '▁▃▁▁' in signal_text:
#                 return '#f39c12'  # เหลือง/ส้ม - Fair
#             elif '▁▁▁▁' in signal_text:
#                 if 'No Signal' in signal_text or 'Error' in signal_text:
#                     return '#95a5a6'  # เทา - No signal
#                 else:
#                     return '#e74c3c'  # แดง - Poor
#             else:
#                 # Fallback สำหรับ dBm values
#                 match = re.search(r'-?(\d+)', signal_text)
#                 if not match:
#                     return '#95a5a6'
#                 dbm_value = -int(match.group(1))
#                 if dbm_value >= -70:
#                     return '#27ae60'
#                 elif dbm_value >= -85:
#                     return '#2ecc71'
#                 elif dbm_value >= -100:
#                     return '#f39c12'
#                 elif dbm_value >= -110:
#                     return '#e74c3c'
#                 else:
#                     return '#95a5a6'
#         except (ValueError, AttributeError):
#             return '#95a5a6'  # fallback color

#     # ==================== 8. การเพิ่ม Tooltip สำหรับ Signal Bars ====================
#     def get_signal_tooltip_enhanced(self, signal_text):
#         """สร้าง tooltip ที่อธิบายความหมายของ signal bars"""
#         try:
#             if '▁▃▅█' in signal_text:
#                 return "▁▃▅█ Excellent Signal\n≥ -70 dBm\n4 bars - สัญญาณแรงมาก"
#             elif '▁▃▅▇' in signal_text:
#                 return "▁▃▅▇ Good Signal\n-85 to -71 dBm\n3 bars - สัญญาณดี"
#             elif '▁▃▁▁' in signal_text:
#                 return "▁▃▁▁ Fair Signal\n-100 to -86 dBm\n2 bars - สัญญาณปานกลาง"
#             elif '▁▁▁▁' in signal_text:
#                 if 'No Signal' in signal_text:
#                     return "▁▁▁▁ No Signal\nไม่มีสัญญาณ"
#                 else:
#                     return "▁▁▁▁ Poor Signal\n≤ -110 dBm\n1 bar - สัญญาณอ่อน"
#             else:
#                 return f"Signal: {signal_text}"
#         except Exception:
#             return "Signal information"

        
#     def setup_styles(self):
#         """ตั้งค่า CSS styles จากไฟล์ใหม่"""
#         self.header.setStyleSheet(MainWindowStyles.get_header_style())
        
#         self.modem_group.setStyleSheet(MainWindowStyles.get_modem_group_style())
#         self.at_group.setStyleSheet(MainWindowStyles.get_at_group_style())
        
#         self.at_combo_main.setStyleSheet(MainWindowStyles.get_at_combo_style())
#         self.input_cmd_main.setStyleSheet(MainWindowStyles.get_input_cmd_style())
#         self.input_sms_main.setStyleSheet(MainWindowStyles.get_sms_input_style())
#         self.input_phone_main.setStyleSheet(MainWindowStyles.get_phone_input_style())
        
#         self.btn_del_cmd.setStyleSheet(MainWindowStyles.get_delete_button_style())
#         self.btn_send_at.setStyleSheet(MainWindowStyles.get_send_at_button_style())
#         self.btn_show_sms.setStyleSheet(MainWindowStyles.get_show_sms_button_style())
#         self.btn_send_sms_main.setStyleSheet(MainWindowStyles.get_send_sms_button_style())
#         self.btn_clear_sms_main.setStyleSheet(MainWindowStyles.get_clear_sms_button_style())
#         self.btn_clear_response.setStyleSheet(MainWindowStyles.get_clear_response_button_style())
#         self.btn_refresh.setStyleSheet(MainWindowStyles.get_refresh_button_style())
#         self.btn_smslog.setStyleSheet(MainWindowStyles.get_smslog_button_style())
#         self.btn_realtime_monitor.setStyleSheet(MainWindowStyles.get_realtime_monitor_style())
#         self.btn_toggle_response.setStyleSheet(MainWindowStyles.get_toggle_button_style())
        
#         self.at_command_display.setStyleSheet(MainWindowStyles.get_command_display_style())
#         self.at_result_display.setStyleSheet(MainWindowStyles.get_result_display_style())
        
#         self.table.setStyleSheet(MainWindowStyles.get_table_style())
    
#     def setup_connections(self):
#         """เชื่อมต่อ signals และ slots"""
#         self.btn_refresh.clicked.connect(self.refresh_ports)
#         self.btn_smslog.clicked.connect(self.on_view_sms_log)
#         self.btn_realtime_monitor.clicked.connect(self.open_realtime_monitor)
#         self.btn_show_sms.clicked.connect(self.open_sms_history)
        
#         self.btn_send_at.clicked.connect(self.send_at_command_main)
#         self.btn_show_sms.clicked.connect(self.show_inbox_sms_main)
#         self.btn_send_sms_main.clicked.connect(self.send_sms_main)
#         self.btn_clear_sms_main.clicked.connect(self.clear_all_sms_main)
#         self.btn_del_cmd.clicked.connect(self.remove_at_command_main)
        
#         # เพิ่มการเชื่อมต่อปุ่ม sync
#         if hasattr(self, 'btn_sync'):
#             self.btn_sync.clicked.connect(self.manual_sync)

#     # ==================== 4. SERIAL PORT MANAGEMENT ====================
#     def refresh_ports(self):
#         """รีเฟรชรายการพอร์ต Serial พร้อมการอัพเดทที่ดีขึ้น"""
#         self.update_at_result_display("[REFRESH] Refreshing serial ports...")
        
#         current_data = self.port_combo.currentData()
#         ports = list_serial_ports()
#         self.port_combo.clear()

#         if ports:
#             for device, desc in ports:
#                 display = f"{device} - {desc}"
#                 self.port_combo.addItem(display, device)
#             self.update_at_result_display(f"[REFRESH] Found {len(ports)} serial ports")
#         else:
#             self.port_combo.addItem("Device not found", None)
#             self.update_at_result_display("[REFRESH] No serial ports found")

#         idx = self.port_combo.findData(current_data)
#         if idx >= 0:
#             self.port_combo.setCurrentIndex(idx)
#             self.update_at_result_display(f"[REFRESH] Restored previous port: {current_data}")
#         else:
#             self.port_combo.setCurrentIndex(self.port_combo.count() - 1)
#             self.update_at_result_display("[REFRESH] Selected default port")

#         # รีเฟรช SIM data
#         self.reload_sim_with_progress()
    
#     def reload_sim_with_progress(self):
#         """โหลดข้อมูล SIM ใหม่พร้อมการแสดงสถานะ (แก้ไขการอัพเดทตาราง)"""
#         self.update_at_result_display("[REFRESH] Reloading SIM data...")
        
#         port = self.port_combo.currentData()
#         baudrate = int(self.baud_combo.currentText())
#         port_ok = bool(port and port != "Device not found")

#         if port_ok:
#             try:
#                 # หยุด serial thread เดิม
#                 if self.serial_thread and self.serial_thread.isRunning():
#                     self.serial_thread.stop()
#                     self.serial_thread.wait()
#                     self.update_at_result_display("[REFRESH] Stopped previous serial connection")

#                 # โหลดข้อมูล SIM ใหม่
#                 self.update_at_result_display("[REFRESH] Loading SIM information...")
#                 self.sims = load_sim_data(port, baudrate)

#                 # อัพเดท signal strength
#                 for sim in self.sims:
#                     sig = self.query_signal_strength(port, baudrate)
#                     sim.signal = sig

#                 # **เพิ่มการ debug ข้อมูล SIM**
#                 self.debug_sim_data()

#                 # แสดงผลลัพธ์
#                 if self.sims and self.sims[0].imsi != "-":
#                     self.update_at_result_display(f"[REFRESH] ✅ SIM data loaded successfully!")
#                     self.update_at_result_display(f"[REFRESH] Phone: {self.sims[0].phone}")
#                     self.update_at_result_display(f"[REFRESH] IMSI: {self.sims[0].imsi}")
#                     self.update_at_result_display(f"[REFRESH] Carrier: {self.sims[0].carrier}")
#                     self.update_at_result_display(f"[REFRESH] Signal: {self.sims[0].signal}")
#                 else:
#                     self.update_at_result_display(f"[REFRESH] ⚠️ SIM data not available or SIM not ready")

#             except Exception as e:
#                 print(f"Error reloading SIM data: {e}")
#                 self.sims = []
#                 self.update_at_result_display(f"[REFRESH] ❌ Failed to reload SIM data: {e}")
#         else:
#             self.sims = []
#             self.update_at_result_display("[REFRESH] ❌ No valid port selected")

#         # **แก้ไขการอัพเดทตาราง**
#         try:
#             self.force_update_table()
            
#             # ถ้าตารางยังไม่แสดงผล ให้ลองสร้างใหม่
#             if self.sims and len(self.sims) > 0:
#                 import time
#                 time.sleep(0.1)  # รอให้ update เสร็จ
                
#                 # ตรวจสอบว่าข้อมูลแสดงหรือไม่
#                 if self.table.rowCount() == 0:
#                     self.update_at_result_display("[TABLE] Table still empty, recreating...")
#                     self.manual_recreate_table()
#                 else:
#                     # ตรวจสอบว่า cell มีข้อมูลหรือไม่
#                     first_item = self.table.item(0, 1)  # IMSI column
#                     if not first_item or first_item.text() == "":
#                         self.update_at_result_display("[TABLE] Table cells empty, recreating...")
#                         self.manual_recreate_table()
#                     else:
#                         self.update_at_result_display(f"[TABLE] ✅ Table shows data: {first_item.text()}")
            
#         except Exception as e:
#             self.update_at_result_display(f"[TABLE] Error in table update process: {e}")
        
#         # อัพเดทสถานะปุ่ม
#         if hasattr(self.table, 'update_sms_button_enable'):
#             self.table.update_sms_button_enable(port_ok)

#         if port_ok:
#             self.update_at_result_display("[REFRESH] Setting up serial monitor...")
#             self.setup_serial_monitor()
#             self.update_at_result_display("[REFRESH] ✅ Refresh completed successfully!")
#         else:
#             self.update_at_result_display("[REFRESH] ❌ Refresh failed - no valid port")

#     def debug_sim_data(self):
#         """Debug ข้อมูล SIM ที่โหลดมา"""
#         try:
#             self.update_at_result_display(f"[DEBUG] SIM data count: {len(self.sims) if self.sims else 0}")
            
#             if self.sims and len(self.sims) > 0:
#                 sim = self.sims[0]
#                 self.update_at_result_display(f"[DEBUG] SIM object type: {type(sim)}")
#                 self.update_at_result_display(f"[DEBUG] SIM attributes:")
                
#                 # ตรวจสอบ attributes ของ SIM object
#                 for attr in ['phone', 'imsi', 'iccid', 'carrier', 'signal']:
#                     if hasattr(sim, attr):
#                         value = getattr(sim, attr)
#                         self.update_at_result_display(f"[DEBUG]   {attr}: '{value}' (type: {type(value)})")
#                     else:
#                         self.update_at_result_display(f"[DEBUG]   {attr}: MISSING ATTRIBUTE")
#             else:
#                 self.update_at_result_display("[DEBUG] No SIM data found")
                
#         except Exception as e:
#             self.update_at_result_display(f"[DEBUG] Error debugging SIM data: {e}")

#     def force_update_table(self):
#         """บังคับอัพเดทตาราง พร้อม debug เพิ่มเติม"""
#         try:
#             self.update_at_result_display(f"[TABLE] Updating table with {len(self.sims) if self.sims else 0} SIM(s)")
            
#             # ตรวจสอบว่า table widget มีอยู่จริง
#             if not hasattr(self, 'table') or not self.table:
#                 self.update_at_result_display("[TABLE] ❌ Table widget not found!")
#                 return
            
#             self.update_at_result_display(f"[TABLE] Table widget type: {type(self.table)}")
#             self.update_at_result_display(f"[TABLE] Table visible: {self.table.isVisible()}")
#             self.update_at_result_display(f"[TABLE] Table enabled: {self.table.isEnabled()}")
            
#             # ตั้งค่าข้อมูลใหม่
#             self.table.set_data(self.sims)
            
#             # ตรวจสอบหลังจากตั้งค่าแล้ว
#             row_count = self.table.rowCount()
#             col_count = self.table.columnCount()
#             self.update_at_result_display(f"[TABLE] After set_data: {row_count} rows, {col_count} columns")
            
#             # ตรวจสอบข้อมูลในแต่ละ cell
#             for row in range(min(row_count, 1)):  # เช็คแค่แถวแรก
#                 for col in range(col_count):
#                     item = self.table.item(row, col)
#                     if item:
#                         self.update_at_result_display(f"[TABLE] Cell [{row},{col}]: '{item.text()}'")
#                     else:
#                         widget = self.table.cellWidget(row, col)
#                         if widget:
#                             self.update_at_result_display(f"[TABLE] Cell [{row},{col}]: <widget>")
#                         else:
#                             self.update_at_result_display(f"[TABLE] Cell [{row},{col}]: <empty>")
            
#             # บังคับให้ตารางอัพเดท
#             self.table.update()
#             self.table.repaint()
#             self.table.viewport().update()
#             self.table.viewport().repaint()
            
#             # ตรวจสอบ parent widget
#             if self.table.parent():
#                 self.table.parent().update()
#                 self.table.parent().repaint()
            
#             # อัพเดท main window
#             self.update()
#             self.repaint()
            
#             self.update_at_result_display(f"[TABLE] Table update completed")
            
#             # ถ้ามีข้อมูลแต่ไม่แสดง ให้ลองสร้างตารางใหม่
#             if self.sims and len(self.sims) > 0 and row_count > 0:
#                 self.update_at_result_display("[TABLE] Data exists and table has rows - checking visibility...")
#                 self.check_table_visibility()
                
#         except Exception as e:
#             self.update_at_result_display(f"[TABLE] ❌ Error updating table: {e}")
#             import traceback
#             self.update_at_result_display(f"[TABLE] Error details: {traceback.format_exc()}")

#     def check_table_visibility(self):
#             """ตรวจสอบการแสดงผลของตาราง"""
#             try:
#                 # ตรวจสอบ geometry
#                 geometry = self.table.geometry()
#                 self.update_at_result_display(f"[TABLE] Geometry: x={geometry.x()}, y={geometry.y()}, w={geometry.width()}, h={geometry.height()}")
                
#                 # ตรวจสอบ parent layout
#                 parent = self.table.parent()
#                 if parent:
#                     self.update_at_result_display(f"[TABLE] Parent: {type(parent)}")
#                     self.update_at_result_display(f"[TABLE] Parent visible: {parent.isVisible()}")
                
#                 # ตรวจสอบ layout
#                 layout = self.table.parent().layout() if self.table.parent() else None
#                 if layout:
#                     self.update_at_result_display(f"[TABLE] Parent layout: {type(layout)}")
#                     self.update_at_result_display(f"[TABLE] Layout count: {layout.count()}")
                
#                 # บังคับให้ table แสดงผล
#                 self.table.show()
#                 self.table.setVisible(True)
                
#                 # ตรวจสอบขนาดของตาราง
#                 if self.table.width() == 0 or self.table.height() == 0:
#                     self.update_at_result_display("[TABLE] ⚠️ Table has zero size - resizing...")
#                     self.table.resize(800, 200)
                
#             except Exception as e:
#                 self.update_at_result_display(f"[TABLE] Error checking visibility: {e}")

#     def manual_recreate_table(self):
#             """สร้างตารางใหม่ด้วยตนเอง"""
#             try:
#                 self.update_at_result_display("[TABLE] Manually recreating table...")
                
#                 # ลบตารางเดิม
#                 if hasattr(self, 'table') and self.table:
#                     self.table.setParent(None)
#                     self.table.deleteLater()
                
#                 # สร้างตารางใหม่
#                 from widgets.sim_table_widget import SimTableWidget
#                 self.table = SimTableWidget(self.sims, history_callback=self.show_sms_log_for_phone)
                
#                 # เพิ่มลง layout
#                 self.main_layout.addWidget(self.table, stretch=1)
                
#                 # ตั้งค่าให้แสดงผล
#                 self.table.show()
#                 self.table.setVisible(True)
                
#                 self.update_at_result_display("[TABLE] ✅ Table recreated successfully")
                
#             except Exception as e:
#                 self.update_at_result_display(f"[TABLE] ❌ Error recreating table: {e}")

#     def manual_populate_table(self):
#         """เพิ่มข้อมูลลงตารางด้วยตนเอง"""
#         try:
#             self.update_at_result_display("[MANUAL TABLE] Manually populating table...")
            
#             sim = self.sims[0]
            
#             # ตั้งค่าจำนวนแถวและคอลัมน์
#             self.table.setRowCount(1)
#             self.table.setColumnCount(5)
            
#             # ตั้งค่า headers
#             headers = ["Telephone", "IMSI", "ICCID", "Mobile network", "Signal"]
#             self.table.setHorizontalHeaderLabels(headers)
            
#             # เพิ่มข้อมูล
#             from PyQt5.QtWidgets import QTableWidgetItem
            
#             phone_text = sim.phone if sim.phone != "-" else "-"
#             imsi_text = sim.imsi if sim.imsi != "-" else "-"
#             iccid_text = getattr(sim, 'iccid', '-') if hasattr(sim, 'iccid') else "-"
#             carrier_text = sim.carrier if sim.carrier != "Unknown" else "Unknown"
#             signal_text = sim.signal if sim.signal != "N/A" else "No Signal (Error)"
            
#             self.table.setItem(0, 0, QTableWidgetItem(phone_text))
#             self.table.setItem(0, 1, QTableWidgetItem(imsi_text))
#             self.table.setItem(0, 2, QTableWidgetItem(iccid_text))
#             self.table.setItem(0, 3, QTableWidgetItem(carrier_text))
#             self.table.setItem(0, 4, QTableWidgetItem(signal_text))
            
#             self.update_at_result_display("[MANUAL TABLE] ✅ Table populated manually")
#             self.update_at_result_display(f"[MANUAL TABLE] Data: {phone_text} | {imsi_text} | {iccid_text} | {carrier_text} | {signal_text}")
            
#         except Exception as e:
#             self.update_at_result_display(f"[MANUAL TABLE] ❌ Error: {e}")

#     def smart_refresh_sim_data(self):
#         """รีเฟรชข้อมูล SIM แบบฉลาด (พร้อมแก้ไขตาราง)"""
#         try:
#             self.update_at_result_display("[SMART REFRESH] Smart refreshing SIM data...")
            
#             port = self.port_combo.currentData()
#             baudrate = int(self.baud_combo.currentText())
            
#             if port and port != "Device not found":
#                 # ตรวจสอบข้อมูลปัจจุบันก่อน
#                 current_has_data = (self.sims and len(self.sims) > 0 and 
#                                 self.sims[0].imsi != "-" and self.sims[0].imsi)
                
#                 if current_has_data:
#                     # ถ้ามีข้อมูลอยู่แล้ว ให้อัพเดทเฉพาะ signal strength
#                     self.update_at_result_display("[SMART REFRESH] SIM data already available, updating signal only...")
#                     for sim in self.sims:
#                         sig = self.query_signal_strength(port, baudrate)
#                         sim.signal = sig
                    
#                     # **บังคับอัพเดทตาราง**
#                     self.force_update_table()
#                     self.update_at_result_display(f"[SMART REFRESH] ✅ Signal updated: {self.sims[0].signal}")
#                 else:
#                     # ถ้าไม่มีข้อมูล ให้โหลดใหม่
#                     self.update_at_result_display("[SMART REFRESH] No SIM data, loading fresh data...")
#                     self.sims = load_sim_data(port, baudrate)
                    
#                     # อัพเดท signal strength
#                     for sim in self.sims:
#                         sig = self.query_signal_strength(port, baudrate)
#                         sim.signal = sig
                    
#                     # **บังคับอัพเดทตาราง**
#                     self.force_update_table()
                    
#                     if self.sims and self.sims[0].imsi != "-":
#                         self.update_at_result_display(f"[SMART REFRESH] ✅ SIM data refreshed!")
#                         self.update_at_result_display(f"[SMART REFRESH] Phone: {self.sims[0].phone}")
#                         self.update_at_result_display(f"[SMART REFRESH] IMSI: {self.sims[0].imsi}")
#                         self.update_at_result_display(f"[SMART REFRESH] Carrier: {self.sims[0].carrier}")
#                         self.update_at_result_display(f"[SMART REFRESH] Signal: {self.sims[0].signal}")
#                     else:
#                         self.update_at_result_display(f"[SMART REFRESH] ⚠️ SIM data still not ready")
#             else:
#                 self.update_at_result_display("[SMART REFRESH] ❌ No valid port available")
                    
#         except Exception as e:
#             self.update_at_result_display(f"[SMART REFRESH] ❌ Error: {e}")


#     # # เพิ่มฟังก์ชัน shortcut สำหรับการรีเฟรชด่วน
#     # def quick_refresh_sim_data(self):
#     #     """รีเฟรชข้อมูล SIM แบบด่วน (ไม่รีเฟรชพอร์ต)"""
#     #     try:
#     #         self.update_at_result_display("[QUICK REFRESH] Quick refreshing SIM data...")
            
#     #         port = self.port_combo.currentData()
#     #         baudrate = int(self.baud_combo.currentText())
            
#     #         if port and port != "Device not found":
#     #             # โหลดข้อมูล SIM ใหม่
#     #             self.sims = load_sim_data(port, baudrate)
                
#     #             # อัพเดท signal strength
#     #             for sim in self.sims:
#     #                 sig = self.query_signal_strength(port, baudrate)
#     #                 sim.signal = sig
                
#     #             # อัพเดทตาราง
#     #             self.table.set_data(self.sims)
                
#     #             if self.sims and self.sims[0].imsi != "-":
#     #                 self.update_at_result_display(f"[QUICK REFRESH] ✅ SIM data refreshed!")
#     #                 self.update_at_result_display(f"[QUICK REFRESH] Phone: {self.sims[0].phone}")
#     #                 self.update_at_result_display(f"[QUICK REFRESH] IMSI: {self.sims[0].imsi}")
#     #                 self.update_at_result_display(f"[QUICK REFRESH] Carrier: {self.sims[0].carrier}")
#     #                 self.update_at_result_display(f"[QUICK REFRESH] Signal: {self.sims[0].signal}")
#     #             else:
#     #                 self.update_at_result_display(f"[QUICK REFRESH] ⚠️ SIM data not ready")
#     #         else:
#     #             self.update_at_result_display("[QUICK REFRESH] ❌ No valid port available")
                
#     #     except Exception as e:
#     #         self.update_at_result_display(f"[QUICK REFRESH] ❌ Error: {e}")

#     def on_cpin_ready_detected(self):
#         """จัดการเมื่อตรวจพบ CPIN READY (สำหรับ manual recovery)"""
#         if self.sim_recovery_in_progress:
#             self.update_at_result_display("[MANUAL] ✅ SIM card ready detected!")
            
#             # รอให้ SIM เสถียรแล้วรีเฟรช
#             QTimer.singleShot(2000, self.finalize_manual_recovery)
#         else:
#             # ถ้าไม่ได้อยู่ในโหมด recovery ให้ทำการรีเฟรชธรรมดา
#             self.update_at_result_display("[AUTO] ✅ SIM ready detected - refreshing data...")
#             # QTimer.singleShot(1000, self.quick_refresh_sim_data)

#     def on_sim_ready_auto(self):
#         """จัดการ SIM ready ในโหมดอัตโนมัติ"""
#         if not self.sim_recovery_in_progress:
#             self.update_at_result_display("[AUTO] SIM ready signal received")
#             # สามารถเพิ่มการจัดการเพิ่มเติมได้ที่นี่

#     def on_cpin_status_received(self, status):
#         """จัดการสถานะ CPIN ที่ได้รับ"""
#         self.update_at_result_display(f"[CPIN STATUS] {status}")
        
#         if status == "READY" and self.sim_recovery_in_progress:
#             # ถ้า recovery กำลังทำงานและได้รับ READY ให้รีเฟรช
#             QTimer.singleShot(1500, self.finalize_manual_recovery)
#         elif status in ["PIN_REQUIRED", "PUK_REQUIRED"]:
#             # ถ้าต้องการ PIN/PUK ให้แจ้งผู้ใช้
#             if self.sim_recovery_in_progress:
#                 self.sim_recovery_in_progress = False
#                 self.show_non_blocking_message(
#                     "SIM Recovery Failed",
#                     f"❌ SIM recovery failed!\n\nSIM status: {status}\n\nPlease enter PIN/PUK manually."
#                 )

#     def finalize_manual_recovery(self):
#         """จบกระบวนการ recovery และรีเฟรชข้อมูล"""
#         if not self.sim_recovery_in_progress:
#             return
            
#         self.sim_recovery_in_progress = False
#         self.update_at_result_display("[MANUAL] Finalizing recovery and refreshing SIM data...")
        
#         try:
#             # รีเฟรชข้อมูล SIM
#             port = self.port_combo.currentData()
#             baudrate = int(self.baud_combo.currentText())
            
#             if port and port != "Device not found":
#                 # โหลดข้อมูล SIM ใหม่
#                 self.sims = load_sim_data(port, baudrate)
                
#                 # อัพเดท signal strength
#                 for sim in self.sims:
#                     sig = self.query_signal_strength(port, baudrate)
#                     sim.signal = sig
                
#                 # อัพเดทตาราง
#                 self.table.set_data(self.sims)
                
#                 # แสดงผลลัพธ์
#                 if self.sims and self.sims[0].imsi != "-":
#                     self.update_at_result_display(f"[MANUAL] ✅ Recovery successful! SIM data refreshed")
#                     self.update_at_result_display(f"[MANUAL] Phone: {self.sims[0].phone}")
#                     self.update_at_result_display(f"[MANUAL] IMSI: {self.sims[0].imsi}")
#                     self.update_at_result_display(f"[MANUAL] Carrier: {self.sims[0].carrier}")
#                     self.update_at_result_display(f"[MANUAL] Signal: {self.sims[0].signal}")
                    
#                     # แสดง success message
#                     self.show_non_blocking_message(
#                         "SIM Recovery Successful",
#                         f"✅ SIM recovery completed successfully!\n\nSIM Information:\n• Phone: {self.sims[0].phone}\n• Carrier: {self.sims[0].carrier}\n• Signal: {self.sims[0].signal}"
#                     )
#                 else:
#                     self.update_at_result_display(f"[MANUAL] ⚠️ Recovery completed but SIM data not fully available")
#                     self.show_non_blocking_message(
#                         "Recovery Partially Successful",
#                         "⚠️ SIM recovery completed but data is not fully available.\n\nPlease check:\n• SIM card connection\n• Try manual refresh"
#                     )
#             else:
#                 self.update_at_result_display("[MANUAL] ❌ No valid port available for refresh")
                
#         except Exception as e:
#             self.update_at_result_display(f"[MANUAL] ❌ Error during recovery finalization: {e}")
#             self.show_non_blocking_message(
#                 "Recovery Error",
#                 f"❌ Error during SIM recovery:\n\n{e}\n\nPlease try again or check the connection."
#             )

#     def setup_serial_monitor(self):
#         """ตั้งค่า Serial Monitor Thread - ปรับปรุงใหม่"""
#         if hasattr(self, 'serial_thread') and self.serial_thread:
#             self.serial_thread.stop()
        
#         port = self.port_combo.currentData()
#         baudrate = int(self.baud_combo.currentText())
        
#         if port and port != "Device not found":
#             self.serial_thread = SerialMonitorThread(port, baudrate)
#             self.serial_thread.new_sms_signal.connect(self.on_new_sms_signal)
#             self.serial_thread.at_response_signal.connect(self.update_at_result_display)
            
#             # เชื่อมต่อ signals ใหม่
#             self.serial_thread.sim_failure_detected.connect(self.on_sim_failure_detected)
#             self.serial_thread.cpin_ready_detected.connect(self.on_cpin_ready_detected)
#             self.serial_thread.sim_ready_signal.connect(self.on_sim_ready_auto)
#             self.serial_thread.cpin_status_signal.connect(self.on_cpin_status_received)
            
#             self.serial_thread.start()
            
#             # ไม่ต้องส่งคำสั่ง AT เพิ่มเติมที่นี่ เพราะ serial_service.py จะจัดการให้
#             self.update_at_result_display("[SETUP] Serial monitor started with SMS notification")

#             self._cmt_buffer = None
#             self._is_sending_sms = False
#             self.auto_open_sms_monitor()
    
#     def on_sim_failure_detected(self):
#         """จัดการเมื่อตรวจพบ SIM failure"""
#         self.sim_recovery_in_progress = True
#         self.update_at_result_display("[SIM FAILURE] 🚨 SIM failure detected! Auto-recovery starting...")
        
#         # แสดง notification
#         self.show_non_blocking_message(
#             "SIM Failure Detected",
#             "⚠️ SIM failure detected!\n\nSystem is performing automatic recovery...\n\nPlease wait for the process to complete."
#         )
        
#         # อัพเดทสถานะใน UI
#         if hasattr(self, 'status_label'):
#             self.status_label.setText("🔄 SIM Recovery in progress...")
        
#         # เริ่มนับเวลา recovery
#         self.start_recovery_timeout()

#     def start_recovery_timeout(self):
#         """เริ่มนับเวลา recovery timeout"""
#         # ตั้งเวลา timeout เป็น 30 วินาที
#         QTimer.singleShot(10000, self.on_recovery_timeout)

#     def on_recovery_timeout(self):
#         """จัดการเมื่อ recovery timeout"""
#         if self.sim_recovery_in_progress:
#             self.sim_recovery_in_progress = False
#             self.update_at_result_display("[SIM RECOVERY] ⏰ Recovery timeout reached")
            
#             # แสดง warning message
#             self.show_non_blocking_message(
#                 "SIM Recovery Timeout",
#                 "⚠️ SIM recovery process timed out!\n\nPlease check:\n• SIM card connection\n• Hardware issues\n• Manual modem restart may be needed"
#             )

#     def start_sms_monitor(self):
#         """เริ่ม SerialMonitorThread"""
#         if self.serial_thread and self.serial_thread.isRunning():
#             return

#         port = self.port_combo.currentData()
#         baud = int(self.baud_combo.currentText())
#         self.serial_thread = SerialMonitorThread(port, baud)
#         self.serial_thread.new_sms_signal.connect(self.on_new_sms_signal)
#         self.serial_thread.start()

#         # ─── Auto-reset CFUN เหมือนกันที่นี่ ถ้าเริ่ม Monitor ใหม่ ───
#         self.serial_thread.send_command("AT+CFUN=0")
#         QTimer.singleShot(200, lambda: self.serial_thread.send_command("AT+CFUN=1"))

#     def auto_open_sms_monitor(self):
#         """เปิด SMS Real-time Monitor อัตโนมัติ"""
#         if not getattr(self, 'auto_sms_monitor', True):
#             return
            
#         try:
#             port = self.port_combo.currentData()
#             baudrate = int(self.baud_combo.currentText())
            
#             if not port or port == "Device not found" or not self.serial_thread:
#                 return
            
#             if hasattr(self, 'sms_monitor_dialog') and self.sms_monitor_dialog and self.sms_monitor_dialog.isVisible():
#                 return
            
#             from widgets.sms_realtime_monitor import SmsRealtimeMonitor
#             self.sms_monitor_dialog = SmsRealtimeMonitor(port, baudrate, self, serial_thread=self.serial_thread)
            
#             self.sms_monitor_dialog.setModal(False)
#             self.sms_monitor_dialog.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
#                                                 Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            
#             self.sms_monitor_dialog.sms_received.connect(self.on_realtime_sms_received)
#             self.sms_monitor_dialog.log_updated.connect(self.on_sms_log_updated)
#             self.sms_monitor_dialog.finished.connect(self.on_sms_monitor_closed)
            
#             self.sms_monitor_dialog.show()
            
#             QTimer.singleShot(1500, self.auto_start_monitoring)
#             self.update_at_result_display("[AUTO] SMS Real-time Monitor opened automatically")
            
#         except Exception as e:
#             error_msg = f"[AUTO ERROR] Failed to open SMS Monitor: {e}"
#             self.update_at_result_display(error_msg)

#     def auto_start_monitoring(self):
#         """เริ่ม monitoring อัตโนมัติ"""
#         try:
#             if hasattr(self, 'sms_monitor_dialog') and self.sms_monitor_dialog and self.sms_monitor_dialog.isVisible():
#                 if hasattr(self.sms_monitor_dialog, 'start_monitoring'):
#                     self.sms_monitor_dialog.start_monitoring()
#                     self.update_at_result_display("[AUTO] SMS Real-time monitoring started automatically")
#         except Exception as e:
#             self.update_at_result_display(f"[AUTO ERROR] Failed to start monitoring: {e}")

#     # ==================== 5. SIM DATA MANAGEMENT ====================
#     def reload_sim(self):
#         """โหลดข้อมูลซิมใหม่"""
#         port = self.port_combo.currentData()
#         baudrate = int(self.baud_combo.currentText())
#         port_ok = bool(port and port != "Device not found")

#         if port_ok:
#             try:
#                 if self.serial_thread and self.serial_thread.isRunning():
#                     self.serial_thread.stop()
#                     self.serial_thread.wait()

#                 self.sims = load_sim_data(port, baudrate)

#                 for sim in self.sims:
#                     sig = self.query_signal_strength(port, baudrate)
#                     sim.signal = sig

#             except Exception as e:
#                 print(f"Error reloading SIM data: {e}")
#                 self.sims = []
#                 self.update_at_result_display(f"[ERROR] Failed to reload SIM data: {e}")
#         else:
#             self.sims = []

#         self.table.set_data(self.sims)
#         self.table.update_sms_button_enable(port_ok)

#         if port_ok:
#             self.setup_serial_monitor()

#     def add_test_button(self, layout):
#         """เพิ่มปุ่มทดสอบ (สำหรับ debug)"""
#         if hasattr(self, 'test_mode') and self.test_mode:
#             test_btn = QPushButton("Test Icons")
#             test_btn.setFixedWidth(100)
#             test_btn.clicked.connect(self.test_signal_icons)
#             layout.addWidget(test_btn)

#     # ==================== 6. AT COMMAND MANAGEMENT ====================
#     def load_at_command_history(self):
#         """โหลดประวัติคำสั่ง AT จากไฟล์"""
#         try:
#             with open("at_command_history.txt", encoding="utf-8") as f:
#                 commands = [line.strip() for line in f if line.strip()]
#                 for cmd in commands:
#                     if self.at_combo_main.findText(cmd) == -1:
#                         self.at_combo_main.addItem(cmd)
#         except FileNotFoundError:
#             self.save_at_command_history()
    
#     def save_at_command_history(self):
#         """บันทึกประวัติคำสั่ง AT ลงไฟล์"""
#         try:
#             commands = [self.at_combo_main.itemText(i) for i in range(self.at_combo_main.count())]
#             with open("at_command_history.txt", "w", encoding="utf-8") as f:
#                 for cmd in commands:
#                     f.write(cmd + "\n")
#         except Exception as e:
#             print(f"Unable to save AT command history: {e}")
    
#     def remove_at_command_main(self):
#         """ลบคำสั่ง AT ที่เลือกใน ComboBox"""
#         current_idx = self.at_combo_main.currentIndex()
#         current_text = self.at_combo_main.currentText().strip()
        
#         if current_idx >= 0 and self.at_combo_main.count() > 1:
#             reply = QMessageBox.question(
#                 self, 'Confirm deletion', 
#                 f'Do you want to delete the command "{current_text}" ?',
#                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No
#             )
            
#             if reply == QMessageBox.Yes:
#                 self.at_combo_main.removeItem(current_idx)
#                 self.save_at_command_history()
                
#                 if self.at_combo_main.count() > 0:
#                     new_text = self.at_combo_main.currentText()
#                     self.input_cmd_main.setPlainText(new_text)
#                 else:
#                     self.input_cmd_main.clear()
                
#                 QMessageBox.information(self, "Deletion successful", f"Delete command \"{current_text}\" finished!!")
#         else:
#             if self.at_combo_main.count() <= 1:
#                 QMessageBox.warning(self, "Notice", "The last command cannot be deleted")
#             else:
#                 QMessageBox.warning(self, "Notice", "Please select the command you want to delete")

#     def send_at_command_main(self):
#         """ส่งคำสั่ง AT จากหน้าหลัก"""
#         if not self.serial_thread:
#             QMessageBox.warning(self, "Notice", "No connection found with Serial")
#             return
        
#         cmd = self.input_cmd_main.toPlainText().strip()
#         if not cmd:
#             QMessageBox.warning(self, "Notice", "Please fill in the order AT")
#             return
        
#         # ตรวจจับคำสั่งพิเศษ
#         if cmd.upper() == "AT+RUN":
#             self.handle_at_run_command()
#             self.update_at_command_display(cmd)
#             return
#         elif cmd.upper() == "AT+STOP":
#             self.handle_at_stop_command()
#             self.update_at_command_display(cmd)
#             return
#         elif cmd.upper() == "AT+CLEAR":
#             self.handle_at_clear_command()
#             self.update_at_command_display(cmd)
#             return
        
#         self.clear_at_displays()
        
#         all_cmds = [self.at_combo_main.itemText(i) for i in range(self.at_combo_main.count())]
#         if cmd and cmd not in all_cmds:
#             self.at_combo_main.addItem(cmd)
#             self.save_at_command_history()
        
#         self.update_at_command_display(cmd)
#         self.serial_thread.send_command(cmd)

#     # ==================== 7. SMS FUNCTIONS ====================
#     def send_sms_main(self):
#         """ส่ง SMS จากหน้าหลัก พร้อม Loading Bar"""
#         if not self.serial_thread:
#             QMessageBox.warning(self, "Notice", "No connection found with Serial")
#             return

#         if not self.sims or not self.sims[0].imsi.isdigit():
#             self.show_loading_dialog()
#             QTimer.singleShot(100, lambda: self.loading_widget.complete_sending_error("ไม่มีซิมในระบบ"))
            
#             from services.sms_log import log_sms_sent
#             phone = self.input_phone_main.text().strip()
#             msg = self.input_sms_main.toPlainText().strip()
#             log_sms_sent(phone, msg, status="ล้มเหลว: ไม่มีซิมในระบบ")
#             return

#         phone_number = self.input_phone_main.text().strip()
#         if not phone_number:
#             QMessageBox.warning(self, "Notice", "Please enter the destination number")
#             return

#         message = self.input_sms_main.toPlainText().strip()
#         if not message:
#             QMessageBox.warning(self, "Notice", "Please fill in the message SMS")
#             return

#         self.show_loading_dialog()
#         self.start_sms_sending_process(phone_number, message)

#     def show_loading_dialog(self):
#         """แสดง Loading Dialog พร้อมสไตล์ใหม่"""
#         from PyQt5.QtWidgets import QDialog, QVBoxLayout
#         from styles import LoadingWidgetStyles

#         self.loading_dialog = QDialog(self)
#         self.loading_dialog.setWindowTitle("📱 ส่ง SMS")
#         self.loading_dialog.setFixedSize(450, 280)
#         self.loading_dialog.setModal(True)
#         self.loading_dialog.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
#         self.loading_dialog.setStyleSheet(LoadingWidgetStyles.get_dialog_style())

#         layout = QVBoxLayout()
#         self.loading_widget = LoadingWidget()
#         self.loading_widget.finished.connect(self.on_sms_sending_finished)
#         layout.addWidget(self.loading_widget)

#         self.loading_dialog.setLayout(layout)
#         self.loading_dialog.show()
#         self.loading_widget.start_sending()

#     def start_sms_sending_process(self, phone_number, message):
#         """เริ่มกระบวนการส่ง SMS"""
#         def encode_ucs2(text):
#             return text.encode('utf-16-be').hex().upper()

#         try:
#             phone_hex = encode_ucs2(phone_number)
#             msg_ucs2 = encode_ucs2(message)
#             self._is_sending_sms = True

#             self.send_at_command_with_progress('AT+CMGF=1', "เชื่อมต่อกับ Modem...")
#             time.sleep(0.2)
#             self.send_at_command_with_progress('AT+CSCS="UCS2"', "ตั้งค่า AT Commands...")
#             time.sleep(0.2)
#             self.send_at_command_with_progress('AT+CSMP=17,167,0,8', "เตรียมข้อความ...")
#             time.sleep(0.2)
#             self.send_at_command_with_progress(f'AT+CMGS="{phone_hex}"', "เข้ารหัสข้อมูล...")
#             time.sleep(0.5)

#             self.loading_widget.update_status("ส่งข้อความ SMS...")
#             self.serial_thread.send_raw(msg_ucs2.encode() + bytes([26]))
#             self.update_at_command_display(f"SMS Content: {message}")

#             self.save_sms_to_log(phone_number, message)
#             self.loading_widget.complete_sending_success()

#         except Exception as e:
#             error_msg = f"There was an error sending SMS: {e}"
#             self.update_at_result_display(error_msg)
#             QMessageBox.critical(self, "Error", error_msg)
#             self._is_sending_sms = False

#             from services.sms_log import log_sms_sent
#             log_sms_sent(phone_number, message, status=f"ล้มเหลว: {e}")

#             if hasattr(self, 'loading_widget'):
#                 self.loading_widget.complete_sending_error(error_msg)

#     def send_at_command_with_progress(self, command, status_text):
#         """ส่งคำสั่ง AT พร้อมอัพเดท loading status"""
#         if hasattr(self, 'loading_widget'):
#             self.loading_widget.update_status(status_text)
        
#         self.serial_thread.send_command(command)
#         self.update_at_command_display(command)

#     def save_sms_to_log(self, phone_number, message):
#         """บันทึก SMS ที่ส่งไปในรูปแบบ
#         "YY/MM/DD,HH:MM:SS+07",phone,message,Sent"""
#         try:
#             append_sms_log(
#                 "sms_sent_log.csv",
#                 phone_number,
#                 message,
#                 "Sent"
#             )
#             self.update_at_result_display("[Log Saved] SMS sent recorded.")
#         except Exception as e:
#             print(f"Error saving SMS log: {e}")
#             self.update_at_result_display(f"[Log Error] Failed to save: {e}")
    
#     def on_sms_sending_finished(self, success):
#         """เมื่อส่ง SMS เสร็จ"""
#         if success:
#             QTimer.singleShot(2000, self.close_loading_dialog)
#             self.input_phone_main.clear()
#             self.input_sms_main.clear()
#         else:
#             QTimer.singleShot(3000, self.close_loading_dialog)

#     def close_loading_dialog(self):
#         """ปิด Loading Dialog"""
#         if hasattr(self, 'loading_dialog') and self.loading_dialog:
#             self.loading_dialog.close()
#             self.loading_dialog = None
#             self.loading_widget = None

#     def show_inbox_sms_main(self):
#         """แสดง SMS เข้าจากหน้าหลัก"""
#         if not self.serial_thread:
#             QMessageBox.warning(self, "Notice", "No connection found with Serial")
#             return
        
#         self.clear_at_displays()
        
#         try:
#             cmd1 = 'AT+CMGF=1'
#             self.serial_thread.send_command(cmd1)
#             self.update_at_command_display(cmd1)
#             time.sleep(0.3)
            
#             cmd2 = 'AT+CMGL="ALL"'
#             self.serial_thread.send_command(cmd2)
#             self.update_at_command_display(cmd2)
            
#             self.update_at_result_display("=== Retrieving SMS from SIM Card ===")
#             self.update_at_result_display("Please wait for response...")
#             self.update_at_result_display("(SMS from SIM will appear in response above)")
            
#             time.sleep(1)
            
#             log_sms_lines = self.read_sms_from_log()
            
#             if log_sms_lines:
#                 self.update_at_result_display("\n=== SMS from Log File ===")
#                 for sms_line in log_sms_lines:
#                     self.update_at_result_display(sms_line)
#             else:
#                 self.update_at_result_display("\n=== SMS from Log File ===")
#                 self.update_at_result_display("(No SMS in log file)")

#         except Exception as e:
#             self.update_at_result_display(f"An error occurred: {e}")

#     def clear_all_sms_main(self):
#         """ลบ SMS ทั้งหมดจากหน้าหลัก"""
#         port = self.port_combo.currentData()
#         baudrate = int(self.baud_combo.currentText())
        
#         if not port or port == "Device not found":
#             QMessageBox.warning(self, "Notice", "Please select a port before use")
#             return
        
#         reply = QMessageBox.question(self, 'Confirm deletion', 
#                                    'Do you want to delete all SMS on your SIM card?',
#                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
#         if reply == QMessageBox.Yes:
#             try:
#                 ser = serial.Serial(port, baudrate, timeout=5)
                
#                 cmd1 = "AT+CMGF=1"
#                 ser.write(b'AT+CMGF=1\r')
#                 self.update_at_command_display(cmd1)
#                 time.sleep(0.1)
                
#                 cmd2 = "AT+CMGD=1,4"
#                 ser.write(b'AT+CMGD=1,4\r')
#                 self.update_at_command_display(cmd2)
#                 time.sleep(0.5)
                
#                 resp = ser.read(200).decode(errors="ignore")
#                 result = f"[CLEAR SMS] {resp if resp else '(All SMS have been deleted)'}"
#                 self.update_at_result_display(result)
#                 ser.close()
                
#                 QMessageBox.information(self, "Success", "All SMS have been deleted")
                
#             except Exception as e:
#                 error_msg = f"An error occurred: {e}"
#                 self.update_at_result_display(error_msg)
#                 QMessageBox.critical(self, "Error", error_msg)

#     def open_sms_history(self):
#         """เปิดประวัติ SMS"""
#         from widgets.sms_log_dialog import SmsLogDialog
#         dlg = SmsLogDialog(self)
#         dlg.send_sms_requested.connect(self.prefill_sms_to_send)
#         dlg.exec_()

#     def prefill_sms_to_send(self, phone, message):
#         """เติมข้อมูลเบอร์และข้อความลงในช่องส่ง SMS"""
#         self.input_phone_main.setText(phone)
#         self.input_sms_main.setPlainText(message)
#         self.input_sms_main.setFocus()
#         self.activateWindow()

#     # ==================== 8. SMS LOG MANAGEMENT ====================
#     def save_sms_to_inbox_log_new_format(self, sender, message, datetime_str):
#         """บันทึก SMS ที่เข้ามาในรูปแบบ
#         "YY/MM/DD,HH:MM:SS+07",phone,message,รับเข้า (real-time)"""
#         try:
#             append_sms_log(
#                 "sms_inbox_log.csv",
#                 sender,
#                 message,
#                 "รับเข้า (real-time)"
#             )
#             self.update_at_result_display(f"[Log Saved] SMS from {sender} recorded.")
#         except Exception as e:
#             self.update_at_result_display(f"[Log Error] Failed to save SMS: {e}")
    
#     def sms_inbox_exists_new_format(self, sender, message, datetime_str, log_file='log/sms_inbox_log.csv'):
#         """ตรวจสอบว่า SMS นี้มีใน log แล้วหรือไม่"""
#         if not os.path.isfile(log_file):
#             return False
            
#         try:
#             with open(log_file, newline='', encoding='utf-8') as f:
#                 content = f.read().strip()
#                 if not content:
#                     return False
                    
#                 f.seek(0)
#                 reader = csv.reader(f)
                
#                 first_row = next(reader, None)
#                 if first_row and first_row[0] == 'Received_Time':
#                     pass
#                 else:
#                     if first_row and len(first_row) >= 3:
#                         if first_row[1] == sender and first_row[2] == message:
#                             return True
                
#                 for row in reader:
#                     if len(row) >= 3 and row[1] == sender and row[2] == message:
#                         return True
                        
#         except Exception as e:
#             print(f"Error checking SMS existence: {e}")
        
#         return False

#     def read_sms_from_log(self):
#         """อ่าน SMS จาก log file - ใช้ sms_log module"""
#         try:
#             from services.sms_log import get_log_file_path
#             log_file = get_log_file_path('sms_inbox_log.csv')
            
#             log_lines = []
            
#             if not os.path.isfile(log_file):
#                 return log_lines
            
#             try:
#                 with open(log_file, newline='', encoding='utf-8') as f:
#                     content = f.read().strip()
#                     if not content:
#                         return log_lines
                        
#                     f.seek(0)
#                     reader = csv.reader(f)
                    
#                     first_row = next(reader, None)
#                     if first_row and (first_row[0] == 'Received_Time' or first_row[0] == 'Datetime'):
#                         pass
#                     else:
#                         if first_row and len(first_row) >= 3:
#                             if len(first_row) >= 4 and ('real-time' in first_row[3] or 'รับเข้า' in first_row[3]):
#                                 datetime_str, sender, message = first_row[0], first_row[1], first_row[2]
#                                 datetime_str = datetime_str.strip('"')
#                                 line_result = f"[LOG] {datetime_str} | {sender}: {message}"
#                             else:
#                                 timestamp, sender, message = first_row[0], first_row[1], first_row[2]
#                                 received_time = first_row[4] if len(first_row) > 4 else timestamp
#                                 line_result = f"[LOG] {received_time} | {sender}: {message}"
#                             log_lines.append(line_result)
                    
#                     for row in reader:
#                         if len(row) >= 3:
#                             if len(row) >= 4 and ('real-time' in row[3] or 'รับเข้า' in row[3]):
#                                 datetime_str, sender, message = row[0], row[1], row[2]
#                                 datetime_str = datetime_str.strip('"')
#                                 line_result = f"[LOG] {datetime_str} | {sender}: {message}"
#                             else:
#                                 timestamp, sender, message = row[0], row[1], row[2]
#                                 received_time = row[4] if len(row) > 4 else timestamp
#                                 line_result = f"[LOG] {received_time} | {sender}: {message}"
#                             log_lines.append(line_result)
                            
#             except Exception as e:
#                 print(f"Error reading SMS log: {e}")
            
#             return log_lines
            
#         except Exception as e:
#             self.update_at_result_display(f"[LOG ERROR] Error reading log: {e}")
#             return []

#     # ==================== 9. DISPLAY MANAGEMENT ====================
#     def update_at_command_display(self, command):
#         """อัพเดทการแสดงคำสั่ง AT"""
#         current_text = self.at_command_display.toPlainText()
#         if current_text:
#             self.at_command_display.setPlainText(current_text + "\n" + command)
#         else:
#             self.at_command_display.setPlainText(command)
        
#         cursor = self.at_command_display.textCursor()
#         cursor.movePosition(cursor.End)
#         self.at_command_display.setTextCursor(cursor)
    
#     def update_at_result_display(self, result):
#         """อัพเดทการแสดงผลลัพธ์ AT พร้อมการรีเฟรชอัตโนมัติ"""
#         current_text = self.at_result_display.toPlainText()
#         if current_text:
#             self.at_result_display.setPlainText(current_text + "\n" + result)
#         else:
#             self.at_result_display.setPlainText(result)
        
#         cursor = self.at_result_display.textCursor()
#         cursor.movePosition(cursor.End)
#         self.at_result_display.setTextCursor(cursor)
        
#         # ตรวจสอบว่า recovery สำเร็จหรือไม่
#         if self.sim_recovery_in_progress and "[SIM RECOVERY]" in result:
#             if "✅ SIM recovery successful!" in result or "Recovery successful!" in result:
#                 self.sim_recovery_in_progress = False
#                 self.update_at_result_display("[SIM RECOVERY] Auto-refreshing SIM data...")
                
#                 # รีเฟรช SIM data หลังจาก recovery สำเร็จ
#                 QTimer.singleShot(1000, self.auto_refresh_after_recovery)
                
#                 self.show_non_blocking_message(
#                     "SIM Recovery Successful",
#                     "✅ SIM recovery completed successfully!\n\nSIM data will be refreshed automatically."
#                 )
                
#             elif "❌ SIM recovery failed" in result or "Recovery failed" in result:
#                 self.sim_recovery_in_progress = False
#                 self.show_non_blocking_message(
#                     "SIM Recovery Failed",
#                     "❌ SIM recovery failed!\n\nPlease check:\n• SIM card connection\n• Hardware issues\n• Manual intervention may be needed"
#                 )
    
#     # เพิ่มฟังก์ชันใหม่สำหรับการรีเฟรชอัตโนมัติ
#     def auto_refresh_after_recovery(self):
#         """รีเฟรช SIM data อัตโนมัติหลังจาก recovery สำเร็จ"""
#         try:
#             self.update_at_result_display("[AUTO REFRESH] Refreshing SIM data after recovery...")
            
#             # รีเฟรช SIM data
#             port = self.port_combo.currentData()
#             baudrate = int(self.baud_combo.currentText())
            
#             if port and port != "Device not found":
#                 # โหลดข้อมูล SIM ใหม่
#                 self.sims = load_sim_data(port, baudrate)
                
#                 # อัพเดท signal strength
#                 for sim in self.sims:
#                     sig = self.query_signal_strength(port, baudrate)
#                     sim.signal = sig
                
#                 # อัพเดทตาราง
#                 self.table.set_data(self.sims)
                
#                 # แสดงผลลัพธ์
#                 if self.sims and self.sims[0].imsi != "-":
#                     self.update_at_result_display(f"[AUTO REFRESH] ✅ SIM data refreshed successfully!")
#                     self.update_at_result_display(f"[AUTO REFRESH] Phone: {self.sims[0].phone}")
#                     self.update_at_result_display(f"[AUTO REFRESH] IMSI: {self.sims[0].imsi}")
#                     self.update_at_result_display(f"[AUTO REFRESH] Carrier: {self.sims[0].carrier}")
#                     self.update_at_result_display(f"[AUTO REFRESH] Signal: {self.sims[0].signal}")
#                 else:
#                     self.update_at_result_display(f"[AUTO REFRESH] ⚠️ SIM data not fully available yet")
#                     # ลองอีกครั้งหลัง 3 วินาที
#                     QTimer.singleShot(3000, self.retry_refresh_after_recovery)
#             else:
#                 self.update_at_result_display("[AUTO REFRESH] ❌ No valid port available")
                
#         except Exception as e:
#             self.update_at_result_display(f"[AUTO REFRESH] ❌ Error: {e}")
    
#     def retry_refresh_after_recovery(self):
#         """ลองรีเฟรชอีกครั้งหากครั้งแรกไม่สำเร็จ"""
#         try:
#             self.update_at_result_display("[AUTO REFRESH] Retrying SIM data refresh...")
            
#             port = self.port_combo.currentData()
#             baudrate = int(self.baud_combo.currentText())
            
#             if port and port != "Device not found":
#                 # โหลดข้อมูล SIM ใหม่
#                 self.sims = load_sim_data(port, baudrate)
                
#                 # อัพเดท signal strength
#                 for sim in self.sims:
#                     sig = self.query_signal_strength(port, baudrate)
#                     sim.signal = sig
                
#                 # อัพเดทตาราง
#                 self.table.set_data(self.sims)
                
#                 if self.sims and self.sims[0].imsi != "-":
#                     self.update_at_result_display(f"[AUTO REFRESH] ✅ SIM data refreshed on retry!")
#                     self.update_at_result_display(f"[AUTO REFRESH] Phone: {self.sims[0].phone}")
#                     self.update_at_result_display(f"[AUTO REFRESH] IMSI: {self.sims[0].imsi}")
#                     self.update_at_result_display(f"[AUTO REFRESH] Carrier: {self.sims[0].carrier}")
#                     self.update_at_result_display(f"[AUTO REFRESH] Signal: {self.sims[0].signal}")
#                 else:
#                     self.update_at_result_display(f"[AUTO REFRESH] ⚠️ SIM still not ready, please try manual refresh")
                    
#         except Exception as e:
#             self.update_at_result_display(f"[AUTO REFRESH RETRY] ❌ Error: {e}")

#     def clear_at_displays(self):
#         """ล้างการแสดง AT Command และผลลัพธ์"""
#         self.at_command_display.clear()
#         self.at_result_display.clear()

#     # ==================== 10. DIALOG MANAGEMENT ====================
#     def on_view_sms_log(self):
#         """เปิดหน้าต่างดูประวัติ SMS"""
#         from widgets.sms_log_dialog import SmsLogDialog
#         dlg = SmsLogDialog(parent=self)
#         dlg.send_sms_requested.connect(self.prefill_sms_to_send)
        
#         dlg.setModal(False)
#         dlg.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
#                         Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
#         dlg.show()
        
#         if not hasattr(self, 'open_dialogs'):
#             self.open_dialogs = []
#         self.open_dialogs.append(dlg)
#         dlg.finished.connect(lambda: self.cleanup_dialog(dlg))
    
#     def cleanup_dialog(self, dialog):
#         """ลบ dialog ออกจาก list เมื่อปิด"""
#         try:
#             if hasattr(self, 'open_dialogs') and dialog in self.open_dialogs:
#                 self.open_dialogs.remove(dialog)
#         except Exception as e:
#             print(f"Error cleaning up dialog: {e}")

#     def on_sms_monitor_closed(self):
#         """จัดการเมื่อ SMS Monitor ถูกปิด"""
#         try:
#             if hasattr(self, 'sms_monitor_dialog'):
#                 self.sms_monitor_dialog = None
#             self.update_at_result_display("[SMS MONITOR] Real-time SMS monitor closed")
#         except Exception as e:
#             print(f"Error handling SMS monitor close: {e}")

#     def open_realtime_monitor(self):
#         """เปิดหน้าต่าง SMS Real-time Monitor"""
#         port = self.port_combo.currentData()
#         baudrate = int(self.baud_combo.currentText())
        
#         if not port or port == "Device not found":
#             QMessageBox.warning(self, "Notice", "Please select a port before opening SMS monitor")
#             return
        
#         if not self.serial_thread:
#             QMessageBox.warning(self, "Notice", "No serial connection available")
#             return
        
#         if hasattr(self, 'sms_monitor_dialog') and self.sms_monitor_dialog and self.sms_monitor_dialog.isVisible():
#             self.sms_monitor_dialog.raise_()
#             self.sms_monitor_dialog.activateWindow()
#             return
        
#         from widgets.sms_realtime_monitor import SmsRealtimeMonitor
#         self.sms_monitor_dialog = SmsRealtimeMonitor(port, baudrate, self, serial_thread=self.serial_thread)
        
#         self.sms_monitor_dialog.setModal(False)
#         self.sms_monitor_dialog.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
#                                             Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        
#         self.sms_monitor_dialog.sms_received.connect(self.on_realtime_sms_received)
#         self.sms_monitor_dialog.log_updated.connect(self.on_sms_log_updated)
#         self.sms_monitor_dialog.show()
#         self.sms_monitor_dialog.finished.connect(self.on_sms_monitor_closed)
        
#         self.update_at_result_display("[SMS MONITOR] Real-time SMS monitor opened")

#     def show_sms_log_for_phone(self, phone):
#         """แสดงประวัติ SMS สำหรับเบอร์ที่ระบุ"""
#         dlg = SmsLogDialog(parent=self)
#         dlg.setModal(False)
#         dlg.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
#                         Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
#         dlg.show()
        
#         if not hasattr(self, 'open_dialogs'):
#             self.open_dialogs = []
#         self.open_dialogs.append(dlg)
#         dlg.finished.connect(lambda: self.cleanup_dialog(dlg))

#     # ==================== 11. SMS SIGNAL HANDLING ====================
#     def on_new_sms_signal(self, data_line):
#         """จัดการสัญญาณ SMS ใหม่ – decode UCS-2 และ fallback เป็น base16→base10"""
#         line = data_line.strip()
#         self.update_at_result_display(f"[SMS SIGNAL] {line}")

#         # กรณี CMTI (SMS เก็บในหน่วยความจำ)
#         if line.startswith("+CMTI:"):
#             self.update_at_result_display(f"[SMS NOTIFICATION] {line}")
#             return

#         # กรณีข้อมูล SMS ที่ process มาแล้วจาก serial_service
#         if "|" in line and not line.startswith("+"):
#             try:
#                 # แยก 3 ช่วง: sender_hex | message_hex | timestamp
#                 sender_hex, message_hex, timestamp = line.split("|", 2)
#                 # ตัดเครื่องหมาย " กับช่องว่างที่อาจมากับ hex string
#                 sender_hex  = sender_hex.strip().replace('"', '').replace(' ', '')
#                 message_hex = message_hex.strip().replace(' ', '')

#                 # 1) ลอง decode UCS-2 ก่อน
#                 decoded_sender = self.decode_ucs2(sender_hex)  # :contentReference[oaicite:0]{index=0}

#                 # 2) ถ้า decode คืนค่าเดิม (แปลงไม่สำเร็จ) ให้ fallback ไปแปลงฐาน16→10
#                 if decoded_sender == sender_hex or not decoded_sender.strip():
#                     try:
#                         sender = str(int(sender_hex, 16))
#                     except ValueError:
#                         sender = sender_hex
#                 else:
#                     sender = decoded_sender

#                 # 3) ตัด null-char ท้ายออก (ในกรณี UCS-2)
#                 sender = sender.split("\x00", 1)[0]

#                 # แปลงข้อความด้วย UCS-2 ปกติ
#                 raw_message = self.decode_ucs2(message_hex)
#                 message     = raw_message.split("\x00", 1)[0]

#                 # ตรวจสอบซ้ำ
#                 key = (timestamp, sender, message)
#                 if key in self._notified_sms:
#                     self.update_at_result_display("[SMS DUPLICATE] Skipping duplicate")
#                     return
#                 self._notified_sms.add(key)

#                 # แสดง notification
#                 self.show_non_blocking_message(
#                     "📱 New SMS Received!",
#                     f"📞 From: {sender}\n🕐 Time: {timestamp}\n💬 Message: {message}"
#                 )

#                 # แสดงใน real-time display
#                 self.update_at_result_display(f"[REAL-TIME SMS] {timestamp} | {sender}: {message}")

#                 # บันทึกลง log
#                 self.save_sms_to_inbox_log_new_format(sender, message, timestamp)

#             except Exception as e:
#                 self.update_at_result_display(f"[SMS PARSE ERROR] {e}")
#                 self.update_at_result_display(f"[SMS RAW DATA] {line}")
#             return

#         # backward compatibility สำหรับ +CMT แบบเก่า
#         if line.startswith("+CMT:"):
#             self._cmt_buffer = line
#             return

#         if self._cmt_buffer:
#             header = self._cmt_buffer
#             body   = line
#             self._cmt_buffer = None
#             try:
#                 self.process_legacy_cmt(header, body)
#             except Exception as e:
#                 self.update_at_result_display(f"[CMT ERROR] {e}")



#     def process_legacy_cmt(self, header, body):
#         """ประมวลผล CMT แบบเก่า (fallback)"""
#         try:
#             import re
            
#             # แยกข้อมูลจาก header
#             match = re.match(r'\+CMT: "([^"]*)","","([^"]+)"', header)
#             if not match:
#                 self.update_at_result_display(f"[CMT ERROR] Invalid format: {header}")
#                 return
            
#             sender_hex = match.group(1)
#             timestamp = match.group(2)
            
#             # แปลง UCS2
#             sender = self.decode_ucs2(sender_hex)
#             message = self.decode_ucs2(body)
            
#             # ตรวจสอบซ้ำ
#             key = (timestamp, sender, message)
#             if key in self._notified_sms:
#                 return
#             self._notified_sms.add(key)

#             # แสดง notification
#             self.show_non_blocking_message(
#                 "📱 New SMS Received!",
#                 f"📞 From: {sender}\n🕐 Time: {timestamp}\n💬 Message: {message}"
#             )

#             self.update_at_result_display(f"[LEGACY SMS] {timestamp} | {sender}: {message}")
#             self.save_sms_to_inbox_log_new_format(sender, message, timestamp)
            
#         except Exception as e:
#             self.update_at_result_display(f"[LEGACY CMT ERROR] {e}")

#     def on_realtime_sms_received(self, sender, message, datetime_str):
#         """จัดการเมื่อได้รับ SMS real-time"""
#         try:
#             key = (datetime_str, sender, message)
#             if key in self._notified_sms:
#                 return
#             self._notified_sms.add(key)
            
#             display_text = f"[REAL-TIME SMS] {datetime_str} | {sender}: {message}"
#             self.update_at_result_display(display_text)
            
#         except Exception as e:
#             print(f"Error handling real-time SMS: {e}")
    
#     def on_sms_log_updated(self):
#         """จัดการเมื่อ SMS log ได้รับการอัพเดท"""
#         try:
#             self.update_at_result_display("[LOG UPDATE] SMS inbox log has been updated")
#         except Exception as e:
#             print(f"Error handling log update: {e}")

#     def decode_ucs2(self, ucs2_string):
#         """แปลง UCS2 string เป็น text - ปรับปรุงการจัดการ"""
#         if not ucs2_string:
#             return ""
            
#         try:
#             # ลบช่องว่างและปรับความยาว
#             ucs2_string = ucs2_string.replace(" ", "").upper()
            
#             if len(ucs2_string) % 2 != 0:
#                 ucs2_string = ucs2_string.ljust((len(ucs2_string) + 3) // 4 * 4, '0')
            
#             # แปลงเป็น bytes และ decode
#             bytes_data = bytes.fromhex(ucs2_string)
            
#             # ลอง decode หลายวิธี
#             for encoding in ['utf-16-be', 'utf-16-le', 'utf-8']:
#                 try:
#                     return bytes_data.decode(encoding, errors='strict')
#                 except UnicodeDecodeError:
#                     continue
            
#             # fallback
#             return bytes_data.decode('utf-16-be', errors='replace')
            
#         except Exception as e:
#             self.update_at_result_display(f"[DECODE ERROR] {e}")
#             return ucs2_string

#     # ==================== 12. SPECIAL AT COMMAND HANDLERS ====================
#     def handle_at_run_command(self):
#         """จัดการคำสั่ง AT+RUN - เริ่ม SMS Monitoring"""
#         try:
#             self.update_at_result_display("[AT+RUN] Processing command...")
            
#             # ตรวจสอบว่า SIM recovery กำลังทำงานอยู่หรือไม่
#             if self.sim_recovery_in_progress:
#                 self.update_at_result_display("[AT+RUN] ⚠️ SIM recovery in progress, please wait...")
#                 return
            
#             if hasattr(self, 'sms_monitor_dialog') and self.sms_monitor_dialog and self.sms_monitor_dialog.isVisible():
#                 if hasattr(self.sms_monitor_dialog, 'start_monitoring'):
#                     self.sms_monitor_dialog.start_monitoring()
#                     self.update_at_result_display("[AT+RUN] SMS Real-time monitoring started")
#                     return
            
#             port = self.port_combo.currentData()
#             baudrate = int(self.baud_combo.currentText())
            
#             if not port or port == "Device not found" or not self.serial_thread:
#                 self.update_at_result_display("[AT+RUN ERROR] Please check port and connection")
#                 return
            
#             from widgets.sms_realtime_monitor import SmsRealtimeMonitor
#             self.sms_monitor_dialog = SmsRealtimeMonitor(port, baudrate, self, serial_thread=self.serial_thread)
            
#             self.sms_monitor_dialog.setModal(False)
#             self.sms_monitor_dialog.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
#                                                 Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            
#             self.sms_monitor_dialog.sms_received.connect(self.on_realtime_sms_received)
#             self.sms_monitor_dialog.log_updated.connect(self.on_sms_log_updated)
#             self.sms_monitor_dialog.finished.connect(self.on_sms_monitor_closed)
#             self.sms_monitor_dialog.show()
            
#             QTimer.singleShot(1000, self.start_monitoring_delayed)
#             self.update_at_result_display("[AT+RUN] SMS Monitor opened")
                    
#         except Exception as e:
#             self.update_at_result_display(f"[AT+RUN ERROR] {e}")
    
#     def add_sim_recovery_button(self):
#         """เพิ่มปุ่ม SIM Recovery (เรียกใน create_control_buttons)"""
#         self.btn_sim_recovery = QPushButton("SIM Recovery")
#         self.btn_sim_recovery.setFixedWidth(120)
#         self.btn_sim_recovery.clicked.connect(self.manual_sim_recovery)
#         self.btn_sim_recovery.setStyleSheet("""
#             QPushButton {
#                 background-color: #e74c3c;
#                 color: white;
#                 border: none;
#                 padding: 8px 16px;
#                 border-radius: 4px;
#                 font-weight: bold;
#             }
#             QPushButton:hover {
#                 background-color: #c0392b;
#             }
#             QPushButton:pressed {
#                 background-color: #a93226;
#             }
#             QPushButton:disabled {
#                 background-color: #bdc3c7;
#                 color: #7f8c8d;
#             }
#         """)
#         return self.btn_sim_recovery
    
#     def manual_sim_recovery(self):
#         """ทำ SIM recovery แบบ manual พร้อมตรวจสอบ CPIN"""
#         if not self.serial_thread:
#             QMessageBox.warning(self, "Notice", "No serial connection available")
#             return
        
#         if self.sim_recovery_in_progress:
#             QMessageBox.information(self, "Recovery in Progress", "SIM recovery is already in progress. Please wait...")
#             return
        
#         reply = QMessageBox.question(
#             self, 
#             'Manual SIM Recovery', 
#             'Do you want to perform manual SIM recovery?\n\nThis will:\n1. Reset the modem (AT+CFUN=0/1)\n2. Check SIM status (AT+CPIN?)\n3. Auto-refresh SIM data if ready\n\nProceed?',
#             QMessageBox.Yes | QMessageBox.No, 
#             QMessageBox.No
#         )
        
#         if reply == QMessageBox.Yes:
#             self.sim_recovery_in_progress = True
#             self.update_at_result_display("[MANUAL] Starting enhanced SIM recovery...")
            
#             # เริ่ม recovery ผ่าน serial thread
#             if hasattr(self.serial_thread, 'force_sim_recovery'):
#                 self.serial_thread.force_sim_recovery()
#             else:
#                 # Fallback method
#                 self.start_manual_recovery_sequence()

#     def simulate_manual_recovery_success(self):
#         """จำลองการสำเร็จของ manual recovery"""
#         self.update_at_result_display("[MANUAL] Manual recovery completed")
#         self.update_at_result_display("[SIM RECOVERY] ✅ Recovery successful!")


#     def handle_at_stop_command(self):
#         """จัดการคำสั่ง AT+STOP - หยุด SMS Monitoring"""
#         try:
#             self.update_at_result_display("[AT+STOP] Processing command...")
            
#             if hasattr(self, 'sms_monitor_dialog') and self.sms_monitor_dialog and self.sms_monitor_dialog.isVisible():
#                 if hasattr(self.sms_monitor_dialog, 'stop_monitoring'):
#                     self.sms_monitor_dialog.stop_monitoring()
#                     self.update_at_result_display("[AT+STOP] SMS Real-time monitoring stopped")
#                 else:
#                     self.update_at_result_display("[AT+STOP ERROR] SMS Monitor not ready")
#             else:
#                 self.update_at_result_display("[AT+STOP] No SMS Monitor window open")
                    
#         except Exception as e:
#             self.update_at_result_display(f"[AT+STOP ERROR] {e}")
    
#     def handle_at_clear_command(self):
#         """จัดการคำสั่ง AT+CLEAR - เคลียร์ SMS Monitoring"""
#         try:
#             self.update_at_result_display("[AT+CLEAR] Processing command...")
            
#             if hasattr(self, 'sms_monitor_dialog') and self.sms_monitor_dialog and self.sms_monitor_dialog.isVisible():
#                 if hasattr(self.sms_monitor_dialog, 'clear_monitoring'):
#                     self.sms_monitor_dialog.clear_monitoring()
#                     self.update_at_result_display("[AT+CLEAR] SMS Real-time monitoring cleared")
#                 else:
#                     self.update_at_result_display("[AT+CLEAR ERROR] Clear method not found")
#             else:
#                 self.update_at_result_display("[AT+CLEAR] No SMS Monitor window open")
                    
#         except Exception as e:
#             self.update_at_result_display(f"[AT+CLEAR ERROR] {e}")

#     def start_monitoring_delayed(self):
#         """เริ่ม monitoring หลังจากรอให้ dialog เปิดเสร็จ"""
#         try:
#             if hasattr(self, 'sms_monitor_dialog') and self.sms_monitor_dialog and self.sms_monitor_dialog.isVisible():
#                 if hasattr(self.sms_monitor_dialog, 'start_monitoring'):
#                     self.sms_monitor_dialog.start_monitoring()
#                     self.update_at_result_display("[AT+RUN] Monitoring started successfully!")
#         except Exception as e:
#             self.update_at_result_display(f"[AT+RUN ERROR] Failed to start: {e}")

#     # ==================== 13. WINDOW EVENT HANDLERS ====================
#     def show_non_blocking_message(self, title, message):
#         """แสดง message box แบบ non-blocking"""
#         try:
#             msg_box = QMessageBox(self)
#             msg_box.setWindowTitle(title)
#             msg_box.setText(message)
#             msg_box.setIcon(QMessageBox.Information)
#             msg_box.setModal(False)
#             msg_box.setAttribute(Qt.WA_DeleteOnClose)
#             msg_box.show()
#         except Exception as e:
#             print(f"Error showing message: {e}")

#     def closeEvent(self, event):
#         """จัดการเมื่อปิดหน้าต่างหลัก"""
#         try:
#             self.save_settings()
            
#             if hasattr(self, 'serial_thread') and self.serial_thread:
#                 self.serial_thread.stop()
                
#             if hasattr(self, 'open_dialogs'):
#                 for dialog in self.open_dialogs[:]:
#                     if dialog and dialog.isVisible():
#                         dialog.close()
                        
#         except Exception as e:
#             print(f"Error during close: {e}")
        
#         event.accept()

#     def query_signal_strength(self, port, baudrate):
#         """ส่ง AT+CSQ แล้วคืนค่าเป็นข้อความพร้อม Unicode Signal Bars - ปรับปรุงการตรวจสอบ SIM"""
#         try:
#             ser = serial.Serial(port, baudrate, timeout=3)
#             time.sleep(0.1)
            
#             # ตรวจสอบสถานะ SIM ก่อนอ่านสัญญาณ
#             ser.write(b'AT+CPIN?\r\n')
#             time.sleep(0.3)
#             cpin_response = ser.read(200).decode(errors='ignore')
            
#             # ถ้า SIM ไม่พร้อมให้คืนค่า No Signal
#             if "CPIN: READY" not in cpin_response:
#                 ser.close()
#                 return '▁▁▁▁ No SIM'
            
#             # ตรวจสอบการลงทะเบียน Network
#             ser.write(b'AT+CREG?\r\n')
#             time.sleep(0.3)
#             creg_response = ser.read(200).decode(errors='ignore')
            
#             # ถ้าไม่ได้ลงทะเบียนเครือข่าย
#             if "+CREG: 0,1" not in creg_response and "+CREG: 0,5" not in creg_response:
#                 ser.close()
#                 return '▁▁▁▁ No Network'
            
#             # อ่านค่าสัญญาณ
#             ser.write(b'AT+CSQ\r\n')
#             time.sleep(0.2)
            
#             raw = ser.read(200).decode(errors='ignore')
#             ser.close()
            
#             m = re.search(r'\+CSQ:\s*(\d+),', raw)
#             if not m:
#                 return '▁▁▁▁ No Signal'
                
#             rssi = int(m.group(1))
            
#             if rssi == 99:
#                 return '▁▁▁▁ Unknown'
#             elif rssi == 0:
#                 return '▁▁▁▁ No Signal'
                
#             dbm = -113 + 2*rssi
            
#             # กำหนด Unicode Signal Bars ตามระดับสัญญาณ
#             if dbm >= -70:
#                 return f'▁▃▅█ {dbm} dBm (Excellent)'      # 4 bars - แรงมาก
#             elif dbm >= -85:
#                 return f'▁▃▅▇ {dbm} dBm (Good)'          # 3 bars - ดี
#             elif dbm >= -100:
#                 return f'▁▃▁▁ {dbm} dBm (Fair)'          # 2 bars - ปานกลาง
#             elif dbm >= -110:
#                 return f'▁▁▁▁ {dbm} dBm (Poor)'          # 1 bar - อ่อน
#             else:
#                 return f'▁▁▁▁ {dbm} dBm (Very Poor)'     # No bars - ไม่มีสัญญาณ
                
#         except Exception as e:
#             return '▁▁▁▁ Error'


# # ==================== MAIN EXECUTION ====================
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = SimInfoWindow()
#     window.show()
#     sys.exit(app.exec_())