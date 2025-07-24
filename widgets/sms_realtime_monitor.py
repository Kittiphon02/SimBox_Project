# sms_realtime_monitor.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, 
    QGroupBox, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
import serial
import time
import re
import os
import csv
from datetime import datetime
from services.sms_log import log_sms_inbox

# ==================== IMPORT NEW STYLES ====================
from styles import SmsRealtimeMonitorStyles


# ==================== UTILITY FUNCTIONS ====================
def decode_ucs2(hex_str):
    """แปลง UCS2 hex string เป็น text - รองรับภาษาไทย"""
    if not hex_str:
        return ""
        
    hex_str = hex_str.replace(" ", "")
    
    try:
        # ลองแปลงแบบ UCS2 (UTF-16 BE) ก่อน
        byte_data = bytes.fromhex(hex_str)
        decoded_text = byte_data.decode("utf-16-be")
        return decoded_text
        
    except ValueError as e:
        # ถ้า hex string ไม่ถูกต้อง
        try:
            # ลองแปลงแบบ UTF-8
            byte_data = bytes.fromhex(hex_str)
            decoded_text = byte_data.decode("utf-8", errors='replace')
            return decoded_text
        except Exception:
            return hex_str  # คืนค่า hex string เดิมถ้าแปลงไม่ได้
            
    except UnicodeDecodeError as e:
        # ถ้าแปลง Unicode ไม่ได้
        try:
            # ลองใช้ errors='replace' เพื่อแทนที่ตัวอักษรที่แปลงไม่ได้
            byte_data = bytes.fromhex(hex_str)
            decoded_text = byte_data.decode("utf-16-be", errors='replace')
            return decoded_text
        except Exception:
            return hex_str
            
    except Exception as e:
        # กรณีอื่นๆ
        print(f"Error decoding UCS2: {e}")
        return hex_str


# ==================== MAIN CLASS ====================
class SmsRealtimeMonitor(QDialog):
    # Signals เพื่อส่งข้อมูลกลับไปยังหน้าหลัก
    sms_received = pyqtSignal(str, str, str)  # sender, message, datetime
    log_updated = pyqtSignal()  # แจ้งเตือนว่า log ได้รับการอัพเดท
    
    def __init__(self, port, baudrate, parent=None, serial_thread=None):
        super().__init__(parent)
        
        # ==================== 1. INITIALIZATION ====================
        self.port = port
        self.baudrate = baudrate
        self.serial_thread = serial_thread
        self._cmt_buffer = None
        self.monitoring = False
        
        # Initialize counters
        self.received_count = 0
        self.saved_count = 0
        self.error_count = 0
        
        # Setup UI and connections
        self.setup_ui()
        self.setup_connections()
        self.apply_styles()  # ใช้สไตล์ใหม่
        
        # เชื่อมต่อกับ serial thread ถ้ามี
        if self.serial_thread:
            self.serial_thread.at_response_signal.connect(self.handle_incoming_data)

    # ==================== 2. UI SETUP ====================
    def setup_ui(self):
        """สร้าง UI components"""
        self.setWindowTitle("SMS Real-time Monitor")
        self.resize(700, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
                           Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("SMS Real-time Inbox Monitor")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Connection info
        conn_info = QLabel(f"Port: {self.port}   Baudrate: {self.baudrate}")
        conn_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(conn_info)
        
        # Control buttons
        self.create_control_section(layout)
        
        # Monitor display
        self.create_monitor_section(layout)
        
        # Stats section
        self.create_stats_section(layout)
        
        # จัดเก็บ reference สำหรับ styling
        self.header = header
        self.conn_info = conn_info
        
        self.setLayout(layout)
    
    def create_control_section(self, layout):
        """สร้างส่วนควบคุม"""
        control_group = QGroupBox("Monitor Controls")
        control_layout = QHBoxLayout()
        
        # Start monitoring button
        self.btn_start = QPushButton("Start Monitoring")
        
        # Stop monitoring button
        self.btn_stop = QPushButton("Stop Monitoring")
        self.btn_stop.setEnabled(False)
        
        # Clear log button
        self.btn_clear = QPushButton("Clear Display")
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addWidget(self.btn_clear)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # จัดเก็บ reference สำหรับ styling
        self.control_group = control_group
    
    def create_monitor_section(self, layout):
        """สร้างส่วนแสดงผล monitor"""
        monitor_group = QGroupBox("Real-time SMS Monitor")
        monitor_layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Status: Ready to monitor")
        monitor_layout.addWidget(self.status_label)
        
        # Monitor display
        self.monitor_display = QTextEdit()
        self.monitor_display.setReadOnly(True)
        self.monitor_display.setPlaceholderText("Waiting for incoming SMS...")
        monitor_layout.addWidget(self.monitor_display)
        
        monitor_group.setLayout(monitor_layout)
        layout.addWidget(monitor_group)
        
        # จัดเก็บ reference สำหรับ styling
        self.monitor_group = monitor_group
    
    def create_stats_section(self, layout):
        """สร้างส่วนแสดงสถิติ"""
        stats_layout = QHBoxLayout()
        
        self.stats_received = QLabel("Received: 0")
        self.stats_saved = QLabel("Saved to CSV: 0")
        self.stats_errors = QLabel("Errors: 0")
        
        stats_layout.addWidget(self.stats_received)
        stats_layout.addWidget(self.stats_saved)
        stats_layout.addWidget(self.stats_errors)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
    
    def setup_connections(self):
        """เชื่อมต่อ signals และ slots"""
        self.btn_start.clicked.connect(self.start_monitoring)
        self.btn_stop.clicked.connect(self.stop_monitoring)
        self.btn_clear.clicked.connect(self.clear_display)

    def apply_styles(self):
        """ใช้สไตล์ใหม่โทนสีแดงทางการ"""
        # Dialog main style
        self.setStyleSheet(SmsRealtimeMonitorStyles.get_dialog_style())
        
        # Header styles
        self.header.setStyleSheet(SmsRealtimeMonitorStyles.get_header_style())
        self.conn_info.setStyleSheet(SmsRealtimeMonitorStyles.get_connection_info_style())
        
        # Group styles
        self.control_group.setStyleSheet(SmsRealtimeMonitorStyles.get_control_group_style())
        self.monitor_group.setStyleSheet(SmsRealtimeMonitorStyles.get_monitor_group_style())
        
        # Button styles
        self.btn_start.setStyleSheet(SmsRealtimeMonitorStyles.get_start_button_style())
        self.btn_stop.setStyleSheet(SmsRealtimeMonitorStyles.get_stop_button_style())
        self.btn_clear.setStyleSheet(SmsRealtimeMonitorStyles.get_clear_button_style())
        
        # Status label (default ready)
        self.status_label.setStyleSheet(SmsRealtimeMonitorStyles.get_status_ready_style())
        
        # Monitor display
        self.monitor_display.setStyleSheet(SmsRealtimeMonitorStyles.get_monitor_display_style())
        
        # Stats labels
        self.stats_received.setStyleSheet(SmsRealtimeMonitorStyles.get_stats_received_style())
        self.stats_saved.setStyleSheet(SmsRealtimeMonitorStyles.get_stats_saved_style())
        self.stats_errors.setStyleSheet(SmsRealtimeMonitorStyles.get_stats_errors_style())

    # ==================== 3. MONITORING CONTROL ====================
    def start_monitoring(self):
        """เริ่มการ monitor"""
        if not self.serial_thread:
            self.show_error("No serial connection available")
            return
        
        self.monitoring = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("Status: Monitoring active")
        
        # ใช้สไตล์ active
        self.status_label.setStyleSheet(SmsRealtimeMonitorStyles.get_status_active_style())
        
        self.append_to_display("[MONITOR] Started SMS real-time monitoring")
        self.append_to_display("[INFO] Waiting for incoming SMS messages...")
    
    def stop_monitoring(self):
        """หยุดการ monitor"""
        self.monitoring = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Status: Monitoring stopped")
        
        # ใช้สไตล์ stopped
        self.status_label.setStyleSheet(SmsRealtimeMonitorStyles.get_status_stopped_style())
        
        self.append_to_display("[MONITOR] Stopped SMS real-time monitoring")
    
    def clear_display(self):
        """ล้างการแสดงผล"""
        self.monitor_display.clear()
        self.append_to_display("[SYSTEM] Display cleared")
    
    def clear_monitoring(self):
        """เคลียร์การ monitoring (สำหรับ AT+CLEAR command)"""
        self.clear_display()
        # รีเซ็ตสถิติ
        self.received_count = 0
        self.saved_count = 0
        self.error_count = 0
        self.update_stats()
        self.append_to_display("[SYSTEM] Monitoring data cleared")

    # ==================== 4. DATA HANDLING ====================
    def handle_incoming_data(self, data_line):
        """จัดการข้อมูลที่เข้ามา"""
        if not self.monitoring:
            return
        
        data = data_line.strip()
        
        # ตรวจจับ CMT header
        if data.startswith("+CMT:"):
            self._cmt_buffer = data
            self.append_to_display(f"[CMT HEADER] {data}")
            return
            
        # ตรวจจับข้อความ SMS ที่ติดตาม CMT header
        elif self._cmt_buffer:
            header = self._cmt_buffer
            message_hex = data
            self._cmt_buffer = None
            
            try:
                self.process_cmt_message(header, message_hex)
            except Exception as e:
                self.error_count += 1
                self.update_stats()
                error_msg = f"[ERROR] Failed to process CMT: {e}"
                self.append_to_display(error_msg)
    
    def process_cmt_message(self, header, message_hex):
        """ประมวลผลข้อความ CMT - รองรับภาษาไทย"""
        try:
            # แยกข้อมูลจาก header
            match = re.match(r'\+CMT: "([^"]*)","","([^"]+)"', header)
            if not match:
                raise ValueError("Invalid CMT header format")
            
            sender_ucs2 = match.group(1)
            datetime_str = match.group(2)
            
            # แปลงข้อมูล
            sender = decode_ucs2(sender_ucs2)
            message = decode_ucs2(message_hex)
            
            self.received_count += 1
            
            # แสดงผลใน monitor
            self.append_to_display(f"[NEW SMS] {datetime_str}")
            self.append_to_display(f"  From: {sender}")
            self.append_to_display(f"  Message: {message}")
            self.append_to_display(f"  Raw Hex: {message_hex}")
            
            # ตรวจสอบว่าเป็นภาษาไทยหรือไม่
            if any('\u0e00' <= char <= '\u0e7f' for char in message):
                self.append_to_display(f"  [THAI] Thai language detected")
            
            self.append_to_display("-" * 50)
            
            # บันทึกลง CSV
            if self.save_to_csv(sender, message, datetime_str):
                self.saved_count += 1
                self.append_to_display(f"[LOG] Saved to CSV successfully")
            
            # ส่ง signal ไปยังหน้าหลัก
            self.sms_received.emit(sender, message, datetime_str)
            self.log_updated.emit()
            
            self.update_stats()
            
        except Exception as e:
            self.error_count += 1
            self.update_stats()
            error_msg = f"[ERROR] Processing SMS: {e}"
            self.append_to_display(error_msg)
            raise

    # ==================== 5. CSV LOGGING ====================
    def save_to_csv(self, sender, message, datetime_str):
        """บันทึก SMS ลง CSV file - ใช้ sms_log module ที่ปรับปรุงแล้ว"""
        try:
            from services.sms_log import log_sms_inbox
            success = log_sms_inbox(sender, message, status='รับเข้า (real-time)')
            
            if success:
                self.append_to_display(f"[LOG] SMS saved to network share successfully")
            else:
                self.append_to_display(f"[LOG] SMS saved to local backup only")
            
            return True
                
        except Exception as e:
            error_msg = f"[ERROR] Saving to CSV: {e}"
            self.append_to_display(error_msg)
            return False

    def save_csv_fallback(self, sender, message, datetime_str, log_file):
        """บันทึกแบบ fallback สำหรับกรณีที่มีปัญหา encoding"""
        try:
            # ใช้ encoding ที่แข็งแกร่งกว่า
            with open(log_file, 'a', newline='', encoding='utf-8', errors='replace') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                
                # เตรียมข้อมูลสำหรับบันทึก
                quoted_datetime = f'"{datetime_str}"'
                formatted_phone = sender if sender.startswith('+') else f'+{sender}'
                
                # แปลงข้อความให้ปลอดภัย
                safe_message = message.encode('utf-8', errors='replace').decode('utf-8') if message else ""
                
                writer.writerow([quoted_datetime, formatted_phone, safe_message, 'รับเข้า (real-time)'])
                
                self.append_to_display(f"[LOG] SMS saved using fallback method in new format")
                
        except Exception as e:
            self.append_to_display(f"[ERROR] Fallback save failed: {e}")
            raise

    def sms_exists_in_log(self, sender, message, log_file='sms_inbox_log.csv'):
        """ตรวจสอบว่า SMS มีใน log แล้วหรือไม่ - รองรับภาษาไทย"""
        if not os.path.isfile(log_file):
            return False
        
        try:
            with open(log_file, newline='', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)  # ข้าม header
                for row in reader:
                    if len(row) >= 3 and str(row[1]) == str(sender) and str(row[2]) == str(message):
                        return True
        except UnicodeDecodeError:
            # ลองอ่านด้วย encoding อื่น
            try:
                with open(log_file, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    for row in reader:
                        if len(row) >= 3 and str(row[1]) == str(sender) and str(row[2]) == str(message):
                            return True
            except Exception:
                pass
        except Exception:
            pass
        
        return False

    # ==================== 6. DISPLAY & UI UPDATES ====================
    def append_to_display(self, text):
        """เพิ่มข้อความลงใน display"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.monitor_display.append(f"[{timestamp}] {text}")
        
        # เลื่อนไปที่ข้อความล่าสุด
        cursor = self.monitor_display.textCursor()
        cursor.movePosition(cursor.End)
        self.monitor_display.setTextCursor(cursor)
    
    def update_stats(self):
        """อัพเดทสถิติ"""
        self.stats_received.setText(f"Received: {self.received_count}")
        self.stats_saved.setText(f"Saved to CSV: {self.saved_count}")
        self.stats_errors.setText(f"Errors: {self.error_count}")
    
    def show_error(self, message):
        """แสดง error message"""
        QMessageBox.warning(self, "Error", message)
        self.append_to_display(f"[ERROR] {message}")
        
        # ใช้สไตล์ error
        self.status_label.setText("Status: Error occurred")
        self.status_label.setStyleSheet(SmsRealtimeMonitorStyles.get_status_error_style())

    # ==================== 7. TESTING & DEBUG ====================
    def test_thai_sms(self):
        """ทดสอบการบันทึก SMS ภาษาไทย"""
        try:
            test_sender = "+66653988461"
            test_message = "สวัสดี"
            test_datetime = "25/07/09,09:10:13+28"
            
            self.append_to_display("[TEST] Testing Thai SMS saving...")
            
            if self.save_to_csv(test_sender, test_message, test_datetime):
                self.append_to_display("[TEST] Thai SMS saved successfully!")
            else:
                self.append_to_display("[TEST] Failed to save Thai SMS")
                
        except Exception as e:
            self.append_to_display(f"[TEST ERROR] {e}")

    # ==================== 8. WINDOW EVENT HANDLERS ====================
    def closeEvent(self, event):
        """จัดการเมื่อปิดหน้าต่าง"""
        if self.monitoring:
            self.stop_monitoring()
        event.accept()