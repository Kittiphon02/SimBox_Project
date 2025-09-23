# port_manager.py
"""
จัดการพอร์ต Serial และการเชื่อมต่อ
"""

import serial
import time
from core.utility_functions import list_serial_ports
from services.sim_model import load_sim_data
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from services.serial_service import SerialMonitorThread
from PyQt5.QtWidgets import QMessageBox


class PortManager:
    """จัดการพอร์ต Serial และการเชื่อมต่อ"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def refresh_ports(self, port_combo):
        """รีเฟรชรายการพอร์ต Serial"""
        if hasattr(self.parent, 'update_at_result_display'):
            self.parent.update_at_result_display("[REFRESH] Refreshing serial ports...")
        
        current_data = port_combo.currentData()
        ports = list_serial_ports()
        port_combo.clear()

        if ports:
            for device, desc in ports:
                display = f"{device} - {desc}"
                port_combo.addItem(display, device)
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[REFRESH] Found {len(ports)} serial ports")
        else:
            port_combo.addItem("Device not found", None)
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[REFRESH] No serial ports found")

        # คืนค่าพอร์ตเดิมถ้าเจอ
        idx = port_combo.findData(current_data)
        if idx >= 0:
            port_combo.setCurrentIndex(idx)
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[REFRESH] Restored previous port: {current_data}")
        else:
            port_combo.setCurrentIndex(port_combo.count() - 1)
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[REFRESH] Selected default port")
    
    def reload_sim_with_progress(self, port_combo, baud_combo):
        """โหลดข้อมูล SIM ใหม่พร้อมการแสดงสถานะ"""
        if hasattr(self.parent, 'update_at_result_display'):
            self.parent.update_at_result_display("[REFRESH] Reloading SIM data...")
        
        port = port_combo.currentData()
        baudrate = int(baud_combo.currentText())
        port_ok = bool(port and port != "Device not found")

        if port_ok:
            try:
                # หยุด serial thread เดิมถ้ามี
                if hasattr(self.parent, 'serial_thread') and self.parent.serial_thread and self.parent.serial_thread.isRunning():
                    self.parent.serial_thread.stop()
                    self.parent.serial_thread.wait()
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[REFRESH] Stopped previous serial connection")

                # โหลดข้อมูล SIM ใหม่
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[REFRESH] Loading SIM information...")
                
                sims = load_sim_data(port, baudrate)

                # อัพเดท signal strength
                for sim in sims:
                    sig = self.query_signal_strength(port, baudrate)
                    sim.signal = sig

                # แสดงผลลัพธ์
                if sims and sims[0].imsi != "-":
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display(f"[REFRESH] ✅ SIM data loaded successfully!")
                        self.parent.update_at_result_display(f"[REFRESH] Phone: {sims[0].phone}")
                        self.parent.update_at_result_display(f"[REFRESH] IMSI: {sims[0].imsi}")
                        self.parent.update_at_result_display(f"[REFRESH] Carrier: {sims[0].carrier}")
                        self.parent.update_at_result_display(f"[REFRESH] Signal: {sims[0].signal}")
                else:
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display(f"[REFRESH] ⚠️ SIM data not available or SIM not ready")

                return sims

            except Exception as e:
                print(f"Error reloading SIM data: {e}")
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[REFRESH] ❌ Failed to reload SIM data: {e}")
                return []
        else:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[REFRESH] ❌ No valid port selected")
            return []
    
    def query_signal_strength(self, port, baudrate):
        """ส่ง AT+CSQ แล้วคืนค่าเป็นข้อความพร้อม Unicode Signal Bars"""
        try:
            ser = serial.Serial(port, baudrate, timeout=3)
            time.sleep(0.1)
            
            # ตรวจสอบสถานะ SIM ก่อนอ่านสัญญาณ
            ser.write(b'AT+CPIN?\r\n')
            time.sleep(0.3)
            cpin_response = ser.read(200).decode(errors='ignore')
            
            # ถ้า SIM ไม่พร้อมให้คืนค่า No Signal
            if "CPIN: READY" not in cpin_response:
                ser.close()
                return '▁▁▁▁ No SIM'
            
            # ตรวจสอบการลงทะเบียน Network
            ser.write(b'AT+CREG?\r\n')
            time.sleep(0.3)
            creg_response = ser.read(200).decode(errors='ignore')
            
            # ถ้าไม่ได้ลงทะเบียนเครือข่าย
            if "+CREG: 0,1" not in creg_response and "+CREG: 0,5" not in creg_response:
                ser.close()
                return '▁▁▁▁ No Network'
            
            # อ่านค่าสัญญาณ
            ser.write(b'AT+CSQ\r\n')
            time.sleep(0.2)
            
            raw = ser.read(200).decode(errors='ignore')
            ser.close()
            
            import re
            m = re.search(r'\+CSQ:\s*(\d+),', raw)
            if not m:
                return '▁▁▁▁ No Signal'
                
            rssi = int(m.group(1))
            
            if rssi == 99:
                return '▁▁▁▁ Unknown'
            elif rssi == 0:
                return '▁▁▁▁ No Signal'
                
            dbm = -113 + 2*rssi
            
            # กำหนด Unicode Signal Bars ตามระดับสัญญาณ
            if dbm >= -70:
                return f'▁▃▅█ {dbm} dBm (Excellent)'      # 4 bars - แรงมาก
            elif dbm >= -85:
                return f'▁▃▅▇ {dbm} dBm (Good)'          # 3 bars - ดี
            elif dbm >= -100:
                return f'▁▃▁▁ {dbm} dBm (Fair)'          # 2 bars - ปานกลาง
            elif dbm >= -110:
                return f'▁▁▁▁ {dbm} dBm (Poor)'          # 1 bar - อ่อน
            else:
                return f'▁▁▁▁ {dbm} dBm (Very Poor)'     # No bars - ไม่มีสัญญาณ
                
        except Exception as e:
            return '▁▁▁▁ Error'
    
    def test_port_connection(self, port, baudrate):
        """ทดสอบการเชื่อมต่อพอร์ต"""
        try:
            ser = serial.Serial(port, baudrate, timeout=2)
            ser.write(b'AT\r\n')
            time.sleep(0.1)
            response = ser.read(50).decode(errors='ignore')
            ser.close()
            
            return "OK" in response
            
        except Exception as e:
            print(f"Port connection test failed: {e}")
            return False


class SerialConnectionManager:
    """จัดการการเชื่อมต่อ Serial และ monitoring"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def setup_serial_monitor(self, port, baudrate):
        """ตั้งค่า Serial Monitor Thread - แก้ไขป้องกันการส่งซ้ำ"""
        try:
            # หยุดและตัดการเชื่อมต่อ thread เดิมอย่างสมบูรณ์
            if hasattr(self.parent, 'serial_thread') and self.parent.serial_thread:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SETUP] Stopping previous serial thread...")
                
                # ตัดการเชื่อมต่อ signals ทั้งหมดก่อน
                try:
                    old_thread = self.parent.serial_thread
                    
                    # ตัดการเชื่อมต่อ signals เดิมทั้งหมด
                    old_thread.at_response_signal.disconnect()
                    old_thread.new_sms_signal.disconnect()
                    old_thread.sim_failure_detected.disconnect()
                    old_thread.cpin_ready_detected.disconnect()
                    old_thread.sim_ready_signal.disconnect()
                    old_thread.cpin_status_signal.disconnect()
                    
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[SETUP] Disconnected all previous signals")
                        
                except Exception as e:
                    # บาง signals อาจไม่ได้เชื่อมต่อ - ไม่เป็นปัญหา
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display(f"[SETUP] Signal disconnect note: {e}")
                
                # หยุด thread
                self.parent.serial_thread.stop()
                self.parent.serial_thread.wait(5000)  # รอสูงสุด 5 วินาที
                self.parent.serial_thread = None
                
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SETUP] Previous thread stopped successfully")
            
            if not port or port == "Device not found":
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SETUP] ❌ No valid port to connect")
                return None
            
            # ทดสอบการเชื่อมต่อก่อน
            try:
                if hasattr(self.parent, 'set_port_status'):
                    self.parent.set_port_status('connecting', port, baudrate)
                test_serial = serial.Serial(port, baudrate, timeout=2)
                test_serial.close()
            except Exception as e:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[SETUP] ❌ Cannot connect to {port}: {e}")
                return None
            
            serial_thread = SerialMonitorThread(port, baudrate)

            # ✅ ต่อสำเร็จ / หลุดการเชื่อมต่อ
            if hasattr(self.parent, 'on_serial_connected'):
                serial_thread.connected_signal.connect(self.parent.on_serial_connected, Qt.UniqueConnection)
            if hasattr(self.parent, 'on_serial_disconnected'):
                serial_thread.disconnected_signal.connect(self.parent.on_serial_disconnected, Qt.UniqueConnection)
            
            if hasattr(self.parent, 'on_new_sms_signal'):
                serial_thread.new_sms_signal.connect(
                    self.parent.on_new_sms_signal, Qt.UniqueConnection
                )
            if hasattr(self.parent, 'update_at_result_display'):
                serial_thread.at_response_signal.connect(
                    self.parent.update_at_result_display, Qt.UniqueConnection
                )
            
            # เชื่อมต่อ signals สำหรับ SIM recovery ด้วย UniqueConnection
            if hasattr(self.parent, 'on_sim_failure_detected'):
                serial_thread.sim_failure_detected.connect(
                    self.parent.on_sim_failure_detected, Qt.UniqueConnection
                )
            if hasattr(self.parent, 'on_cpin_ready_detected'):
                serial_thread.cpin_ready_detected.connect(
                    self.parent.on_cpin_ready_detected, Qt.UniqueConnection
                )
            if hasattr(self.parent, 'on_sim_ready_auto'):
                serial_thread.sim_ready_signal.connect(
                    self.parent.on_sim_ready_auto, Qt.UniqueConnection
                )
            if hasattr(self.parent, 'on_cpin_status_received'):
                serial_thread.cpin_status_signal.connect(
                    self.parent.on_cpin_status_received, Qt.UniqueConnection
                )
            
            # เริ่ม thread
            serial_thread.start()
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SETUP] ✅ Serial monitor started on {port}")
                self.parent.update_at_result_display("[SETUP] All signals connected with duplicate protection")

            return serial_thread
            
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SETUP ERROR] Failed to setup serial monitor: {e}")
            if hasattr(self.parent, 'set_port_status'):
                self.parent.set_port_status('disconnected')
            return None
    
    def start_sms_monitor(self, port, baudrate):
        """เริ่ม SMS monitoring"""
        try:
            serial_thread = self.setup_serial_monitor(port, baudrate)
            if serial_thread:
                # เก็บ reference
                if hasattr(self.parent, 'serial_thread'):
                    self.parent.serial_thread = serial_thread
                
                # Auto-reset CFUN (รอให้ thread เริ่มก่อน)
                def delayed_cfun_reset():
                    if serial_thread and serial_thread.isRunning():
                        serial_thread.send_command("AT+CFUN=0")
                        QTimer.singleShot(2000, lambda: serial_thread.send_command("AT+CFUN=1"))
                
                QTimer.singleShot(1000, delayed_cfun_reset)
                
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SMS MONITOR] SMS monitoring started")
            
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SMS MONITOR ERROR] {e}")
    
    def stop_serial_monitor(self):
        """หยุด serial monitor"""
        try:
            if hasattr(self.parent, 'serial_thread') and self.parent.serial_thread:
                self.parent.serial_thread.stop()
                self.parent.serial_thread.wait()
                self.parent.serial_thread = None
                
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SETUP] Serial monitor stopped")
                    
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SETUP ERROR] Error stopping serial monitor: {e}")
            if hasattr(self.parent, 'on_serial_disconnected'):
                self.parent.on_serial_disconnected()

class SimRecoveryManager:
    def __init__(self, parent=None):
        self.parent = parent
        self._recovery_in_progress = False  # เพิ่มการป้องกัน
        self._last_recovery_time = 0
        self._min_recovery_interval = 30  # วินาที
    
    def manual_sim_recovery(self):
        """ทำ SIM recovery แบบ manual - แก้ไขหลัก"""
        current_time = time.time()

        # ตรวจสอบว่า recovery เพิ่งทำไปหรือไม่
        if (self._recovery_in_progress or 
            current_time - self._last_recovery_time < self._min_recovery_interval):
            
            remaining = self._min_recovery_interval - (current_time - self._last_recovery_time)
            QMessageBox.information(
                self.parent, 
                "Recovery Cooldown", 
                f"⏳ Please wait {remaining:.0f} seconds before attempting recovery again.\n\n"
                "This prevents system overload and duplicate processes."
            )
            return
        
        # ตั้งแฟลกป้องกัน
        self._recovery_in_progress = True
        self._last_recovery_time = current_time

        try:
            # ตรวจสอบ serial connection
            if not hasattr(self.parent, 'serial_thread') or not self.parent.serial_thread:
                QMessageBox.warning(
                    self.parent, 
                    "No Connection", 
                    "❌ No serial connection available!\n\nPlease:\n1. Select correct USB Port\n2. Click 'Refresh Ports' first\n3. Make sure the modem is connected"
                )
                return
            
            # ตรวจสอบว่า thread ยังทำงานอยู่
            if not self.parent.serial_thread.isRunning():
                QMessageBox.warning(
                    self.parent, 
                    "Connection Not Active", 
                    "❌ Serial connection is not active!\n\nPlease click 'Refresh Ports' to reconnect."
                )
                return
            
            # ตรวจสอบ recovery ที่กำลังดำเนินการ
            if getattr(self.parent, 'sim_recovery_in_progress', False):
                QMessageBox.information(
                    self.parent, "Recovery in Progress", 
                    "⏳ SIM recovery is already in progress.\n\nPlease wait for the current process to complete..."
                )
                return
            
            # ยืนยันการทำ recovery
            reply = QMessageBox.question(
                self.parent, 
                'Manual SIM Recovery', 
                '🔧 Do you want to perform manual SIM recovery?\n\n'
                'This process will:\n'
                '• Reset the modem (AT+CFUN=0 → AT+CFUN=1)\n'
                '• Check SIM status (AT+CPIN?)\n'
                '• Auto-refresh SIM data if successful\n\n'
                '⚠️ This may take 10-15 seconds to complete.\n\n'
                'Proceed with SIM recovery?',
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # เริ่ม recovery process
                if hasattr(self.parent, 'sim_recovery_in_progress'):
                    self.parent.sim_recovery_in_progress = True
                
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[MANUAL] 🔧 Starting enhanced SIM recovery...")
                
                # เริ่ม recovery ผ่าน serial thread
                if hasattr(self.parent.serial_thread, 'force_sim_recovery'):
                    self.parent.serial_thread.force_sim_recovery()
                else:
                    self._fallback_recovery()
                    
                # แสดง progress message
                self._show_recovery_progress()
        
        finally:
            # ปลดล็อกหลังจาก 15 วินาที
            QTimer.singleShot(15000, self._reset_recovery_flag)
    
    def _show_recovery_progress(self):
        """แสดงความคืบหน้าของ recovery"""
        if hasattr(self.parent, 'show_non_blocking_message'):
            self.parent.show_non_blocking_message(
                "SIM Recovery in Progress",
                "🔧 SIM recovery is in progress...\n\n"
                "Steps:\n"
                "1. ⏳ Disabling modem (AT+CFUN=0)\n"
                "2. ⏳ Enabling modem (AT+CFUN=1)\n"
                "3. ⏳ Checking SIM status (AT+CPIN?)\n"
                "4. ⏳ Refreshing SIM data\n\n"
                "Please wait 10-15 seconds..."
            )

    def _reset_recovery_flag(self):
        """รีเซ็ตแฟลก recovery"""
        self._recovery_in_progress = False
        if hasattr(self.parent, 'update_at_result_display'):
            self.parent.update_at_result_display("[RECOVERY] Ready for next recovery attempt")
    
    def _fallback_recovery(self):
        """วิธี recovery สำรอง"""
        try:
            if hasattr(self.parent, 'serial_thread'):
                # ส่งคำสั่ง recovery แบบ sequential
                success1 = self.parent.serial_thread.send_command("AT+CFUN=0")
                
                if success1:
                    QTimer.singleShot(2000, lambda: self.parent.serial_thread.send_command("AT+CFUN=1"))
                    QTimer.singleShot(5000, lambda: self.parent.serial_thread.send_command("AT+CPIN?"))
                    
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[MANUAL] Fallback recovery initiated")
                else:
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[MANUAL ERROR] Failed to send AT+CFUN=0")
                    self._recovery_failed("Failed to send AT+CFUN=0 command")
                    
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[MANUAL ERROR] Fallback recovery failed: {e}")
            self._recovery_failed(str(e))
    
    def _recovery_failed(self, error_msg):
        """จัดการเมื่อ recovery ล้มเหลว"""
        if hasattr(self.parent, 'sim_recovery_in_progress'):
            self.parent.sim_recovery_in_progress = False
            
        if hasattr(self.parent, 'show_non_blocking_message'):
            self.parent.show_non_blocking_message(
                "SIM Recovery Failed",
                f"❌ SIM recovery failed!\n\n"
                f"Error: {error_msg}\n\n"
                "Please try:\n"
                "• Check SIM card connection\n"
                "• Restart the modem manually\n"
                "• Click 'Refresh Ports' and try again"
            )
    
    def on_recovery_timeout(self):
        """จัดการเมื่อ recovery timeout"""
        if hasattr(self.parent, 'sim_recovery_in_progress'):
            self.parent.sim_recovery_in_progress = False
            
        if hasattr(self.parent, 'update_at_result_display'):
            self.parent.update_at_result_display("[SIM RECOVERY] ⏰ Recovery timeout reached")
        
        if hasattr(self.parent, 'show_non_blocking_message'):
            self.parent.show_non_blocking_message(
                "SIM Recovery Timeout",
                "⚠️ SIM recovery process timed out!\n\n"
                "Please check:\n"
                "• SIM card connection\n"
                "• Hardware issues\n"
                "• Manual modem restart may be needed\n\n"
                "Try clicking 'Refresh Ports' and attempt recovery again."
            )