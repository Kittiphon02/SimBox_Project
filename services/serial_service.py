# serial_service.py - FIXED VERSION

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

    connected_signal = pyqtSignal(str, int)   # (port, baudrate)
    disconnected_signal = pyqtSignal()        # no args
    
    def __init__(self, port, baudrate):
        super().__init__()
        
        self.setTerminationEnabled(True)
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.cmt_buffer = None

        # เพิ่มตัวแปรติดตาม background commands
        self.last_command_was_background = False
        
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

        # เพิ่มตัวแปรเก็บแหล่งที่มาของคำสั่ง
        self.command_source = None  # 'MANUAL', 'SIGNAL_QUALITY', 'BACKGROUND'
        self.command_source_queue = deque(maxlen=10)

        connected_signal = pyqtSignal(str, int)   # (port, baud)
        disconnected_signal = pyqtSignal()        # no args
        
    def set_command_source(self, source):
        """กำหนดแหล่งที่มาของคำสั่ง"""
        self.command_source = source
        self.command_source_queue.append(source)

    def run(self):
        """เปิดพอร์ต, loop อ่าน, และเดินคิวกู้ซิมทุก ๆ รอบ"""
        self.running = True
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            self.at_response_signal.emit(f"[SETUP] Connected to {self.port} at {self.baudrate} baud.")
            self.connected_signal.emit(self.port, self.baudrate)

            # เคลียร์บัฟเฟอร์ SMS แบบ 2 บรรทัด
            self.cmt_buffer = None

            # ตัวคิว/แฟล็กที่อาจยังไม่ถูกตั้งจากภายนอก
            if not hasattr(self, "recovery_active"):
                self.recovery_active = False
            if not hasattr(self, "command_source_queue"):
                from collections import deque
                self.command_source_queue = deque()

            while self.running:
                # ── เดินคิวกู้ซิมทุก ๆ รอบ ──────────────────────────────
                try:
                    self.process_recovery_queue()
                except Exception as e:
                    # กันพังเงียบ ๆ เพื่อไม่ให้ loop หลุด
                    self.at_response_signal.emit(f"[RECOVERY LOOP ERROR] {e}")

                # ── อ่านข้อมูลจากพอร์ต ─────────────────────────────────
                if self.serial_conn and self.serial_conn.in_waiting:
                    try:
                        line = self.serial_conn.readline().decode(errors="ignore").strip()
                        if line:
                            self.process_received_line(line)
                    except Exception as e:
                        self.at_response_signal.emit(f"[READ ERROR] {e}")

                time.sleep(0.1)

        except serial.SerialException as e:
            self.at_response_signal.emit(f"[FATAL] Cannot open port {self.port}: {e}")
        except Exception as e:
            self.at_response_signal.emit(f"[ERROR] {e}")
        finally:
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except Exception:
                    pass
                self.serial_conn = None
            self.disconnected_signal.emit()
    
    def process_received_line(self, line: str):
        """ประมวลผลข้อความที่อ่านได้จากพอร์ต"""
        if not line:
            return

        up = line.upper().strip()

        # ── จับ SMS แบบ notify ────────────────────────────────────────
        if up.startswith("+CMTI:"):
            # แจ้ง UI และจบ
            self.new_sms_signal.emit(line)
            self.at_response_signal.emit(line)
            return

        # ── จับ SMS แบบ 2 บรรทัด (+CMT: header → บรรทัดถัดไปเป็น body) ─
        if up.startswith("+CMT:"):
            self.cmt_buffer = line
            return
        elif getattr(self, "cmt_buffer", None):
            header = self.cmt_buffer
            self.cmt_buffer = None
            body = line
            self.new_sms_signal.emit(f"{header}|{body}")
            return

        # ── จับสถานะซิมก่อน (สำคัญ) ─────────────────────────────────
        if "+CPIN:" in up:
            # ให้ handler ตัดสินว่ากู้สำเร็จหรือไม่ (READY → ปิด recovery + init SMS)
            try:
                self.handle_cpin_response(line)
            finally:
                # ไม่ปล่อยตกไปที่ at_response_signal ซ้ำ
                return

        # ── ซ่อน ERROR จร ๆ ระหว่าง recovery หรือคำสั่งพื้นหลัง ───────
        if up == "ERROR":
            if getattr(self, "recovery_active", False):
                return
            # ดูแหล่งที่มาของคำสั่งล่าสุด (ถ้ามีการบันทึก)
            cmd_src = None
            try:
                if self.command_source_queue and isinstance(self.command_source_queue[-1], tuple):
                    cmd_src = self.command_source_queue[-1][1]
            except Exception:
                cmd_src = None
            if cmd_src in ("SIGNAL_QUALITY", "BACKGROUND"):
                return

        # ── แจ้ง SIM failure ชัดเจน ───────────────────────────────────
        if any(k in up for k in ("NO SIM", "SIM NOT INSERTED", "SIM FAILURE")):
            try:
                self.sim_failure_detected.emit()
            finally:
                # แสดงบรรทัดไว้ด้วย เผื่อ debug
                self.at_response_signal.emit(line)
                return

        # ── ระหว่าง recovery: ให้ handler ของ recovery ตัดสินใจ ──────
        if getattr(self, "recovery_active", False):
            try:
                if self.handle_recovery_response(line):
                    return  # ถูกจัดการแล้ว
            except Exception:
                # หาก handler โยน error ก็ให้ตกลงมาล็อกปกติ
                pass

        # ── บรรทัดอื่น ๆ แสดงปกติ ────────────────────────────────────
        self.at_response_signal.emit(line)

    def _is_signal_response(self, line):
        """ตรวจสอบว่าเป็น Signal Quality response หรือไม่"""
        line_upper = line.upper().strip()
        
        # Signal Quality indicators
        signal_indicators = ["+CSQ:", "+CESQ:", "+COPS:", "+CREG:", "+CIMI:", "+CCID:", "+QCCID:", "+CNUM:"]
        
        # ตรวจสอบ response patterns
        if any(indicator in line_upper for indicator in signal_indicators):
            return True
        
        # ตรวจสอบรูปแบบ CSQ response แบบเฉพาะตัวเลข เช่น "14,99"
        if re.match(r'^\d+,\d+$', line.strip()):
            return True
        
        return False

    def _determine_response_source(self, line):
        """กำหนดว่า response นี้มาจากแหล่งไหน - Enhanced version"""
        line_upper = line.upper().strip()
        
        # ตรวจสอบ SMS responses
        sms_indicators = ["+CMTI:", "+CMT:", "+CMGR:", "+CMGL:", "+CMGS:", "+CMS ERROR:"]
        if any(indicator in line_upper for indicator in sms_indicators):
            return 'SMS'
        
        # ตรวจสอบ Signal Quality responses
        if self._is_signal_response(line):
            return 'SIGNAL_QUALITY'
        
        # Default เป็น Manual
        return 'MANUAL'
    
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
        """ดึงงานชุดถัดไปจากคิวแล้วส่ง AT ตามสเต็ป"""
        if not getattr(self, "recovery_active", False):
            return
        if not getattr(self, "recovery_queue", None):
            return
        if not self.recovery_queue:
            return

        job = self.recovery_queue.popleft()
        delay = int(job.get('delay', 0)) or 0
        if delay > 0:
            time.sleep(delay)

        self.recovery_step = int(job.get('step', 0))
        ok = self.send_command_silent(job['command'])
        if not ok:
            self._recovery_failed(f"Failed to send {job['command']}")
    
    def send_command_silent(self, command: str) -> bool:
        """ส่ง AT โดยไม่สแปมขึ้นหน้าจอ (ใช้สำหรับ recovery)"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(f"{command}\r\n".encode())
                self.serial_conn.flush()
                return True
        except Exception as e:
            self.at_response_signal.emit(f"[SEND ERROR] {e}")
        return False
    
    def handle_cpin_response(self, line: str):
        u = line.upper()
        if "CPIN: READY" in u:
            # ปิดโหมด recovery แล้วประกาศสำเร็จ
            self.recovery_active = False
            self.recovery_queue.clear()
            self.recovery_step = 0
            self.recovery_completed_steps.clear()
            self.at_response_signal.emit("[RECOVERY] ✅ Complete - SIM is ready!")

            # แจ้งสัญญาณให้ UI และ init SMS stack (ถ้ามี)
            try:
                self.cpin_status_signal.emit("READY")
                self.sim_ready_signal.emit()
                self.cpin_ready_detected.emit()
            except Exception:
                pass
            try:
                # ถ้ามีเมธอดนี้ ให้ตั้ง CSCS/CMGF/CPMS/CNMI ต่อ
                self.init_sms_stack_safe()
            except Exception:
                pass
            return

        if "CPIN: SIM PIN" in u:
            self.recovery_active = False
            self.recovery_queue.clear()
            self.at_response_signal.emit("[RECOVERY] ❌ Failed - SIM PIN required")
            self.cpin_status_signal.emit("PIN_REQUIRED")
            return

        if "CPIN: SIM PUK" in u:
            self.recovery_active = False
            self.recovery_queue.clear()
            self.at_response_signal.emit("[RECOVERY] ❌ Failed - SIM PUK required")
            self.cpin_status_signal.emit("PUK_REQUIRED")
            return

        # อย่างอื่น (NOT READY ฯลฯ) ก็แค่โชว์ไว้
        self.at_response_signal.emit(line)
    
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
        """หยุดตัวจับเวลาถาม CPIN (ถ้าคุณเคยตั้ง QTimer ไว้)"""
        try:
            if getattr(self, "cpin_timer", None):
                self.cpin_timer.stop()
                self.cpin_timer = None
        except Exception:
            pass
    
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
        if self.serial_conn and self.running:
            try:
                self.serial_conn.write(f"{command}\r\n".encode()); self.serial_conn.flush()

                # ตีความแหล่งที่มาอัตโนมัติ
                if not self.command_source:
                    bg = ["AT+CSQ", "AT+CESQ", "AT+COPS", "AT+CREG", "AT+CIMI", "AT+CCID", "AT+QCCID", "AT+CNUM"]
                    self.command_source = "SIGNAL_QUALITY" if any(x in command.upper() for x in bg) else "MANUAL"

                self.command_source_queue.append((command, self.command_source))

                if self.command_source == "MANUAL":
                    self.at_response_signal.emit(f"[SENT] {command}")
                # SIGNAL_QUALITY/BACKGROUND → ไม่ spam ไปหน้าหลัก

                self.command_source = None
                return True
            except Exception as e:
                self.at_response_signal.emit(f"[SEND ERROR] {e}")
                return False
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
        """เริ่ม SIM recovery: CFUN=0 -> CFUN=1 -> CPIN? แล้วรอผล"""
        self.at_response_signal.emit("[RECOVERY] Starting SIM recovery...")

        # reset state
        try:
            self.recovery_queue.clear()
        except Exception:
            from collections import deque
            self.recovery_queue = deque()
        self.recovery_completed_steps = set()
        self.recovery_active = True
        self.recovery_step = 0
        self.stop_cpin_polling()

        # เดิน 0 -> 1 -> 2 ตามสเต็ป
        self.recovery_queue.append({'command': 'AT+CFUN=0', 'step': 1, 'delay': 0})
        self.recovery_queue.append({'command': 'AT+CFUN=1', 'step': 2, 'delay': 2})
        self.recovery_queue.append({'command': 'AT+CPIN?', 'step': 3, 'delay': 4})
    
    def _recovery_failed(self, reason):
        """จัดการเมื่อ recovery ล้มเหลว""" 
        self.recovery_active = False
        self.recovery_queue.clear()
        self.recovery_completed_steps.clear()
        self.recovery_step = 0
        self.at_response_signal.emit(f"[RECOVERY] ❌ Failed: {reason}")
    
    def stop(self):
        """หยุดเธรดและทำความสะอาด"""
        self.running = False
        try:
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None
        finally:
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