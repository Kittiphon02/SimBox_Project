# sms_manager.py
"""
จัดการการส่งและรับ SMS - Enhanced with SIM status checking
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
from services.sms_log import get_log_file_path

class SMSHandler:
    """จัดการการประมวลผล SMS ที่รับเข้า"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self._cmt_buffer = None
        self._notified_sms = set()  # เซ็ตเก็บ SMS ที่แจ้งเตือนไปแล้ว

        # เชื่อมต่อกับ serial thread เมื่อ parent มี serial_thread
        if hasattr(parent, 'serial_thread') and parent.serial_thread:
            parent.serial_thread.new_sms_signal.connect(self.process_new_sms_signal)

    # ===== helpers for display routing =====
    def _resp(self, text: str):
        # โชว์ที่ Response (สรุปสำคัญ)
        if hasattr(self.parent, 'update_at_result_display'):
            self.parent.update_at_result_display(text)

    def _mon(self, text: str):
        # โชว์ที่ SMS Monitor (log ละเอียดยาว)
        if hasattr(self.parent, 'at_monitor_signal'):
            from datetime import datetime
            ts = datetime.now().strftime('%H:%M:%S')
            self.parent.at_monitor_signal.emit(f"[{ts}] {text}")
        else:
            # ถ้ายังไม่มี monitor ให้ fallback ไป Response
            self._resp(text)
    
    def send_sms_main(self, phone_number, message):
        """ส่ง SMS พร้อมตรวจสอบสถานะ SIM - Enhanced version"""
        try:
            # ตรวจสอบการเชื่อมต่อ serial
            if not hasattr(self.parent, 'serial_thread') or not self.parent.serial_thread:
                self._handle_sms_error(phone_number, message, "ไม่มีการเชื่อมต่อ Serial")
                return False
            
            if not self.parent.serial_thread.isRunning():
                self._handle_sms_error(phone_number, message, "การเชื่อมต่อ Serial ไม่ทำงาน")
                return False
            
            # ตรวจสอบข้อมูล input
            if not phone_number or not message:
                error_msg = "ข้อมูลไม่ครบถ้วน"
                self._handle_sms_error(phone_number, message, error_msg)
                return False
            
            # ⭐ ตรวจสอบสถานะ SIM ก่อนส่ง
            sim_status = self._check_sim_status()
            if not sim_status['ready']:
                self._handle_sms_error(phone_number, message, sim_status['error'])
                return False
            
            # ⭐ แสดง Loading Dialog
            if hasattr(self.parent, 'show_loading_dialog'):
                self.parent.show_loading_dialog()
            
            # เริ่มกระบวนการส่ง SMS
            return self._send_sms_process(phone_number, message)
            
        except Exception as e:
            error_msg = f"ข้อผิดพลาดในระบบ: {str(e)}"
            
            # ⭐ ป้องกันการเรียก _handle_sms_error ซ้ำ
            if not hasattr(self, '_handling_error') or not self._handling_error:
                self._handle_sms_error(phone_number, message, error_msg)
            else:
                # ถ้ากำลัง handle error อยู่ ให้แสดง log เบื้องต้นเท่านั้น
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[SMS SYSTEM ERROR] ❌ {error_msg}")
                print(f"SMS System Error (secondary): {error_msg}")
            
            return False
    
    def _check_sim_status(self):
        """ตรวจสอบสถานะ SIM ก่อนส่ง SMS"""
        try:
            # ตรวจสอบจากข้อมูล SIM ที่โหลดไว้
            if not hasattr(self.parent, 'sims') or not self.parent.sims:
                return {'ready': False, 'error': 'ไม่พบข้อมูล SIM ในระบบ'}
            
            sim = self.parent.sims[0]
            
            # ตรวจสอบ IMSI
            if not hasattr(sim, 'imsi') or not sim.imsi or sim.imsi == '-':
                return {'ready': False, 'error': 'ไม่มี SIM Card หรือ SIM ไม่พร้อมใช้งาน'}
            
            # ตรวจสอบว่า IMSI เป็นตัวเลขที่ถูกต้อง
            if not sim.imsi.isdigit() or len(sim.imsi) < 15:
                return {'ready': False, 'error': 'SIM Card ไม่ถูกต้องหรือเสียหาย'}
            
            # ตรวจสอบ Carrier
            if not hasattr(sim, 'carrier') or sim.carrier in ['Unknown', 'No SIM']:
                return {'ready': False, 'error': 'SIM Card ไม่สามารถระบุผู้ให้บริการได้'}
            
            # ตรวจสอบสัญญาณ
            if hasattr(sim, 'signal'):
                signal_str = str(sim.signal).upper()
                if any(keyword in signal_str for keyword in ['NO SIM', 'NO SIGNAL', 'ERROR', 'PIN REQUIRED', 'PUK REQUIRED']):
                    return {'ready': False, 'error': f'SIM มีปัญหา: {sim.signal}'}
            
            return {'ready': True, 'error': None}
            
        except Exception as e:
            return {'ready': False, 'error': f'ไม่สามารถตรวจสอบสถานะ SIM ได้: {str(e)}'}
    
    def _send_sms_process(self, phone_number, message):
        """กระบวนการส่ง SMS"""
        try:
            if hasattr(self.parent, '_is_sending_sms'):
                self.parent._is_sending_sms = True
            
            # เข้ารหัสข้อความ
            phone_hex = encode_text_to_ucs2(phone_number)
            msg_ucs2 = encode_text_to_ucs2(message)
            
            # ส่งคำสั่ง AT ตามลำดับ
            self._send_at_command_with_progress('AT+CMGF=1', "เชื่อมต่อกับ Modem...")
            time.sleep(0.2)
            self._send_at_command_with_progress('AT+CSCS="UCS2"', "ตั้งค่า AT Commands...")
            time.sleep(0.2)
            self._send_at_command_with_progress('AT+CSMP=17,167,0,8', "เตรียมข้อความ...")
            time.sleep(0.2)
            self._send_at_command_with_progress(f'AT+CMGS="{phone_hex}"', "เข้ารหัสข้อมูล...")
            time.sleep(0.5)

            # อัพเดทสถานะ
            if hasattr(self.parent, 'loading_widget'):
                self.parent.loading_widget.update_status("ส่งข้อความ SMS...")
            
            # ส่งข้อความ
            success = self.parent.serial_thread.send_raw(msg_ucs2.encode() + bytes([26]))
            if not success:
                raise Exception("ไม่สามารถส่งข้อมูล SMS ผ่าน Serial ได้")
            
            if hasattr(self.parent, 'update_at_command_display'):
                self.parent.update_at_command_display(f"SMS Content: {message}")
            
            # บันทึก log สำเร็จ
            self._save_sms_success_log(phone_number, message)
            
            # แสดงผลสำเร็จ
            if hasattr(self.parent, 'loading_widget'):
                self.parent.loading_widget.complete_sending_success()
            
            return True
            
        except Exception as e:
            error_msg = f"เกิดข้อผิดพลาดในการส่ง SMS: {str(e)}"
            self._handle_sms_error(phone_number, message, error_msg)
            return False
    
    def _send_at_command_with_progress(self, command, status_text):
        """ส่งคำสั่ง AT พร้อมอัพเดท loading status"""
        if hasattr(self.parent, 'loading_widget'):
            self.parent.loading_widget.update_status(status_text)
        
        if hasattr(self.parent, 'serial_thread'):
            success = self.parent.serial_thread.send_command(command)
            if not success:
                raise Exception(f"ไม่สามารถส่งคำสั่ง {command} ได้")
        
        if hasattr(self.parent, 'update_at_command_display'):
            self.parent.update_at_command_display(command)
    
    def _save_sms_success_log(self, phone_number, message):
        """บันทึก SMS ที่ส่งสำเร็จ"""
        try:
            from services.sms_log import log_sms_sent
            log_sms_sent(phone_number, message, "ส่งสำเร็จ")
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[Log Saved] ✅ SMS sent recorded successfully.")
        except Exception as e:
            print(f"Error saving SMS success log: {e}")
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[Log Error] ⚠️ Failed to save success log: {e}")
    
    def _handle_sms_error(self, phone_number, message, error_msg):
        """จัดการข้อผิดพลาดในการส่ง SMS - ป้องกัน duplicate และ None error"""
        
        # ⭐ ป้องกันการเรียกซ้ำ
        if hasattr(self, '_handling_error') and self._handling_error:
            return
        self._handling_error = True
        
        try:
            # แสดงข้อผิดพลาดใน UI
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS ERROR] ❌ {error_msg}")
            
            # แสดง MessageBox
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.parent, 
                "❌ ส่ง SMS ไม่สำเร็จ", 
                f"ไม่สามารถส่ง SMS ได้\n\n"
                f"📞 เบอร์: {phone_number}\n"
                f"💬 ข้อความ: {message[:50]}{'...' if len(message) > 50 else ''}\n\n"
                f"❌ สาเหตุ: {error_msg}\n\n"
                f"💡 แนะนำ:\n"
                f"• ตรวจสอบ SIM Card\n"
                f"• คลิก 'Refresh Ports'\n"
                f"• ตรวจสอบการเชื่อมต่อ"
            )
            
            # บันทึก log ข้อผิดพลาด
            self._save_sms_error_log(phone_number, message, error_msg)
            
            # ⭐ ตรวจสอบว่า loading_widget มีอยู่จริงก่อนเรียกใช้
            if (hasattr(self.parent, 'loading_widget') and 
                self.parent.loading_widget is not None and
                hasattr(self.parent.loading_widget, 'complete_sending_error')):
                self.parent.loading_widget.complete_sending_error(error_msg)
            else:
                # ถ้าไม่มี loading_widget ให้ปิด loading dialog
                if (hasattr(self.parent, 'loading_dialog') and 
                    self.parent.loading_dialog is not None):
                    self.parent.loading_dialog.close()
                    self.parent.loading_dialog = None
            
            # รีเซ็ตสถานะ
            if hasattr(self.parent, '_is_sending_sms'):
                self.parent._is_sending_sms = False
                
        except Exception as e:
            print(f"Error in _handle_sms_error: {e}")
        finally:
            # ⭐ รีเซ็ตการป้องกันการเรียกซ้ำ
            self._handling_error = False
    
    def _save_sms_error_log(self, phone_number, message, error_msg):
        """บันทึก SMS ที่ส่งไม่สำเร็จ"""
        try:
            from services.sms_log import log_sms_sent
            status = f"ส่งไม่สำเร็จ: {error_msg}"
            log_sms_sent(phone_number, message, status)
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[Log Saved] ❌ SMS error recorded in log.")
                
        except Exception as e:
            print(f"Error saving SMS error log: {e}")
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[Log Error] ⚠️ Failed to save error log: {e}")
    
    def process_new_sms_signal(self, data_line):
        """จัดการสัญญาณ SMS ใหม่ - Fixed 2-line SMS processing"""
        line = data_line.strip()
        
        self._mon(f"[SMS DEBUG] Received signal: {line}")

        # กรณี CMTI (SMS เก็บในหน่วยความจำ)
        if line.startswith("+CMTI:"):
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS NOTIFICATION] {line}")
            return

        # กรณีข้อมูล SMS รูปแบบ header|body (จาก serial_service)
        if "|" in line and line.startswith("+CMT:"):
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS PROCESSING] Processing 2-line SMS...")
            try:
                self._process_cmt_2line_sms(line)
            except Exception as e:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[SMS PARSE ERROR] {e}")
            return

        # กรณีข้อมูล SMS รูปแบบเก่า (formatted)
        if "|" in line and not line.startswith("+"):
            try:
                self._process_formatted_sms(line)
            except Exception as e:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[SMS PARSE ERROR] {e}")
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

    def _process_cmt_2line_sms(self, combined_line):
        """ประมวลผล SMS รูปแบบ +CMT: header|body - Fixed imports and decoding"""
        try:
            # แยก header และ body
            header, body = combined_line.split("|", 1)
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS PARSE] Header: {header}")
                self.parent.update_at_result_display(f"[SMS PARSE] Body: {body}")
            
            # แยกข้อมูลจาก header: +CMT: "+66653988461","","25/08/29,10:15:35+28"
            import re
            match = re.match(r'\+CMT: "([^"]*)","([^"]*)","([^"]+)"', header)
            if not match:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[CMT ERROR] Invalid header format: {header}")
                return
            
            sender_raw = match.group(1)
            datetime_str = match.group(3)
            
            # Fix: import normalize_phone_number
            try:
                from core.utility_functions import normalize_phone_number
                sender = normalize_phone_number(sender_raw) if sender_raw else "Unknown"
            except ImportError:
                # Fallback ถ้า import ไม่ได้
                sender = sender_raw.replace('+66', '0') if sender_raw.startswith('+66') else sender_raw
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS SENDER] Raw: {sender_raw} -> Normalized: {sender}")
            
            # ประมวลผล message (UCS2 hex to Thai text)
            message = self._decode_message_safely(body)
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS DECODED] From: {sender}")
                self.parent.update_at_result_display(f"[SMS DECODED] Message: {message}")
                self.parent.update_at_result_display(f"[SMS DECODED] Time: {datetime_str}")
            
            # ตรวจสอบซ้ำ
            key = (datetime_str, sender, message)
            if key in self._notified_sms:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SMS DUPLICATE] Skipping duplicate")
                return
            self._notified_sms.add(key)

            # แสดง notification
            self._show_sms_notification(sender, message, datetime_str)

            # บันทึกลง log
            self.parent.update_at_result_display("[SMS SAVE] Attempting to save to log...")
            success = self._save_sms_to_inbox_log(sender, message, datetime_str)
            
            if success:
                self.parent.update_at_result_display("[SMS SAVE] Successfully saved to log!")
            else:
                self.parent.update_at_result_display("[SMS SAVE] Failed to save to log!")

            # อัพเดท counter
            # if hasattr(self.parent, 'on_new_sms_received'):
            #     self.parent.on_new_sms_received()
                
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[CMT 2-LINE ERROR] {e}")
                import traceback
                self.parent.update_at_result_display(f"[CMT 2-LINE TRACE] {traceback.format_exc()}")

    def _decode_message_safely(self, body: str) -> str:
        """
        รับ body ของบรรทัด CMT (มักเป็น UCS2 hex) แล้วพยายามถอดรหัสเป็นข้อความไทย/อังกฤษอย่างปลอดภัย
        - รองรับทั้งกรณีเป็น hex UCS2 และกรณีเป็นข้อความ ASCII ปกติ
        - ตัด \x00 ท้ายสตริงกรณีถอดจาก UCS2
        """
        try:
            s = (body or "").strip().strip('"').replace(" ", "")
            # เดาว่าเป็น HEX ไหม (ตัวอักษร 0-9A-F ทั้งหมด และความยาวต้องเป็นเลขคู่)
            import re as _re
            is_hex = bool(_re.fullmatch(r'[0-9A-Fa-f]+', s)) and (len(s) % 2 == 0)

            if is_hex:
                # ลองใช้ util ที่มีในโปรเจกต์ก่อน
                try:
                    text = decode_ucs2_to_text(s)
                    return text.split("\x00", 1)[0]
                except Exception:
                    # เผื่อ util ล้มเหลว ใช้วิธีมาตรฐาน (UTF-16BE)
                    try:
                        return bytes.fromhex(s).decode('utf-16-be', errors='ignore').split("\x00", 1)[0]
                    except Exception:
                        pass

            # ไม่ใช่ hex → ถือเป็นข้อความปกติ
            return s
        except Exception:
            # ถ้าเกิดปัญหา ให้คืนค่าดิบเพื่อไม่ให้หลุดการทำงาน
            return body or ""
        
    def test_sms_logging(self):
        """ทดสอบการบันทึก SMS log"""
        try:
            test_sender = "+66653988461"
            test_message = "ทดสอบการบันทึก SMS"
            test_datetime = "29/08/2025,14:30:00+07"
            
            self.update_at_result_display("[TEST] Testing SMS logging...")
            
            # ทดสอบผ่าน SMS handler
            success = self.sms_handler._save_sms_to_inbox_log(test_sender, test_message, test_datetime)
            
            if success:
                self.update_at_result_display("[TEST] SMS logging test successful!")
            else:
                self.update_at_result_display("[TEST] SMS logging test failed!")
                
        except Exception as e:
            self.update_at_result_display(f"[TEST ERROR] {e}")

    def _process_formatted_sms(self, line):
        """ประมวลผล SMS ที่มาในรูปแบบ sender_hex|message_hex|timestamp - Fixed phone decode"""
        # แยก 3 ช่วง: sender_hex | message_hex | timestamp
        sender_hex, message_hex, timestamp = line.split("|", 2)
        
        # ✅ แปลง sender จาก UCS2 hex เป็นเบอร์โทรปกติ
        sender_raw = sender_hex.strip().replace('"', '').replace(' ', '')
        print(f"🔍 DEBUG SMS: Raw sender hex = '{sender_raw}'")
        
        # ลองแปลง sender จาก UCS2 ก่อน
        try:
            if len(sender_raw) > 10 and all(c in '0123456789ABCDEF' for c in sender_raw.upper()):
                # เป็น hex string - แปลงเป็นเบอร์โทร
                sender_decoded = decode_ucs2_to_text(sender_raw)
                print(f"🔍 DEBUG SMS: Decoded sender = '{sender_decoded}'")
                
                # ตรวจสอบว่าเป็นเบอร์โทรหรือไม่
                if sender_decoded and (sender_decoded.startswith('+') or sender_decoded.isdigit()):
                    sender = sender_decoded
                else:
                    # ถ้าแปลงไม่ได้หรือไม่ใช่เบอร์โทร ใช้ hex เดิม
                    sender = sender_raw
            else:
                # ไม่ใช่ hex หรือสั้นเกินไป - ใช้เดิม
                sender = sender_raw
        except Exception as e:
            print(f"❌ DEBUG SMS: Error decoding sender: {e}")
            sender = sender_raw

        print(f"✅ DEBUG SMS: Final sender = '{sender}'")

        # แปลงข้อความ:
        # ตรวจสอบว่า message_hex น่าจะเป็น UCS2-encoded hex จริงๆ หรือไม่
        is_hex = bool(re.fullmatch(r'[0-9A-Fa-f]+', message_hex))
        has_hex_letters = any(c in message_hex for c in "ABCDEFabcdef")
        looks_like_ucs2 = is_hex and len(message_hex) % 4 == 0 and len(message_hex) > 4

        if is_hex and (has_hex_letters or looks_like_ucs2):
            # น่าจะเป็น UCS2 → decode
            raw_message = decode_ucs2_to_text(message_hex)
        else:
            # ปกติแล้วเป็น ASCII/text ปกติ
            raw_message = message_hex

        # ตัด null-terminator ถ้ามี (เฉพาะกรณี decode มาจาก UCS2)
        message = raw_message.split("\x00", 1)[0]

        print(f"✅ DEBUG SMS: Final message = '{message}'")

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

        # หลัง self._show_sms_notification(...) หรือหลัง update_at_result_display
        # self.parent.incoming_sms_count += 1
        # self.parent.lbl_msg_count.setText(f"Messages: {self.parent.incoming_sms_count}")

    
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

                # หลัง self._show_sms_notification(...) หรือหลัง update_at_result_display
                # self.parent.incoming_sms_count += 1
                # self.parent.lbl_msg_count.setText(f"Messages: {self.parent.incoming_sms_count}")

    
    def _show_sms_notification(self, sender, message, timestamp):
        """แสดง notification SMS ใหม่"""
        if hasattr(self.parent, 'show_non_blocking_message'):
            self.parent.show_non_blocking_message(
                "📱 New SMS Received!",
                f"📞 From: {sender}\n🕐 Time: {timestamp}\n💬 Message: {message}"
            )
    
    def _save_sms_to_inbox_log(self, sender, message, datetime_str):
        try:
            from services.sms_log import log_sms_inbox

            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[LOG DEBUG] Saving SMS: {sender} -> {message[:30]}...")

            success = log_sms_inbox(sender, message, "รับเข้า (real-time)")
            if success:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[LOG SUCCESS] SMS from {sender} saved to CSV successfully")
                return True
            else:
                return self._fallback_save_sms(sender, message, datetime_str)
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[LOG ERROR] Failed to save SMS: {e}")
            return self._fallback_save_sms(sender, message, datetime_str)

    def _fallback_save_sms(self, sender, message, datetime_str):
        """บันทึก SMS แบบ fallback เมื่อ main method ไม่สำเร็จ"""
        try:
             # ดึง log file path
            log_file = get_log_file_path("sms_inbox_log.csv")
            
            # สร้างโฟลเดอร์ถ้าไม่มี
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # ตรวจสอบว่าไฟล์มีอยู่หรือไม่ (สำหรับ header)
            is_new_file = not os.path.exists(log_file) or os.path.getsize(log_file) == 0
            
            # เตรียม timestamp
            now = datetime.now()
            timestamp = now.strftime('%d/%m/%Y,%H:%M:%S+07')
            
            # บันทึกลงไฟล์
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                
                # เขียน header ถ้าเป็นไฟล์ใหม่
                if is_new_file:
                    writer.writerow(['Received_Time', 'Sender', 'Message', 'Status'])
                
                # เขียนข้อมูล SMS
                writer.writerow([timestamp, sender, message, 'รับเข้า (real-time)'])
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[FALLBACK SUCCESS] SMS saved using fallback method")
                
            return True
            
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[FALLBACK ERROR] Fallback save also failed: {e}")
            return False

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