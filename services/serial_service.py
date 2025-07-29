from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
import serial
import time
import re
from collections import deque

class SerialMonitorThread(QThread):
    new_sms_signal = pyqtSignal(str)
    at_response_signal = pyqtSignal(str)
    sim_failure_detected = pyqtSignal()
    sim_ready_signal = pyqtSignal()
    cpin_status_signal = pyqtSignal(str)
    cpin_ready_detected = pyqtSignal()
    
    def __init__(self, port, baudrate):
        super().__init__()
        self.setTerminationEnabled(True)
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.cmt_buffer = None
        
        # ตัวแปรสำหรับ CPIN polling
        self.cpin_polling_active = False
        self.cpin_poll_count = 0
        self.max_cpin_polls = 3
        self.cpin_poll_interval = 2000
        
        # ตัวแปรสำหรับ SIM recovery - ทำความสะอาด
        self.recovery_active = False
        self.recovery_queue = deque()
        self.recovery_step = 0
        self.recovery_completed_steps = set()  # เก็บ step ที่เสร็จแล้ว

        # Timer สำหรับ CPIN polling
        self.cpin_timer = QTimer()
        self.cpin_timer.timeout.connect(self.check_cpin_status)
        self.cpin_timer.setSingleShot(True)
        
    def run(self):
        """Main thread loop"""
        self.running = True
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            self.at_response_signal.emit(f"[SETUP] Connected to {self.port} at {self.baudrate} baud.")

            while self.running:
                if self.serial_conn and self.serial_conn.in_waiting:
                    try:
                        line = self.serial_conn.readline().decode(errors='ignore').strip()
                        if line:
                            self.process_received_line(line)
                    except Exception as e:
                        self.at_response_signal.emit(f"[READ ERROR] {str(e)}")
                
                # ประมวลผล recovery queue
                self.process_recovery_queue()
                
                time.sleep(0.1)
                
        except serial.SerialException as e:
            self.at_response_signal.emit(f"[FATAL] Cannot open port {self.port}: {str(e)}")
        except Exception as e:
            self.at_response_signal.emit(f"[ERROR] {str(e)}")
        finally:
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None
    
    def process_received_line(self, line):
        """ประมวลผลข้อมูลที่รับมา - ทำความสะอาด"""
        
        # ตรวจสอบ recovery response
        if self.recovery_active:
            recovery_handled = self.handle_recovery_response(line)
            if recovery_handled:
                return
        
        # ตรวจสอบ CPIN response
        if "CPIN:" in line:
            self.handle_cpin_response(line)
            return
        
        # ตรวจสอบ SMS notifications
        if line.startswith("+CMTI:"):
            self.new_sms_signal.emit(line)
            return
        
        if line.startswith("+CMT:"):
            self.cmt_buffer = line
            return
        
        if self.cmt_buffer:
            header = self.cmt_buffer
            body = line
            self.cmt_buffer = None
            self.process_sms_message(header, body)
            return
        
        # ตรวจสอบ SIM failure
        if any(keyword in line.upper() for keyword in ["SIM NOT INSERTED", "SIM FAILURE", "SIM ERROR", "+SIMCARD: NOT AVAILABLE"]):
            self.sim_failure_detected.emit()
            return
        
        # ส่งข้อมูลทั่วไปไปยัง UI
        if line.strip():
            self.at_response_signal.emit(line)
    
    def handle_recovery_response(self, line):
        """จัดการ response ของ recovery - แสดงเฉพาะที่จำเป็น"""
        line_upper = line.upper().strip()
        
        # แสดงเฉพาะข้อความที่ต้องการ
        if line_upper == "OK":
            return True  # ไม่แสดง OK
        elif "ERROR" in line_upper:
            return True  # ไม่แสดง ERROR
        elif "+CPIN:" in line_upper:
            # จัดการ CPIN response แยกต่างหาก
            return False  # ส่งต่อไปให้ handle_cpin_response
        else:
            # แสดงเฉพาะข้อความที่กำหนด
            show_messages = ["SMS DONE", "PB DONE", "AT+CFUN=0", "AT+CFUN=1", "AT+CPIN?"]
            if any(msg in line for msg in show_messages):
                self.at_response_signal.emit(f"[RECOVERY] {line}")
                return True
            
        return True
    
    def process_recovery_queue(self):
        """ประมวลผล recovery queue - ไม่แสดงข้อความเพิ่มเติม"""
        if not self.recovery_active or len(self.recovery_queue) == 0:
            return
        
        # ดึงคำสั่งถัดไปจาก queue
        command_info = self.recovery_queue.popleft()
        command = command_info['command']
        step = command_info['step']
        delay = command_info.get('delay', 0)
        
        # รอตาม delay ที่กำหนด
        if delay > 0:
            time.sleep(delay)
        
        # ส่งคำสั่งโดยไม่แสดงข้อความ
        self.recovery_step = step
        success = self.send_command_silent(command)  # ใช้ silent version
        
        if not success:
            self._recovery_failed(f"Failed to send {command}")
    
    def send_command_silent(self, command):
        """ส่งคำสั่ง AT แบบเงียบ - ไม่แสดง [SENT]"""
        if self.serial_conn and self.running:
            try:
                cmd_bytes = f"{command}\r\n".encode()
                self.serial_conn.write(cmd_bytes)
                self.serial_conn.flush()
                return True
            except Exception as e:
                self.at_response_signal.emit(f"[SEND ERROR] {e}")
                return False
        else:
            return False
    
    def handle_cpin_response(self, line):
        """จัดการ CPIN response - แสดงเฉพาะผลลัพธ์"""
        
        if "CPIN: READY" in line.upper():
            self.stop_cpin_polling()
            
            # ถ้าอยู่ในโหมด recovery
            if self.recovery_active:
                self.recovery_active = False
                self.recovery_queue.clear()
                self.recovery_step = 0
                self.recovery_completed_steps.clear()
                self.at_response_signal.emit("[RECOVERY] Complete - SIM is ready!")
            else:
                self.at_response_signal.emit("[CPIN] SIM Ready")
            
            self.cpin_status_signal.emit("READY")
            self.sim_ready_signal.emit()
            self.cpin_ready_detected.emit()
            
        elif "CPIN: SIM PIN" in line.upper():
            self.stop_cpin_polling()
            
            if self.recovery_active:
                self.recovery_active = False
                self.recovery_queue.clear()
                self.recovery_step = 0
                self.recovery_completed_steps.clear()
                self.at_response_signal.emit("[RECOVERY] Failed - PIN required")
            
            self.cpin_status_signal.emit("PIN_REQUIRED")
            
        elif "CPIN: SIM PUK" in line.upper():
            self.stop_cpin_polling()
            
            if self.recovery_active:
                self.recovery_active = False
                self.recovery_queue.clear()
                self.recovery_step = 0
                self.recovery_completed_steps.clear()
                self.at_response_signal.emit("[RECOVERY] Failed - PUK required")
            
            self.cpin_status_signal.emit("PUK_REQUIRED")
    
    def start_cpin_polling(self):
        """เริ่ม CPIN polling"""
        if not self.cpin_polling_active:
            self.cpin_polling_active = True
            self.cpin_poll_count = 0
            self.check_cpin_status()
    
    def check_cpin_status(self):
        """ตรวจสอบสถานะ CPIN"""
        if not self.running or not self.cpin_polling_active:
            return
            
        self.cpin_poll_count += 1
        
        if self.cpin_poll_count > self.max_cpin_polls:
            self.stop_cpin_polling()
            return
        
        try:
            self.send_command("AT+CPIN?")
            
            if self.cpin_polling_active:
                self.cpin_timer.start(self.cpin_poll_interval)
                
        except Exception as e:
            self.at_response_signal.emit(f"[CPIN ERROR] {e}")
            self.stop_cpin_polling()
    
    def stop_cpin_polling(self):
        """หยุด CPIN polling"""
        self.cpin_polling_active = False
        if self.cpin_timer:
            self.cpin_timer.stop()
    
    def process_sms_message(self, header, body):
        """ประมวลผล SMS message"""
        try:
            parts = [p.strip().strip('"') for p in header.split(",")]
            sender = parts[0].split(" ", 1)[1] if len(parts) > 0 else "Unknown"
            timestamp = parts[-1] if len(parts) > 0 else "Unknown time"
            
            self.new_sms_signal.emit(f"{sender}|{body}|{timestamp}")
            
        except Exception as e:
            self.at_response_signal.emit(f"[SMS ERROR] {e}")
    
    def send_command(self, command):
        """ส่งคำสั่ง AT - แสดง [SENT] เฉพาะตอนไม่ recovery"""
        if self.serial_conn and self.running:
            try:
                cmd_bytes = f"{command}\r\n".encode()
                self.serial_conn.write(cmd_bytes)
                self.serial_conn.flush()
                
                # แสดง [SENT] เฉพาะตอนไม่ recovery
                if not self.recovery_active:
                    self.at_response_signal.emit(f"[SENT] {command}")
                
                return True
            except Exception as e:
                self.at_response_signal.emit(f"[SEND ERROR] {e}")
                return False
        else:
            self.at_response_signal.emit(f"[SEND ERROR] No serial connection available")
            return False
    
    def send_raw(self, data):
        """ส่งข้อมูลดิบ"""
        if self.serial_conn and self.running:
            try:
                self.serial_conn.write(data)
                self.serial_conn.flush()
                return True
            except Exception as e:
                self.at_response_signal.emit(f"[SEND RAW ERROR] {e}")
                return False
        return False
    
    def force_sim_recovery(self):
        """บังคับ SIM recovery - แสดงข้อความเริ่มต้นเท่านั้น"""
        self.at_response_signal.emit("[RECOVERY] Starting SIM recovery...")
        
        # ล้าง queue และ state เดิม
        self.recovery_queue.clear()
        self.recovery_completed_steps.clear()
        self.recovery_active = True
        self.recovery_step = 0
        self.stop_cpin_polling()
        
        # เพิ่มคำสั่งลง queue
        self.recovery_queue.append({
            'command': 'AT+CFUN=0',
            'step': 1,
            'delay': 0
        })
        
        self.recovery_queue.append({
            'command': 'AT+CFUN=1', 
            'step': 2,
            'delay': 2
        })
        
        self.recovery_queue.append({
            'command': 'AT+CPIN?',
            'step': 3, 
            'delay': 4
        })
    
    def _recovery_failed(self, reason):
        """จัดการเมื่อ recovery ล้มเหลว""" 
        self.recovery_active = False
        self.recovery_queue.clear()
        self.recovery_completed_steps.clear()
        self.recovery_step = 0
        self.at_response_signal.emit(f"[RECOVERY] ❌ Failed: {reason}")
    
    def stop(self):
        """หยุดการทำงาน"""
        self.running = False
        self.stop_cpin_polling()
        self.recovery_active = False
        self.recovery_queue.clear()
        self.recovery_completed_steps.clear()
            
        if self.isRunning():
            self.wait(3000)
    
    def cleanup(self):
        """ทำความสะอาด"""
        self.running = False
        self.stop_cpin_polling()
        self.recovery_active = False
        self.recovery_queue.clear()
        self.recovery_completed_steps.clear()
        
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None