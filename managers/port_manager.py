# port_manager.py
"""
จัดการพอร์ต Serial และการเชื่อมต่อ
"""

import serial
import time
from core.utility_functions import list_serial_ports
from services.sim_model import load_sim_data


class PortManager:
    """จัดการพอร์ต Serial และการเชื่อมต่อ"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def refresh_ports(self, port_combo):
        """รีเฟรชรายการพอร์ต Serial
        
        Args:
            port_combo: QComboBox widget สำหรับแสดงพอร์ต
        """
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
        """โหลดข้อมูล SIM ใหม่พร้อมการแสดงสถานะ
        
        Args:
            port_combo: QComboBox สำหรับพอร์ต
            baud_combo: QComboBox สำหรับ baudrate
            
        Returns:
            list: รายการ SIM ที่โหลดได้
        """
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
        """ส่ง AT+CSQ แล้วคืนค่าเป็นข้อความพร้อม Unicode Signal Bars
        
        Args:
            port (str): พอร์ต Serial
            baudrate (int): Baudrate
            
        Returns:
            str: ข้อความแสดงสัญญาณ
        """
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
        """ทดสอบการเชื่อมต่อพอร์ต
        
        Args:
            port (str): พอร์ต Serial
            baudrate (int): Baudrate
            
        Returns:
            bool: True ถ้าเชื่อมต่อได้
        """
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
    
    def get_modem_info(self, port, baudrate):
        """ดึงข้อมูลโมเด็ม
        
        Args:
            port (str): พอร์ต Serial
            baudrate (int): Baudrate
            
        Returns:
            dict: ข้อมูลโมเด็ม
        """
        try:
            ser = serial.Serial(port, baudrate, timeout=3)
            
            modem_info = {
                'manufacturer': 'Unknown',
                'model': 'Unknown',
                'version': 'Unknown',
                'imei': 'Unknown'
            }
            
            # ดึงข้อมูล manufacturer
            ser.write(b'AT+CGMI\r\n')
            time.sleep(0.2)
            response = ser.read(200).decode(errors='ignore')
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('AT') and 'OK' not in line:
                    modem_info['manufacturer'] = line
                    break
            
            # ดึงข้อมูล model
            ser.write(b'AT+CGMM\r\n')
            time.sleep(0.2)
            response = ser.read(200).decode(errors='ignore')
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('AT') and 'OK' not in line:
                    modem_info['model'] = line
                    break
            
            # ดึงข้อมูล version
            ser.write(b'AT+CGMR\r\n')
            time.sleep(0.2)
            response = ser.read(200).decode(errors='ignore')
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('AT') and 'OK' not in line:
                    modem_info['version'] = line
                    break
            
            # ดึงข้อมูล IMEI
            ser.write(b'AT+CGSN\r\n')
            time.sleep(0.2)
            response = ser.read(200).decode(errors='ignore')
            for line in response.split('\n'):
                line = line.strip()
                if line and line.isdigit() and len(line) >= 15:
                    modem_info['imei'] = line
                    break
            
            ser.close()
            return modem_info
            
        except Exception as e:
            print(f"Error getting modem info: {e}")
            return {
                'manufacturer': 'Error',
                'model': 'Error', 
                'version': 'Error',
                'imei': 'Error'
            }


class SerialConnectionManager:
    """จัดการการเชื่อมต่อ Serial และ monitoring"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def setup_serial_monitor(self, port, baudrate):
        """ตั้งค่า Serial Monitor Thread
        
        Args:
            port (str): พอร์ต Serial
            baudrate (int): Baudrate
            
        Returns:
            SerialMonitorThread: Thread object หรือ None
        """
        try:
            # หยุด thread เดิมถ้ามี
            if hasattr(self.parent, 'serial_thread') and self.parent.serial_thread:
                self.parent.serial_thread.stop()
            
            if not port or port == "Device not found":
                return None
            
            from services.serial_service import SerialMonitorThread
            serial_thread = SerialMonitorThread(port, baudrate)
            
            # เชื่อมต่อ signals
            if hasattr(self.parent, 'on_new_sms_signal'):
                serial_thread.new_sms_signal.connect(self.parent.on_new_sms_signal)
            if hasattr(self.parent, 'update_at_result_display'):
                serial_thread.at_response_signal.connect(self.parent.update_at_result_display)
            
            # เชื่อมต่อ signals สำหรับ SIM recovery
            if hasattr(self.parent, 'on_sim_failure_detected'):
                serial_thread.sim_failure_detected.connect(self.parent.on_sim_failure_detected)
            if hasattr(self.parent, 'on_cpin_ready_detected'):
                serial_thread.cpin_ready_detected.connect(self.parent.on_cpin_ready_detected)
            if hasattr(self.parent, 'on_sim_ready_auto'):
                serial_thread.sim_ready_signal.connect(self.parent.on_sim_ready_auto)
            if hasattr(self.parent, 'on_cpin_status_received'):
                serial_thread.cpin_status_signal.connect(self.parent.on_cpin_status_received)
            
            serial_thread.start()
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[SETUP] Serial monitor started with SMS notification")

            return serial_thread
            
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SETUP ERROR] Failed to setup serial monitor: {e}")
            return None
    
    def start_sms_monitor(self, port, baudrate):
        """เริ่ม SMS monitoring
        
        Args:
            port (str): พอร์ต Serial
            baudrate (int): Baudrate
        """
        try:
            serial_thread = self.setup_serial_monitor(port, baudrate)
            if serial_thread:
                # เก็บ reference
                if hasattr(self.parent, 'serial_thread'):
                    self.parent.serial_thread = serial_thread
                
                # Auto-reset CFUN
                serial_thread.send_command("AT+CFUN=0")
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, lambda: serial_thread.send_command("AT+CFUN=1"))
                
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


class SimRecoveryManager:
    """จัดการ SIM recovery"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def manual_sim_recovery(self):
        """ทำ SIM recovery แบบ manual"""
        if not hasattr(self.parent, 'serial_thread') or not self.parent.serial_thread:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.parent, "Notice", "No serial connection available")
            return
        
        if getattr(self.parent, 'sim_recovery_in_progress', False):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self.parent, "Recovery in Progress", 
                "SIM recovery is already in progress. Please wait..."
            )
            return
        
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.parent, 
            'Manual SIM Recovery', 
            'Do you want to perform manual SIM recovery?\n\n'
            'This will:\n'
            '1. Reset the modem (AT+CFUN=0/1)\n'
            '2. Check SIM status (AT+CPIN?)\n'
            '3. Auto-refresh SIM data if ready\n\n'
            'Proceed?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if hasattr(self.parent, 'sim_recovery_in_progress'):
                self.parent.sim_recovery_in_progress = True
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[MANUAL] Starting enhanced SIM recovery...")
            
            # เริ่ม recovery ผ่าน serial thread
            if hasattr(self.parent.serial_thread, 'force_sim_recovery'):
                self.parent.serial_thread.force_sim_recovery()
            else:
                self._fallback_recovery()
    
    def _fallback_recovery(self):
        """วิธี recovery สำรอง"""
        try:
            if hasattr(self.parent, 'serial_thread'):
                self.parent.serial_thread.send_command("AT+CFUN=0")
                
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(2000, lambda: self.parent.serial_thread.send_command("AT+CFUN=1"))
                QTimer.singleShot(5000, lambda: self.parent.serial_thread.send_command("AT+CPIN?"))
                
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[MANUAL] Fallback recovery initiated")
                    
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[MANUAL ERROR] Fallback recovery failed: {e}")
    
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
                "• Manual modem restart may be needed"
            )