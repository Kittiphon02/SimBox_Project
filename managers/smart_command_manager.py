# managers/smart_command_manager.py - Enhanced version with Signal Quality filtering
# 🧠 Smart Command Manager สำหรับจัดการ AT Commands อย่างชาญฉลาด + กรองข้อมูล Signal Quality

import time
import queue
from enum import Enum
from PyQt5.QtCore import QTimer
from collections import deque

class CommandPriority(Enum):
    """🔧 ระดับความสำคัญของคำสั่ง"""
    CRITICAL = 0   # User commands จากหน้าหลัก
    HIGH = 1       # SMS sending/receiving
    MEDIUM = 2     # SIM recovery, Manual refresh  
    LOW = 3        # Background monitoring (Signal Quality)

class CommandSource(Enum):
    """🔧 แหล่งที่มาของคำสั่ง"""
    USER_MAIN = "user_main"           # จากหน้าหลัก
    SMS_SEND = "sms_send"             # ส่ง SMS
    SMS_MONITOR = "sms_monitor"       # Monitor SMS
    SIGNAL_QUALITY = "signal_quality" # Signal Quality Checker
    SIM_RECOVERY = "sim_recovery"     # SIM Recovery
    BACKGROUND = "background"         # Background tasks

class SmartCommandManager:
    """
    🧠 จัดการคำสั่ง AT อย่างชาญฉลาด
    ✅ ใช้ Response ในหน้าหลักได้ปกติ
    ✅ ส่ง AT command ได้ปกติ
    ✅ ไม่ชนกันระหว่าง modules
    ✅ ซ่อนข้อมูล Signal Quality จาก Response area
    """
    
    def __init__(self, serial_thread):
        self.serial_thread = serial_thread
        self.command_queue = deque()
        self.is_processing = False
        self.last_command_time = 0
        self.min_interval = 0.1  # วินาที
        
        # 🔧 ติดตาม module ที่ใช้งาน
        self.active_modules = set()
        self.user_command_active = False
        self.signal_quality_active = False
        self.sms_sending_active = False
        
        # 🔧 ติดตาม commands ที่ไม่ต้องแสดงใน UI
        self.silent_commands = set()
        self.background_responses = set()
        
        # 🆕 เพิ่มการกรอง Signal Quality
        self.signal_quality_commands = set()
        self.signal_quality_patterns = {
            'AT+CSQ', 'AT+CESQ', 'AT+COPS', 'AT+CREG', 
            'AT+CIMI', 'AT+CCID', 'AT+CNUM', 'AT+QCSQ',
            'AT+QENG', 'AT+QNWINFO'
        }
        self.signal_quality_responses = {
            '+CSQ:', '+CESQ:', '+COPS:', '+CREG:', 
            '+CIMI:', '+CCID:', '+CNUM:', '+QCSQ:',
            '+QENG:', '+QNWINFO:'
        }
        
        # Timer สำหรับประมวลผล queue
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_queue)
        self.process_timer.start(50)  # ทุก 50ms
        
        # Hook เข้า serial thread เดิม
        self._hook_serial_thread()
    
    def _hook_serial_thread(self):
        """🔗 เชื่อมต่อเข้า serial thread เดิม"""
        if self.serial_thread:
            # เก็บ method เดิม
            self.original_send_command = self.serial_thread.send_command
            self.original_process_line = getattr(self.serial_thread, 'process_received_line', None)
            
            # แทนที่ด้วย smart version
            self.serial_thread.send_command_smart = self.smart_send_command
            
            # เชื่อมต่อ response processing
            if hasattr(self.serial_thread, 'at_response_signal'):
                self.serial_thread.at_response_signal.connect(self.smart_process_response)
    
    def register_module(self, module_name: str):
        """📝 ลงทะเบียน module ที่ใช้งาน"""
        self.active_modules.add(module_name)
        
        if module_name == "signal_quality":
            self.signal_quality_active = True
        elif module_name == "sms_sending":
            self.sms_sending_active = True
    
    def unregister_module(self, module_name: str):
        """❌ ยกเลิกการลงทะเบียน module"""
        self.active_modules.discard(module_name)
        
        if module_name == "signal_quality":
            self.signal_quality_active = False
        elif module_name == "sms_sending":
            self.sms_sending_active = False
    
    def smart_send_command(self, command: str, source: CommandSource = CommandSource.USER_MAIN, 
                          priority: CommandPriority = CommandPriority.CRITICAL, silent: bool = False):
        """
        🧠 ส่งคำสั่ง AT อย่างชาญฉลาด
        
        Args:
            command: คำสั่ง AT
            source: แหล่งที่มาของคำสั่ง  
            priority: ระดับความสำคัญ
            silent: ไม่แสดง [SENT] และบาง response ใน UI
        """
        
        # 🆕 ตรวจสอบว่าเป็น Signal Quality command หรือไม่
        if self._is_signal_quality_command(command):
            source = CommandSource.SIGNAL_QUALITY
            priority = CommandPriority.LOW
            silent = True
            self.signal_quality_commands.add(command.upper().strip())
        
        # 🔧 ตรวจสอบว่าควรส่งทันทีหรือใส่ queue
        if self._should_send_immediately(source, priority):
            return self._execute_command_now(command, source, silent)
        else:
            self._add_to_queue(command, source, priority, silent)
            return True
    
    def _is_signal_quality_command(self, command: str) -> bool:
        """🔍 ตรวจสอบว่าเป็นคำสั่งจาก Signal Quality Checker หรือไม่"""
        cmd_upper = command.upper().strip()
        
        # ตรวจสอบ pattern ที่ตรงกันทั้งหมด
        for pattern in self.signal_quality_patterns:
            if cmd_upper.startswith(pattern):
                return True
        
        return False
    
    def _should_send_immediately(self, source: CommandSource, priority: CommandPriority) -> bool:
        """🤔 ตัดสินใจว่าควรส่งทันทีหรือไม่"""
        
        current_time = time.time()
        
        # ✅ User commands จากหน้าหลักส่งทันที
        if source == CommandSource.USER_MAIN:
            self.user_command_active = True
            return True
        
        # ✅ SMS sending มี priority สูง
        if source == CommandSource.SMS_SEND and priority <= CommandPriority.HIGH:
            return True
        
        # ✅ Signal Quality commands ส่งได้เสมอแต่เป็น background
        if source == CommandSource.SIGNAL_QUALITY:
            return True
        
        # ✅ ถ้าไม่มีคำสั่งในคิว และผ่านเวลาขั้นต่ำแล้ว
        if (len(self.command_queue) == 0 and 
            current_time - self.last_command_time >= self.min_interval):
            return True
        
        # ✅ ถ้าไม่มี user command กำลังรอ และเป็นคำสั่งสำคัญ
        if not self.user_command_active and priority <= CommandPriority.MEDIUM:
            return True
        
        return False
    
    def _execute_command_now(self, command: str, source: CommandSource, silent: bool) -> bool:
        """⚡ ส่งคำสั่งทันที"""
        try:
            # 🔧 จัดการ silent mode
            if silent or source == CommandSource.SIGNAL_QUALITY:
                self.silent_commands.add(command.upper().strip())
            
            # ✅ ส่งคำสั่งผ่าน method เดิม
            success = self.original_send_command(command)
            
            if success:
                self.last_command_time = time.time()
                
                # รีเซ็ต user command flag หลังส่งเสร็จ
                if source == CommandSource.USER_MAIN:
                    QTimer.singleShot(2000, self._reset_user_command_flag)
            
            return success
            
        except Exception as e:
            print(f"Error executing command: {e}")
            return False
    
    def _add_to_queue(self, command: str, source: CommandSource, priority: CommandPriority, silent: bool):
        """📥 เพิ่มคำสั่งเข้า queue"""
        command_info = {
            'command': command,
            'source': source,
            'priority': priority,
            'silent': silent,
            'timestamp': time.time()
        }
        
        # เรียงตามความสำคัญ
        inserted = False
        for i, existing in enumerate(self.command_queue):
            if priority.value < existing['priority'].value:
                self.command_queue.insert(i, command_info)
                inserted = True
                break
        
        if not inserted:
            self.command_queue.append(command_info)
    
    def _process_queue(self):
        """⚙️ ประมวลผล command queue"""
        if not self.command_queue or self.is_processing:
            return
        
        current_time = time.time()
        
        # ตรวจสอบว่าพร้อมส่งคำสั่งหรือไม่
        if current_time - self.last_command_time < self.min_interval:
            return
        
        # ดึงคำสั่งที่มีความสำคัญสูงสุด
        command_info = self.command_queue.popleft()
        
        # ตรวจสอบอีกครั้งว่าควรส่งหรือไม่
        if self._should_send_immediately(command_info['source'], command_info['priority']):
            self.is_processing = True
            success = self._execute_command_now(
                command_info['command'], 
                command_info['source'], 
                command_info['silent']
            )
            self.is_processing = False
            
            if not success:
                # ถ้าส่งไม่สำเร็จ ใส่กลับเข้าคิว
                self.command_queue.appendleft(command_info)
        else:
            # ใส่กลับเข้าคิว
            self.command_queue.appendleft(command_info)
    
    def smart_process_response(self, line: str):
        """🔍 ประมวลผลข้อมูลที่ได้รับอย่างชาญฉลาด - กรอง Signal Quality responses"""
        
        # ✅ ตรวจสอบว่าเป็น response จาก Signal Quality หรือไม่
        if self._is_signal_quality_response(line):
            self._handle_signal_quality_response(line)
            return  # ไม่ส่งต่อไป UI หลัก
        
        # ✅ ตรวจสอบว่าเป็น response จาก silent command หรือไม่
        if self._is_silent_response(line):
            self._handle_silent_response(line)
            return
        
        # ✅ ส่งต่อไป UI ปกติเฉพาะข้อมูลที่จำเป็น
        if hasattr(self.serial_thread, 'parent') and hasattr(self.serial_thread.parent, 'update_at_result_display'):
            self.serial_thread.parent.update_at_result_display(line)
    
    def _is_signal_quality_response(self, line: str) -> bool:
        """🔍 ตรวจสอบว่าเป็น response จาก Signal Quality หรือไม่"""
        line_upper = line.strip().upper()
        
        # ตรวจสอบ response patterns
        for pattern in self.signal_quality_responses:
            if line_upper.startswith(pattern):
                return True
        
        # ตรวจสอบ OK/ERROR หลัง Signal Quality commands
        if line_upper in ['OK', 'ERROR'] and self.signal_quality_commands:
            # ล้าง signal quality commands เมื่อได้ OK/ERROR
            self.signal_quality_commands.clear()
            return True
        
        return False
    
    def _handle_signal_quality_response(self, line: str):
        """📶 จัดการ response จาก Signal Quality - ไม่แสดงใน UI หลัก"""
        # ส่งไปยัง Signal Quality Window โดยตรง
        self._notify_signal_quality_modules(line)
        
        # บันทึก log สำหรับ debug (ถ้าต้องการ)
        print(f"[SIGNAL QUALITY] {line}")
    
    def _is_silent_response(self, line: str) -> bool:
        """🤔 ตรวจสอบว่าเป็น response จาก silent command หรือไม่"""
        
        # ถ้าเพิ่งมี user command ให้แสดงทุก response
        if self.user_command_active:
            return False
        
        # ตรวจสอบ pattern จาก background commands (ไม่ใช่ Signal Quality)
        silent_patterns = [
            r'\+COPS:\s*\d+,\d+,"[^"]*"', # Operator selection (non-Signal Quality)
        ]
        
        import re
        for pattern in silent_patterns:
            if re.search(pattern, line):
                return True
        
        # ตรวจสอบ OK/ERROR หลัง silent commands (ไม่ใช่ Signal Quality)
        if line.strip().upper() in ['OK', 'ERROR'] and self.silent_commands and not self.signal_quality_commands:
            self.silent_commands.clear()
            return True
        
        return False
    
    def _handle_silent_response(self, line: str):
        """🤫 จัดการ silent response"""
        # บันทึก response สำหรับ modules ที่ต้องการ
        self.background_responses.add(line)
        print(f"[SILENT] {line}")
    
    def _notify_signal_quality_modules(self, line: str):
        """📶 แจ้ง Signal Quality modules"""
        # ส่งข้อมูลไปยัง Signal Quality Window ถ้าเปิดอยู่
        if hasattr(self, 'signal_quality_window') and self.signal_quality_window:
            try:
                # ส่งข้อมูลไป Signal Quality Window
                if hasattr(self.signal_quality_window, '_process_signal_data'):
                    self.signal_quality_window._process_signal_data(line)
                elif hasattr(self.signal_quality_window, 'monitoring_thread'):
                    # ส่งไปยัง monitoring thread
                    pass
            except Exception as e:
                print(f"Error notifying Signal Quality: {e}")
    
    def _reset_user_command_flag(self):
        """🔄 รีเซ็ต user command flag"""
        self.user_command_active = False
    
    def register_signal_quality_window(self, window):
        """📶 ลงทะเบียน Signal Quality Window"""
        self.signal_quality_window = window
        print("Signal Quality Window registered with SmartCommandManager")
    
    def unregister_signal_quality_window(self):
        """📶 ยกเลิกการลงทะเบียน Signal Quality Window"""
        self.signal_quality_window = None
        print("Signal Quality Window unregistered from SmartCommandManager")
    
    def get_status(self) -> dict:
        """📊 ดูสถานะปัจจุบัน"""
        return {
            'active_modules': list(self.active_modules),
            'queue_size': len(self.command_queue),
            'user_command_active': self.user_command_active,
            'signal_quality_active': self.signal_quality_active,
            'sms_sending_active': self.sms_sending_active,
            'signal_quality_commands': len(self.signal_quality_commands),
            'last_command_time': self.last_command_time
        }