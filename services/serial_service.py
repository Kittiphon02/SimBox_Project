from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
import serial
import time
import re

class SerialMonitorThread(QThread):
    new_sms_signal = pyqtSignal(str)
    at_response_signal = pyqtSignal(str)
    sim_failure_detected = pyqtSignal()
    sim_ready_signal = pyqtSignal()  # ใหม่: สัญญาณเมื่อ SIM พร้อม
    cpin_status_signal = pyqtSignal(str)  # ใหม่: สัญญาณสถานะ CPIN
    cpin_ready_detected = pyqtSignal()  # เพิ่ม signal ใหม่
    
    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.cmt_buffer = None
        
        # ตัวแปรสำหรับ CPIN polling
        self.cpin_polling_active = False
        self.cpin_poll_count = 0
        self.max_cpin_polls = 3  # 3 ครั้ง
        self.cpin_poll_interval = 2000  # 2 วินาทีต่อครั้ง
        
        # ตัวแปรสำหรับ SIM recovery tracking
        self.recovery_step = 0  # เพิ่มตัวแปรติดตาม recovery step
        self.manual_recovery_mode = False  # เพิ่มโหมด manual recovery
        
        # Timer สำหรับ CPIN polling
        self.cpin_timer = QTimer()
        self.cpin_timer.timeout.connect(self.check_cpin_status)
        self.cpin_timer.setSingleShot(True)
        
        # ย้าย timer ไปยัง main thread
        self.cpin_timer.moveToThread(self.thread())
        
    def run(self):
        """Main thread loop"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            
            # เริ่ม CPIN polling ทันที (ยกเว้นเมื่ออยู่ใน manual recovery mode)
            if not self.manual_recovery_mode:
                self.start_cpin_polling()
            
            while self.running:
                try:
                    if self.serial.in_waiting > 0:
                        line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.process_received_line(line)
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    if self.running:
                        self.at_response_signal.emit(f"[SERIAL ERROR] {e}")
                    
        except Exception as e:
            self.at_response_signal.emit(f"[CONNECTION ERROR] {e}")
        finally:
            self.cleanup()
    
    def start_cpin_polling(self):
        """เริ่ม CPIN polling"""
        if not self.cpin_polling_active:
            self.cpin_polling_active = True
            self.cpin_poll_count = 0
            
            # ส่งคำสั่ง CPIN ครั้งแรก
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
            # ส่งคำสั่ง AT+CPIN?
            self.send_command("AT+CPIN?")
            
            # รอ response และตั้งเวลาสำหรับการตรวจสอบครั้งถัดไป
            if self.cpin_polling_active:
                self.cpin_timer.start(self.cpin_poll_interval)
                
        except Exception as e:
            self.at_response_signal.emit(f"[CPIN ERROR] {e}")
            self.stop_cpin_polling()
    
    def stop_cpin_polling(self):
        """หยุด CPIN polling"""
        self.cpin_polling_active = False
        self.cpin_timer.stop()
    
    def process_received_line(self, line):
        """ประมวลผลข้อมูลที่รับมา"""
        
        # ตรวจสอบ recovery steps (เพิ่มส่วนนี้)
        if self.recovery_step > 0:
            self.handle_recovery_response(line)
        
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
            # ประมวลผล SMS body
            header = self.cmt_buffer
            body = line
            self.cmt_buffer = None
            self.process_sms_message(header, body)
            return
        
        # ตรวจสอบ SIM failure
        if any(keyword in line.upper() for keyword in ["SIM NOT INSERTED", "SIM FAILURE", "SIM ERROR"]):
            self.sim_failure_detected.emit()
            return
        
        # ส่งข้อมูลทั่วไปไปยัง UI
        if line.strip():
            self.at_response_signal.emit(line)
    
    def handle_recovery_response(self, line):
        """จัดการ response ในระหว่าง recovery (เพิ่มฟังก์ชันใหม่)"""
        if "OK" in line and self.recovery_step > 0:
            if self.recovery_step == 1:  # หลัง AT+CFUN=0
                self.recovery_step = 2
                self.at_response_signal.emit("[SIM RECOVERY] Step 2: Enabling modem...")
                # รอ 1 วินาทีแล้วส่ง AT+CFUN=1
                QTimer.singleShot(1000, lambda: self.send_command("AT+CFUN=1"))
                
            elif self.recovery_step == 2:  # หลัง AT+CFUN=1
                self.recovery_step = 3
                self.at_response_signal.emit("[SIM RECOVERY] Step 3: Checking SIM status...")
                # รอ 3 วินาทีแล้วส่ง AT+CPIN?
                QTimer.singleShot(3000, lambda: self.send_command("AT+CPIN?"))
                
            elif self.recovery_step == 3:  # หลัง AT+CPIN?
                # รอ CPIN response ใน handle_cpin_response
                pass
    
    def handle_cpin_response(self, line):
        """จัดการ CPIN response (ลด messages)"""
        
        # ตรวจสอบสถานะ CPIN
        if "CPIN: READY" in line.upper():
            self.stop_cpin_polling()
            self.at_response_signal.emit("[CPIN] ✅ SIM Ready")
            self.cpin_status_signal.emit("READY")
            self.sim_ready_signal.emit()
            self.cpin_ready_detected.emit()
            
            # ถ้าอยู่ในโหมด recovery ให้จบ recovery
            if self.recovery_step > 0:
                self.recovery_step = 0
                self.manual_recovery_mode = False
                self.at_response_signal.emit("[RECOVERY] ✅ Complete")
            
        elif "CPIN: SIM PIN" in line.upper():
            self.stop_cpin_polling()
            self.at_response_signal.emit("[CPIN] ⚠️ PIN required")
            self.cpin_status_signal.emit("PIN_REQUIRED")
            
        elif "CPIN: SIM PUK" in line.upper():
            self.stop_cpin_polling()
            self.at_response_signal.emit("[CPIN] ❌ PUK required")
            self.cpin_status_signal.emit("PUK_REQUIRED")
            
        elif "ERROR" in line.upper():
            # ไม่แสดงข้อความ error ของ CPIN เพราะเป็นเรื่องปกติ
            pass
    
    def process_sms_message(self, header, body):
        """ประมวลผล SMS message"""
        try:
            # แยกข้อมูลจาก header
            parts = [p.strip().strip('"') for p in header.split(",")]
            sender = parts[0].split(" ", 1)[1] if len(parts) > 0 else "Unknown"
            timestamp = parts[-1] if len(parts) > 0 else "Unknown time"
            
            # ส่งสัญญาณ SMS ใหม่
            self.new_sms_signal.emit(f"{sender}|{body}|{timestamp}")
            
        except Exception as e:
            self.at_response_signal.emit(f"[SMS ERROR] {e}")
    
    def send_command(self, command):
        """ส่งคำสั่ง AT"""
        if self.serial and self.running:
            try:
                self.serial.write(f"{command}\r\n".encode())
                self.serial.flush()
            except Exception as e:
                self.at_response_signal.emit(f"[SEND ERROR] {e}")
    
    def send_raw(self, data):
        """ส่งข้อมูลดิบ"""
        if self.serial and self.running:
            try:
                self.serial.write(data)
                self.serial.flush()
            except Exception as e:
                self.at_response_signal.emit(f"[SEND RAW ERROR] {e}")
    
    def force_sim_recovery(self):
        """บังคับ SIM recovery (ปรับปรุงใหม่)"""
        self.at_response_signal.emit("[SIM RECOVERY] Starting forced recovery...")
        self.manual_recovery_mode = True
        self.recovery_step = 1
        self.stop_cpin_polling()  # หยุด polling ปกติ
        
        self.at_response_signal.emit("[SIM RECOVERY] Step 1: Disabling modem...")
        self.send_command("AT+CFUN=0")
    
    def stop(self):
        """หยุดการทำงาน"""
        self.running = False
        self.stop_cpin_polling()
        self.wait()
    
    def cleanup(self):
        """ทำความสะอาด"""
        self.running = False
        self.stop_cpin_polling()
        
        if self.serial:
            try:
                self.serial.close()
            except:
                pass
            self.serial = None