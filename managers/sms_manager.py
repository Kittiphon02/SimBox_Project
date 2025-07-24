# sms_manager.py
"""
จัดการการส่งและรับ SMS
"""

import serial
import time
import csv
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from core.utility_functions import decode_ucs2_to_text, encode_text_to_ucs2, get_timestamp_formatted


class SMSHandler:
    """จัดการการประมวลผล SMS ที่รับเข้า"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self._cmt_buffer = None
        self._notified_sms = set()  # เซ็ตเก็บ SMS ที่แจ้งเตือนไปแล้ว
    
    def process_new_sms_signal(self, data_line):
        """จัดการสัญญาณ SMS ใหม่ - decode UCS-2 และ fallback เป็น base16→base10"""
        line = data_line.strip()
        
        if hasattr(self.parent, 'update_at_result_display'):
            self.parent.update_at_result_display(f"[SMS SIGNAL] {line}")

        # กรณี CMTI (SMS เก็บในหน่วยความจำ)
        if line.startswith("+CMTI:"):
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS NOTIFICATION] {line}")
            return

        # กรณีข้อมูล SMS ที่ process มาแล้วจาก serial_service
        if "|" in line and not line.startswith("+"):
            try:
                self._process_formatted_sms(line)
            except Exception as e:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[SMS PARSE ERROR] {e}")
                    self.parent.update_at_result_display(f"[SMS RAW DATA] {line}")
            return

        # backward compatibility สำหรับ +CMT แบบเก่า
        if line.startswith("+CMT:"):
            self._cmt_buffer = line
            return

        if self._cmt_buffer:
            header = self._cmt_buffer
            body = line
            self._cmt_buffer = None
            try:
                self._process_legacy_cmt(header, body)
            except Exception as e:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[CMT ERROR] {e}")
    
    def _process_formatted_sms(self, line):
        """ประมวลผล SMS ที่มาในรูปแบบ sender_hex|message_hex|timestamp"""
        # แยก 3 ช่วง: sender_hex | message_hex | timestamp
        sender_hex, message_hex, timestamp = line.split("|", 2)
        
        # ตัดเครื่องหมาย " กับช่องว่างที่อาจมากับ hex string
        sender_hex = sender_hex.strip().replace('"', '').replace(' ', '')
        message_hex = message_hex.strip().replace(' ', '')

        # 1) ลอง decode UCS-2 ก่อน
        decoded_sender = decode_ucs2_to_text(sender_hex)

        # 2) ถ้า decode คืนค่าเดิม (แปลงไม่สำเร็จ) ให้ fallback ไปแปลงฐาน16→10
        if decoded_sender == sender_hex or not decoded_sender.strip():
            try:
                sender = str(int(sender_hex, 16))
            except ValueError:
                sender = sender_hex
        else:
            sender = decoded_sender

        # 3) ตัด null-char ท้ายออก (ในกรณี UCS-2)
        sender = sender.split("\x00", 1)[0]

        # แปลงข้อความด้วย UCS-2 ปกติ
        raw_message = decode_ucs2_to_text(message_hex)
        message = raw_message.split("\x00", 1)[0]

        # ตรวจสอบซ้ำ
        key = (timestamp, sender, message)
        if key in self._notified_sms:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[SMS DUPLICATE] Skipping duplicate")
            return
        self._notified_sms.add(key)

        # แสดง notification
        self._show_sms_notification(sender, message, timestamp)

        # แสดงใน real-time display
        if hasattr(self.parent, 'update_at_result_display'):
            self.parent.update_at_result_display(f"[REAL-TIME SMS] {timestamp} | {sender}: {message}")

        # บันทึกลง log
        self._save_sms_to_inbox_log(sender, message, timestamp)
    
    def _process_legacy_cmt(self, header, body):
        """ประมวลผล CMT แบบเก่า (fallback)"""
        try:
            # แยกข้อมูลจาก header
            match = re.match(r'\+CMT: "([^"]*)","","([^"]+)"', header)
            if not match:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[CMT ERROR] Invalid format: {header}")
                return
            
            sender_hex = match.group(1)
            timestamp = match.group(2)
            
            # แปลง UCS2
            sender = decode_ucs2_to_text(sender_hex)
            message = decode_ucs2_to_text(body)
            
            # ตรวจสอบซ้ำ
            key = (timestamp, sender, message)
            if key in self._notified_sms:
                return
            self._notified_sms.add(key)

            # แสดง notification
            self._show_sms_notification(sender, message, timestamp)

            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[LEGACY SMS] {timestamp} | {sender}: {message}")
            
            self._save_sms_to_inbox_log(sender, message, timestamp)
            
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[LEGACY CMT ERROR] {e}")
    
    def _show_sms_notification(self, sender, message, timestamp):
        """แสดง notification SMS ใหม่"""
        if hasattr(self.parent, 'show_non_blocking_message'):
            self.parent.show_non_blocking_message(
                "📱 New SMS Received!",
                f"📞 From: {sender}\n🕐 Time: {timestamp}\n💬 Message: {message}"
            )
    
    def _save_sms_to_inbox_log(self, sender, message, datetime_str):
        """บันทึก SMS ที่เข้ามาในรูปแบบ log"""
        try:
            from services.sms_log import append_sms_log
            append_sms_log("sms_inbox_log.csv", sender, message, "รับเข้า (real-time)")
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[Log Saved] SMS from {sender} recorded.")
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[Log Error] Failed to save SMS: {e}")


class SMSInboxManager:
    """จัดการ SMS inbox และการแสดงผล"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def show_inbox_sms(self):
        """แสดง SMS เข้าจากหน้าหลัก"""
        if not hasattr(self.parent, 'serial_thread') or not self.parent.serial_thread:
            QMessageBox.warning(self.parent, "Notice", "No connection found with Serial")
            return
        
        if hasattr(self.parent, 'clear_at_displays'):
            self.parent.clear_at_displays()
        
        try:
            # ส่งคำสั่ง AT เพื่อดึง SMS
            cmd1 = 'AT+CMGF=1'
            self.parent.serial_thread.send_command(cmd1)
            if hasattr(self.parent, 'update_at_command_display'):
                self.parent.update_at_command_display(cmd1)
            time.sleep(0.3)
            
            cmd2 = 'AT+CMGL="ALL"'
            self.parent.serial_thread.send_command(cmd2)
            if hasattr(self.parent, 'update_at_command_display'):
                self.parent.update_at_command_display(cmd2)
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("=== Retrieving SMS from SIM Card ===")
                self.parent.update_at_result_display("Please wait for response...")
                self.parent.update_at_result_display("(SMS from SIM will appear in response above)")
            
            time.sleep(1)
            
            # อ่าน SMS จาก log file
            log_sms_lines = self._read_sms_from_log()
            
            if hasattr(self.parent, 'update_at_result_display'):
                if log_sms_lines:
                    self.parent.update_at_result_display("\n=== SMS from Log File ===")
                    for sms_line in log_sms_lines:
                        self.parent.update_at_result_display(sms_line)
                else:
                    self.parent.update_at_result_display("\n=== SMS from Log File ===")
                    self.parent.update_at_result_display("(No SMS in log file)")

        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"An error occurred: {e}")
    
    def clear_all_sms(self):
        """ลบ SMS ทั้งหมดจากหน้าหลัก"""
        if not hasattr(self.parent, 'port_combo') or not hasattr(self.parent, 'baud_combo'):
            QMessageBox.warning(self.parent, "Notice", "Port configuration not available")
            return
            
        port = self.parent.port_combo.currentData()
        baudrate = int(self.parent.baud_combo.currentText())
        
        if not port or port == "Device not found":
            QMessageBox.warning(self.parent, "Notice", "Please select a port before use")
            return
        
        reply = QMessageBox.question(
            self.parent, 'Confirm deletion', 
            'Do you want to delete all SMS on your SIM card?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                ser = serial.Serial(port, baudrate, timeout=5)
                
                cmd1 = "AT+CMGF=1"
                ser.write(b'AT+CMGF=1\r')
                if hasattr(self.parent, 'update_at_command_display'):
                    self.parent.update_at_command_display(cmd1)
                time.sleep(0.1)
                
                cmd2 = "AT+CMGD=1,4"
                ser.write(b'AT+CMGD=1,4\r')
                if hasattr(self.parent, 'update_at_command_display'):
                    self.parent.update_at_command_display(cmd2)
                time.sleep(0.5)
                
                resp = ser.read(200).decode(errors="ignore")
                result = f"[CLEAR SMS] {resp if resp else '(All SMS have been deleted)'}"
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(result)
                ser.close()
                
                QMessageBox.information(self.parent, "Success", "All SMS have been deleted")
                
            except Exception as e:
                error_msg = f"An error occurred: {e}"
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(error_msg)
                QMessageBox.critical(self.parent, "Error", error_msg)
    
    def _read_sms_from_log(self):
        """อ่าน SMS จาก log file"""
        try:
            from services.sms_log import get_log_file_path
            log_file = get_log_file_path('sms_inbox_log.csv')
            
            log_lines = []
            
            if not os.path.isfile(log_file):
                return log_lines
            
            try:
                with open(log_file, newline='', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return log_lines
                        
                    f.seek(0)
                    reader = csv.reader(f)
                    
                    first_row = next(reader, None)
                    if first_row and (first_row[0] == 'Received_Time' or first_row[0] == 'Datetime'):
                        pass  # ข้าม header
                    else:
                        if first_row and len(first_row) >= 3:
                            line_result = self._format_log_line(first_row)
                            if line_result:
                                log_lines.append(line_result)
                    
                    for row in reader:
                        if len(row) >= 3:
                            line_result = self._format_log_line(row)
                            if line_result:
                                log_lines.append(line_result)
                            
            except Exception as e:
                print(f"Error reading SMS log: {e}")
            
            return log_lines
            
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[LOG ERROR] Error reading log: {e}")
            return []
    
    def _format_log_line(self, row):
        """จัดรูปแบบข้อมูล log line"""
        try:
            if len(row) >= 4 and ('real-time' in row[3] or 'รับเข้า' in row[3]):
                # รูปแบบใหม่
                datetime_str, sender, message = row[0], row[1], row[2]
                datetime_str = datetime_str.strip('"')
                return f"[LOG] {datetime_str} | {sender}: {message}"
            else:
                # รูปแบบเก่า
                timestamp, sender, message = row[0], row[1], row[2]
                received_time = row[4] if len(row) > 4 else timestamp
                return f"[LOG] {received_time} | {sender}: {message}"
        except Exception:
            return None


class SMSLogReader:
    """อ่านและจัดการ SMS log files"""
    
    def __init__(self):
        pass
    
    def read_sms_logs(self, log_type="inbox"):
        """อ่าน SMS logs จากไฟล์
        
        Args:
            log_type (str): ประเภท log ("inbox" หรือ "sent")
            
        Returns:
            list: รายการ SMS ที่อ่านได้
        """
        try:
            from services.sms_log import get_log_file_path
            
            if log_type == "inbox":
                log_file = get_log_file_path('sms_inbox_log.csv')
            else:
                log_file = get_log_file_path('sms_sent_log.csv')
            
            sms_list = []
            
            if not os.path.isfile(log_file):
                return sms_list
            
            with open(log_file, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                
                # ข้าม header
                next(reader, None)
                
                for row in reader:
                    if len(row) >= 3:
                        sms_data = {
                            'datetime': row[0],
                            'phone': row[1],
                            'message': row[2],
                            'status': row[3] if len(row) > 3 else ""
                        }
                        sms_list.append(sms_data)
            
            return sms_list
            
        except Exception as e:
            print(f"Error reading SMS logs: {e}")
            return []
    
    def export_sms_logs(self, sms_list, export_path):
        """ส่งออก SMS logs เป็นไฟล์
        
        Args:
            sms_list (list): รายการ SMS
            export_path (str): path ที่ต้องการส่งออก
            
        Returns:
            bool: True ถ้าส่งออกสำเร็จ
        """
        try:
            if export_path.endswith('.csv'):
                # Export เป็น CSV
                with open(export_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['วันที่', 'เบอร์โทร', 'ข้อความ', 'สถานะ'])
                    
                    for sms in sms_list:
                        writer.writerow([
                            sms.get('datetime', ''),
                            sms.get('phone', ''),
                            sms.get('message', ''),
                            sms.get('status', '')
                        ])
            else:
                # Export เป็น Excel
                try:
                    import pandas as pd
                    df = pd.DataFrame(sms_list)
                    df.columns = ['วันที่', 'เบอร์โทร', 'ข้อความ', 'สถานะ']
                    df.to_excel(export_path, index=False)
                except ImportError:
                    raise Exception("ต้องติดตั้ง pandas สำหรับการ export Excel")
            
            return True
            
        except Exception as e:
            print(f"Error exporting SMS logs: {e}")
            return False