# managers/at_command_manager.py
"""
จัดการคำสั่ง AT และประวัติคำสั่ง
"""

import os
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from core.utility_functions import encode_text_to_ucs2
from core.constants import DEFAULT_AT_COMMANDS, AT_HISTORY_FILE


class ATCommandManager:
    """คลาสจัดการคำสั่ง AT และประวัติ"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.command_history_file = AT_HISTORY_FILE
        self.default_commands = DEFAULT_AT_COMMANDS
        
    def load_command_history(self, combo_widget):
        """โหลดประวัติคำสั่ง AT จากไฟล์"""
        try:
            # เพิ่มคำสั่งเริ่มต้น
            combo_widget.addItems(self.default_commands)
            
            # โหลดคำสั่งเพิ่มเติมจากไฟล์
            if os.path.exists(self.command_history_file):
                with open(self.command_history_file, encoding="utf-8") as f:
                    commands = [line.strip() for line in f if line.strip()]
                    for cmd in commands:
                        if combo_widget.findText(cmd) == -1:  # ไม่มีในรายการ
                            combo_widget.addItem(cmd)
        except FileNotFoundError:
            self.save_command_history(combo_widget)
        except Exception as e:
            print(f"Error loading AT command history: {e}")
    
    def save_command_history(self, combo_widget):
        """บันทึกประวัติคำสั่ง AT ลงไฟล์"""
        try:
            commands = [combo_widget.itemText(i) for i in range(combo_widget.count())]
            with open(self.command_history_file, "w", encoding="utf-8") as f:
                for cmd in commands:
                    f.write(cmd + "\n")
        except Exception as e:
            print(f"Unable to save AT command history: {e}")
    
    def add_command_to_history(self, combo_widget, command):
        """เพิ่มคำสั่งใหม่ลงในประวัติ"""
        if not command or command in [combo_widget.itemText(i) for i in range(combo_widget.count())]:
            return
        
        combo_widget.addItem(command)
        self.save_command_history(combo_widget)
    
    def remove_command_from_history(self, combo_widget, input_widget):
        """ลบคำสั่ง AT ที่เลือกใน ComboBox"""
        current_idx = combo_widget.currentIndex()
        current_text = combo_widget.currentText().strip()
        
        if current_idx >= 0 and combo_widget.count() > 1:
            reply = QMessageBox.question(
                self.parent, 'Confirm deletion', 
                f'Do you want to delete the command "{current_text}" ?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                combo_widget.removeItem(current_idx)
                self.save_command_history(combo_widget)
                
                if combo_widget.count() > 0:
                    new_text = combo_widget.currentText()
                    input_widget.setPlainText(new_text)
                else:
                    input_widget.clear()
                
                QMessageBox.information(
                    self.parent, "Deletion successful", 
                    f"Delete command \"{current_text}\" finished!!"
                )
        else:
            if combo_widget.count() <= 1:
                QMessageBox.warning(self.parent, "Notice", "The last command cannot be deleted")
            else:
                QMessageBox.warning(self.parent, "Notice", "Please select the command you want to delete")


class SpecialCommandHandler:
    """จัดการคำสั่งพิเศษ AT+RUN, AT+STOP, AT+CLEAR"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def handle_at_run_command(self):
        """จัดการคำสั่ง AT+RUN - เริ่ม SMS Monitoring"""
        try:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[AT+RUN] Processing command...")
            
            # ตรวจสอบว่า SIM recovery กำลังทำงานอยู่หรือไม่
            if getattr(self.parent, 'sim_recovery_in_progress', False):
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[AT+RUN] ⚠️ SIM recovery in progress, please wait...")
                return
            
            # ตรวจสอบ SMS monitor dialog
            if (hasattr(self.parent, 'sms_monitor_dialog') and 
                self.parent.sms_monitor_dialog and 
                self.parent.sms_monitor_dialog.isVisible()):
                
                if hasattr(self.parent.sms_monitor_dialog, 'start_monitoring'):
                    self.parent.sms_monitor_dialog.start_monitoring()
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[AT+RUN] SMS Real-time monitoring started")
                    return
            
            # เปิด SMS monitor ใหม่
            self._open_sms_monitor()
                    
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[AT+RUN ERROR] {e}")
    
    def handle_at_stop_command(self):
        """จัดการคำสั่ง AT+STOP - หยุด SMS Monitoring"""
        try:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[AT+STOP] Processing command...")
            
            if (hasattr(self.parent, 'sms_monitor_dialog') and 
                self.parent.sms_monitor_dialog and 
                self.parent.sms_monitor_dialog.isVisible()):
                
                if hasattr(self.parent.sms_monitor_dialog, 'stop_monitoring'):
                    self.parent.sms_monitor_dialog.stop_monitoring()
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[AT+STOP] SMS Real-time monitoring stopped")
                else:
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[AT+STOP ERROR] SMS Monitor not ready")
            else:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[AT+STOP] No SMS Monitor window open")
                    
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[AT+STOP ERROR] {e}")
    
    def handle_at_clear_command(self):
        """จัดการคำสั่ง AT+CLEAR - เคลียร์ SMS Monitoring"""
        try:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[AT+CLEAR] Processing command...")
            
            if (hasattr(self.parent, 'sms_monitor_dialog') and 
                self.parent.sms_monitor_dialog and 
                self.parent.sms_monitor_dialog.isVisible()):
                
                if hasattr(self.parent.sms_monitor_dialog, 'clear_monitoring'):
                    self.parent.sms_monitor_dialog.clear_monitoring()
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[AT+CLEAR] SMS Real-time monitoring cleared")
                else:
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[AT+CLEAR ERROR] Clear method not found")
            else:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[AT+CLEAR] No SMS Monitor window open")
                    
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[AT+CLEAR ERROR] {e}")
    
    def _open_sms_monitor(self):
        """เปิด SMS Monitor ใหม่"""
        try:
            if not hasattr(self.parent, 'port_combo') or not hasattr(self.parent, 'baud_combo'):
                return
                
            port = self.parent.port_combo.currentData()
            baudrate = int(self.parent.baud_combo.currentText())
            
            if not port or port == "Device not found" or not getattr(self.parent, 'serial_thread', None):
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[AT+RUN ERROR] Please check port and connection")
                return
            
            # Import และสร้าง SMS monitor
            from widgets.sms_realtime_monitor import SmsRealtimeMonitor
            self.parent.sms_monitor_dialog = SmsRealtimeMonitor(
                port, baudrate, self.parent, 
                serial_thread=self.parent.serial_thread
            )
            
            # ตั้งค่า dialog
            self.parent.sms_monitor_dialog.setModal(False)
            from PyQt5.QtCore import Qt
            self.parent.sms_monitor_dialog.setWindowFlags(
                Qt.Window | Qt.WindowMinimizeButtonHint | 
                Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
            )
            
            # เชื่อมต่อ signals
            if hasattr(self.parent, 'on_realtime_sms_received'):
                self.parent.sms_monitor_dialog.sms_received.connect(self.parent.on_realtime_sms_received)
            if hasattr(self.parent, 'on_sms_log_updated'):
                self.parent.sms_monitor_dialog.log_updated.connect(self.parent.on_sms_log_updated)
            if hasattr(self.parent, 'on_sms_monitor_closed'):
                self.parent.sms_monitor_dialog.finished.connect(self.parent.on_sms_monitor_closed)
            
            self.parent.sms_monitor_dialog.show()
            
            # เริ่ม monitoring หลังจากรอ
            QTimer.singleShot(1000, self._start_monitoring_delayed)
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[AT+RUN] SMS Monitor opened")
                
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[AT+RUN ERROR] Failed to open SMS Monitor: {e}")
    
    def _start_monitoring_delayed(self):
        """เริ่ม monitoring หลังจากรอให้ dialog เปิดเสร็จ"""
        try:
            if (hasattr(self.parent, 'sms_monitor_dialog') and 
                self.parent.sms_monitor_dialog and 
                self.parent.sms_monitor_dialog.isVisible()):
                
                if hasattr(self.parent.sms_monitor_dialog, 'start_monitoring'):
                    self.parent.sms_monitor_dialog.start_monitoring()
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[AT+RUN] Monitoring started successfully!")
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[AT+RUN ERROR] Failed to start: {e}")


class SMSManager:
    """จัดการการส่ง SMS"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def prepare_sms_sending(self, phone_number, message):
        """เตรียมการส่ง SMS"""
        if not getattr(self.parent, 'serial_thread', None):
            QMessageBox.warning(self.parent, "Notice", "No connection found with Serial")
            return False

        if not hasattr(self.parent, 'sims') or not self.parent.sims or not self.parent.sims[0].imsi.isdigit():
            self._show_no_sim_error(phone_number, message)
            return False

        if not phone_number:
            QMessageBox.warning(self.parent, "Notice", "Please enter the destination number")
            return False

        if not message:
            QMessageBox.warning(self.parent, "Notice", "Please fill in the message SMS")
            return False
        
        return True
    
    def send_sms_with_loading(self, phone_number, message):
        """ส่ง SMS พร้อม loading dialog"""
        try:
            # เข้ารหัสข้อความ
            phone_hex = encode_text_to_ucs2(phone_number)
            msg_ucs2 = encode_text_to_ucs2(message)
            
            if hasattr(self.parent, '_is_sending_sms'):
                self.parent._is_sending_sms = True

            # ส่งคำสั่ง AT ตามลำดับ
            self._send_at_command_with_progress('AT+CMGF=1', "เชื่อมต่อกับ Modem...")
            import time
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
            self.parent.serial_thread.send_raw(msg_ucs2.encode() + bytes([26]))
            if hasattr(self.parent, 'update_at_command_display'):
                self.parent.update_at_command_display(f"SMS Content: {message}")

            # บันทึก log
            self._save_sms_to_log(phone_number, message)
            
            # แสดงผลสำเร็จ
            if hasattr(self.parent, 'loading_widget'):
                self.parent.loading_widget.complete_sending_success()

        except Exception as e:
            error_msg = f"There was an error sending SMS: {e}"
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(error_msg)
            QMessageBox.critical(self.parent, "Error", error_msg)
            
            if hasattr(self.parent, '_is_sending_sms'):
                self.parent._is_sending_sms = False

            # บันทึก log ที่ล้มเหลว
            from services.sms_log import log_sms_sent
            log_sms_sent(phone_number, message, status=f"ล้มเหลว: {e}")

            if hasattr(self.parent, 'loading_widget'):
                self.parent.loading_widget.complete_sending_error(str(e))
    
    def _send_at_command_with_progress(self, command, status_text):
        """ส่งคำสั่ง AT พร้อมอัพเดท loading status"""
        if hasattr(self.parent, 'loading_widget'):
            self.parent.loading_widget.update_status(status_text)
        
        if hasattr(self.parent, 'serial_thread'):
            self.parent.serial_thread.send_command(command)
        
        if hasattr(self.parent, 'update_at_command_display'):
            self.parent.update_at_command_display(command)
    
    def _save_sms_to_log(self, phone_number, message):
        """บันทึก SMS ที่ส่งไปในรูปแบบ log"""
        try:
            from services.sms_log import append_sms_log
            append_sms_log("sms_sent_log.csv", phone_number, message, "Sent")
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[Log Saved] SMS sent recorded.")
        except Exception as e:
            print(f"Error saving SMS log: {e}")
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[Log Error] Failed to save: {e}")
    
    def _show_no_sim_error(self, phone_number, message):
        """แสดง error เมื่อไม่มี SIM"""
        if hasattr(self.parent, 'show_loading_dialog'):
            self.parent.show_loading_dialog()
            QTimer.singleShot(100, lambda: self.parent.loading_widget.complete_sending_error("ไม่มีซิมในระบบ"))
        
        from services.sms_log import log_sms_sent
        log_sms_sent(phone_number, message, status="ล้มเหลว: ไม่มีซิมในระบบ")