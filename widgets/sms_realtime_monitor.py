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
from core.utility_functions import decode_ucs2_to_text as decode_ucs2

# ==================== IMPORT NEW STYLES ====================
from styles import SmsRealtimeMonitorStyles


# ==================== UTILITY FUNCTIONS ====================
def decode_ucs2(hex_str):
    """แปลง UCS2 hex string เป็น text - Fixed spacing issues"""
    if not hex_str:
        return ""
        
    hex_str = hex_str.replace(" ", "").upper()
    
    try:
        # ลองแปลงแบบ UCS2 (UTF-16 BE) ก่อน
        byte_data = bytes.fromhex(hex_str)
        
        for encoding in ['utf-16-be', 'utf-16-le']:
            try:
                decoded_text = byte_data.decode(encoding)
                
                # ✅ แก้ไขการจัดการตัวอักษรพิเศษ
                cleaned_text = ""
                for char in decoded_text:
                    char_code = ord(char)
                    if char_code == 0:  # null character
                        continue
                    elif char_code < 32 and char_code not in [9, 10, 13]:  # control characters
                        cleaned_text += " "  # แทนที่ด้วยช่องว่าง
                    else:
                        cleaned_text += char
                
                # ลบช่องว่างซ้ำๆ
                import re
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                
                if cleaned_text:
                    return cleaned_text
                    
            except UnicodeDecodeError:
                continue
                
    except ValueError:
        # ถ้า hex string ไม่ถูกต้อง ลอง UTF-8
        try:
            byte_data = bytes.fromhex(hex_str)
            decoded_text = byte_data.decode("utf-8", errors='replace')
            return decoded_text.replace('\x00', '').strip()
        except Exception:
            return hex_str
            
    except Exception as e:
        print(f"Error decoding UCS2: {e}")
        return hex_str
    
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
        """ประมวลผลข้อความ CMT - Enhanced decoding"""
        try:
            # แยกข้อมูลจาก header
            match = re.match(r'\+CMT: "([^"]*)","","([^"]+)"', header)
            if not match:
                raise ValueError("Invalid CMT header format")
            
            sender_ucs2 = match.group(1)
            datetime_str = match.group(2)
            
            print(f"🔍 DEBUG CMT: Original datetime = '{datetime_str}'")
            print(f"🔍 DEBUG CMT: Sender UCS2 = '{sender_ucs2}'")
            print(f"🔍 DEBUG CMT: Message hex = '{message_hex[:50]}{'...' if len(message_hex) > 50 else ''}'")
            
            # แปลง sender - ลองหลายวิธี
            sender = self._decode_sender_safely(sender_ucs2)
            
            # แปลงข้อความ - Enhanced decoding
            message = self._decode_message_safely(message_hex)
            
            # ✅ บังคับใช้วันที่ปัจจุบันแทน
            now = datetime.now()
            current_date = now.strftime("%d/%m/%Y")  # 31/07/2025
            
            # แยกเฉพาะเวลาจาก datetime_str เดิม
            if "," in datetime_str:
                _, time_part = datetime_str.split(",", 1)
                if "+" in time_part:
                    time_only = time_part.split("+", 1)[0]
                else:
                    time_only = time_part
            else:
                time_only = now.strftime("%H:%M:%S")  # ใช้เวลาปัจจุบัน
            
            # สร้าง datetime_str ใหม่ด้วยวันที่ปัจจุบัน
            corrected_datetime = f"{current_date},{time_only}+07"
            
            print(f"✅ DEBUG CMT: Decoded sender = '{sender}'")
            print(f"✅ DEBUG CMT: Decoded message = '{message}'")
            print(f"✅ DEBUG CMT: Corrected datetime = '{corrected_datetime}'")
            
            self.received_count += 1
            
            # แสดงผลใน monitor
            self.append_to_display(f"[NEW SMS] {corrected_datetime}")
            self.append_to_display(f"  From: {sender}")
            self.append_to_display(f"  Message: {message}")
            
            # ตรวจสอบว่าเป็นภาษาไทยหรือไม่
            if any('\u0e00' <= char <= '\u0e7f' for char in message):
                self.append_to_display(f"  [THAI] Thai language detected")
            
            # ตรวจสอบว่าเป็นภาษาอังกฤษและมีปัญหาการแสดงผลหรือไม่
            if message.isupper() and ' ' not in message and len(message) > 10:
                self.append_to_display(f"  [WARNING] Message may have decode issues")
            
            self.append_to_display("-" * 50)
            
            # บันทึกลง CSV ด้วยวันที่ปัจจุบัน
            if self.save_to_csv(sender, message, corrected_datetime):
                self.saved_count += 1
                self.log_updated.emit()
            
            # ส่ง signal ไปยังหน้าหลัก
            self.sms_received.emit(sender, message, corrected_datetime)
            self.log_updated.emit()
            
            self.update_stats()
            
        except Exception as e:
            self.error_count += 1
            self.update_stats()
            error_msg = f"[ERROR] Processing SMS: {e}"
            self.append_to_display(error_msg)

    def _decode_message_safely(self, message_hex):
        """แปลงข้อความ UCS2 อย่างปลอดภัย - Fixed spacing"""
        if not message_hex:
            return ""
        
        try:
            message_clean = message_hex.strip().replace('"', '').replace(' ', '')
            print(f"🔍 DEBUG Message: Input hex = '{message_clean[:50]}...'")
            
            # ใช้ฟังก์ชัน decode_ucs2 ที่แก้ไขแล้ว
            decoded = decode_ucs2(message_clean)
            
            # ✅ เพิ่มการตรวจสอบและแก้ไขข้อความที่ติดกัน
            if decoded and decoded != message_clean:
                # ตรวจหาคำที่ติดกัน (เช่น "Badboygirl" -> "Bad boy girl")
                fixed_message = self._fix_concatenated_words(decoded)
                print(f"✅ DEBUG Message: Final = '{fixed_message}'")
                return fixed_message
            
            print(f"⚠️ DEBUG Message: Using original = '{decoded}'")
            return decoded
            
        except Exception as e:
            print(f"❌ DEBUG Message: Error = {e}")
            return message_hex
    
    def _fix_concatenated_words(self, text):
        """แก้ไขคำที่ติดกันในข้อความ - Simple word separation"""
        if not text:
            return text
        
        try:
            # ✅ แยกคำที่ติดกันด้วยกฎง่ายๆ
            import re
            
            # กรณี: ตัวเล็กตัวใหญ่ติดกัน เช่น "badBoy" -> "bad Boy"
            text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
            
            # กรณี: ตัวเลขกับตัวอักษร เช่น "hello123world" -> "hello 123 world"
            text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
            text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
            
            # กรณี: คำที่รู้จักติดกัน (สามารถเพิ่มได้)
            common_fixes = {
                'badboy': 'bad boy',
                'goodgirl': 'good girl',
                'badgirl': 'bad girl',
                'goodboy': 'good boy',
                'hellothere': 'hello there',
                'thankyou': 'thank you',
                'howareyou': 'how are you',
            }
            
            text_lower = text.lower()
            for wrong, correct in common_fixes.items():
                if wrong in text_lower:
                    # แทนที่โดยรักษาตัวพิมพ์เดิม
                    text = re.sub(re.escape(wrong), correct, text, flags=re.IGNORECASE)
            
            # ลบช่องว่างซ้ำ
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            print(f"Error fixing concatenated words: {e}")
            return text

    def _decode_sender_safely(self, sender_ucs2):
        """แปลง sender UCS2 อย่างปลอดภัย - Enhanced version"""
        if not sender_ucs2:
            return "Unknown"
        
        sender_clean = sender_ucs2.strip().replace('"', '').replace(' ', '')
        print(f"🔍 DEBUG Sender: Input = '{sender_clean}'")
        
        try:
            # ตรวจสอบว่าเป็น hex string หรือไม่
            if len(sender_clean) > 10 and all(c in '0123456789ABCDEFabcdef' for c in sender_clean):
                print(f"🔍 DEBUG Sender: Detected as UCS2 hex")
                
                # ลองแปลงจาก UCS2
                decoded = decode_ucs2(sender_clean)
                print(f"🔍 DEBUG Sender: UCS2 decoded = '{decoded}'")
                
                # ตรวจสอบว่าผลลัพธ์เป็นเบอร์โทรหรือไม่
                if decoded and decoded != sender_clean:
                    # ลบตัวอักษรที่ไม่ใช่เบอร์โทร
                    phone_chars = ''.join(c for c in decoded if c.isdigit() or c in ['+', '-', ' ', '(', ')'])
                    if phone_chars and (phone_chars.startswith('+') or len(''.join(filter(str.isdigit, phone_chars))) >= 9):
                        print(f"✅ DEBUG Sender: Valid phone detected = '{phone_chars}'")
                        return phone_chars
                
                # ถ้าแปลงไม่ได้หรือไม่เหมือนเบอร์โทร ลองวิธีอื่น
                try:
                    # ลองแปลงแบบ manual (ทีละ 4 hex chars)
                    manual_decoded = ""
                    for i in range(0, len(sender_clean), 4):
                        hex_char = sender_clean[i:i+4]
                        if len(hex_char) == 4:
                            try:
                                char_code = int(hex_char, 16)
                                if 32 <= char_code <= 126:  # ASCII printable
                                    manual_decoded += chr(char_code)
                            except ValueError:
                                continue
                    
                    if manual_decoded:
                        print(f"✅ DEBUG Sender: Manual decode = '{manual_decoded}'")
                        return manual_decoded
                        
                except Exception as e:
                    print(f"❌ DEBUG Sender: Manual decode error: {e}")
            
            # ถ้าไม่ใช่ hex หรือแปลงไม่ได้ ตรวจสอบว่าเป็นเบอร์โทรปกติหรือไม่
            if all(c.isdigit() or c in ['+', '-', ' ', '(', ')'] for c in sender_clean):
                print(f"✅ DEBUG Sender: Plain phone number = '{sender_clean}'")
                return sender_clean
            
            # fallback - ใช้ตัวเดิม
            print(f"⚠️ DEBUG Sender: Using original = '{sender_clean}'")
            return sender_clean
                
        except Exception as e:
            print(f"❌ DEBUG Sender: Error in decode: {e}")
            return sender_clean

    def update_old_dates_to_current():
        """อัพเดทข้อมูลเก่าวันที่ 25/07/25 ให้เป็น 30/07/2025"""
        try:
            from services.sms_log import get_log_file_path
            log_file = get_log_file_path("sms_inbox_log.csv")
            
            if not os.path.exists(log_file):
                print("ไม่มีไฟล์ log")
                return
            
            # อ่านข้อมูลเดิม
            updated_rows = []
            current_date = datetime.now().strftime("%d/%m/%Y")  # 30/07/2025
            
            with open(log_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # อ่าน header
                updated_rows.append(header)
                
                for row in reader:
                    if len(row) >= 4:
                        timestamp, phone, message, status = row[:4]
                        
                        # ตรวจสอบว่าเป็นวันที่ 25/07/25 หรือไม่
                        if '"25/07/25,' in timestamp or '25/07/25,' in timestamp:
                            print(f"🔄 Updating old date: {timestamp}")
                            
                            # แยกเวลา
                            clean_timestamp = timestamp.strip('"')
                            if ',' in clean_timestamp:
                                _, time_part = clean_timestamp.split(',', 1)
                                new_timestamp = f'"{current_date},{time_part}"'
                                
                                updated_rows.append([new_timestamp, phone, message, status])
                                print(f"✅ Updated to: {new_timestamp}")
                            else:
                                updated_rows.append(row)  # เก็บเดิม
                        else:
                            updated_rows.append(row)  # เก็บเดิม
            
            # เขียนข้อมูลใหม่
            with open(log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(updated_rows)
            
            print(f"✅ Updated log file successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error updating dates: {e}")
            return False


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