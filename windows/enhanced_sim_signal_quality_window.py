# enhanced_sim_signal_quality_window.py - FIXED VERSION

import re
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QTabWidget, QWidget, QProgressBar, QGroupBox, QGridLayout,
    QScrollArea, QFrame, QMessageBox, QApplication, QComboBox,
    QCheckBox, QSpinBox, QSlider, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QFont, QTextCursor, QPalette, QColor, QPixmap, QPainter
from widgets.signal_strength_widget import SignalStrengthWidget
from styles.signal_quality_window_styles import get_stylesheet

ENABLE_GRAPH_SCROLLING = True

# --- Y-axis tick options ---
SHOW_Y_TICKS = True    
Y_TICK_STEP  = 2       

@dataclass
class SIMIdentityInfo:
    imsi: str = ""
    iccid: str = ""
    phone_number: str = ""
    # IMSI breakdown
    mcc: str = ""  # Mobile Country Code
    mnc: str = ""  # Mobile Network Code
    msin: str = ""  # Mobile Subscriber Identification Number
    # ICCID breakdown
    iin: str = ""  # Issuer Identification Number
    account_id: str = ""
    check_digit: str = ""
    # Analysis results
    country: str = ""
    carrier: str = ""
    home_network: bool = True
    roaming: bool = False
    sim_valid: bool = True
    iccid_valid: bool = True

@dataclass
class SignalMeasurement:
    timestamp: str
    rssi: int = -999
    rsrp: int = -999
    rsrq: int = -999
    sinr: int = -999
    ber: float = 99.0
    signal_bars: int = 0
    quality_score: float = 0.0
    network_type: str = "Unknown"
    carrier: str = "Unknown"
    sim_info: Optional[SIMIdentityInfo] = None


class EnhancedSignalQualityThread(QThread):
    
    signal_measured = pyqtSignal(SignalMeasurement)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    sim_info_updated = pyqtSignal(SIMIdentityInfo)
    command_response_signal = pyqtSignal(str)
    
    def __init__(self, serial_thread, interval: int = 5, include_sim_info: bool = True):
        super().__init__()
        self.serial_thread = serial_thread
        self.interval = interval
        self.monitoring = False
        self.include_sim_info = include_sim_info
        self.sim_identity = None
        
        # เก็บ responses ชั่วคราว
        self.temp_responses = {}
        self.current_command = None
        self.response_timeout = 5.0
        
        self.mcc_database = {
            "520": {"country": "Thailand", "iso": "TH"},
            "525": {"country": "Singapore", "iso": "SG"},
            "502": {"country": "Malaysia", "iso": "MY"},
            "510": {"country": "Indonesia", "iso": "ID"},
            "515": {"country": "Philippines", "iso": "PH"},
            "454": {"country": "Hong Kong", "iso": "HK"},
            "460": {"country": "China", "iso": "CN"},
            "405": {"country": "India", "iso": "IN"},
            "310": {"country": "United States", "iso": "US"}
        }
        
        self.thailand_mnc = {
            "00": {"carrier": "CAT Telecom", "type": "GSM"},
            "01": {"carrier": "AIS", "type": "GSM/3G/4G/5G"},
            "03": {"carrier": "AIS", "type": "3G/4G/5G"},
            "05": {"carrier": "dtac", "type": "GSM/3G/4G/5G"},
            "15": {"carrier": "TrueMove H", "type": "3G/4G/5G"},
            "18": {"carrier": "dtac", "type": "3G/4G/5G"},
            "23": {"carrier": "AIS", "type": "4G/5G"},
            "25": {"carrier": "TrueMove H", "type": "4G/5G"},
            "47": {"carrier": "NT Mobile", "type": "4G/5G"},
            "99": {"carrier": "TrueMove", "type": "GSM/3G"}
        }
        
        # เชื่อมต่อ serial thread เพื่อรับ responses
        if self.serial_thread:
            self.serial_thread.at_response_signal.connect(self.handle_serial_response)
    
    def handle_serial_response(self, response):
        """รับ response จาก serial thread"""
        try:
            if not self.monitoring or not self.current_command:
                return
            response = response.strip()
            if not response:
                return
            
            # แสดงใน Signal Quality window
            self.command_response_signal.emit(f"RECV: {response}")
            
            # เก็บ response
            if self.current_command not in self.temp_responses:
                self.temp_responses[self.current_command] = []
            
            self.temp_responses[self.current_command].append(response)
            
            # ถ้าได้ OK หรือ ERROR แล้วให้หยุดรอ
            if response in ['OK', 'ERROR'] or 'ERROR:' in response:
                self.current_command = None
            
        except Exception as e:
            print(f"Error handling response: {e}")
    
    def _send_command_and_wait_direct(self, command: str, timeout: float = 5.0) -> List[str]:
        """ส่งคำสั่งและรอ response โดยตรง"""
        if not self.serial_thread or not self.serial_thread.isRunning():
            return ["ERROR: No connection"]
        
        try:
            # บอก serial thread ว่าเป็น Signal Quality command
            if hasattr(self.serial_thread, 'set_command_source'):
                self.serial_thread.set_command_source('SIGNAL_QUALITY')
            
            # ล้างข้อมูลเก่า
            self.temp_responses.clear()
            self.current_command = command
            
            # แสดงคำสั่งที่ส่ง
            self.command_response_signal.emit(f"[SIGNAL] {command}")
            
            # ส่งคำสั่ง
            success = self.serial_thread.send_command(command)
            if not success:
                self.current_command = None
                return ["ERROR: Failed to send command"]
            
            # รอ response
            wait_time = 0
            while self.current_command and wait_time < timeout:
                self.msleep(100)
                wait_time += 0.1
            
            # ดึง responses
            responses = self.temp_responses.get(command, [])
            self.current_command = None
            
            return responses if responses else ["ERROR: No response"]
            
        except Exception as e:
            self.current_command = None
            return [f"ERROR: {e}"]
    
    def _measure_signal(self) -> Optional[SignalMeasurement]:
        """วัดสัญญาณ - ปรับปรุงให้แม่นยำขึ้น"""
        try:
            measurement = SignalMeasurement(
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
            
            # ส่ง AT+CSQ
            csq_responses = self._send_command_and_wait_direct("AT+CSQ")
            print(f"CSQ Responses: {csq_responses}")
            
            for response in csq_responses:
                # หา +CSQ: response
                if '+CSQ:' in response:
                    match = re.search(r'\+CSQ:\s*(\d+),\s*(\d+)', response)
                    if match:
                        rssi_raw = int(match.group(1))
                        ber_raw = int(match.group(2))
                        
                        print(f"Found +CSQ: RSSI={rssi_raw}, BER={ber_raw}")
                        
                        # คำนวณ RSSI ตาม GSM 07.07 standard
                        if rssi_raw == 99:  # Not known or not detectable
                            measurement.rssi = -999
                        elif rssi_raw == 0:
                            measurement.rssi = -113  # <= -113 dBm
                        elif rssi_raw == 31:
                            measurement.rssi = -51   # >= -51 dBm
                        elif 1 <= rssi_raw <= 30:
                            measurement.rssi = -113 + (rssi_raw * 2)
                        else:
                            measurement.rssi = -999
                        
                        # คำนวณ BER
                        if ber_raw == 99:
                            measurement.ber = 99.0  # Not known or not detectable
                        else:
                            measurement.ber = ber_raw
                        
                        measurement.signal_bars = self._calculate_bars(measurement.rssi)
                        measurement.quality_score = self._calculate_quality(measurement.rssi, measurement.ber)
                        
                        print(f"Calculated: RSSI={measurement.rssi}, Quality={measurement.quality_score:.1f}")
                        break
            
            # ถ้าไม่ได้ค่าจาก +CSQ: ให้ลองหาจาก response อื่น
            if measurement.rssi == -999:
                for response in csq_responses:
                    # บางครั้งได้แค่ตัวเลข เช่น "14,99"
                    if re.match(r'^\d+,\d+$', response.strip()):
                        parts = response.strip().split(',')
                        if len(parts) == 2:
                            rssi_raw = int(parts[0])
                            ber_raw = int(parts[1])
                            
                            if rssi_raw != 99:
                                if rssi_raw == 0:
                                    measurement.rssi = -113
                                elif rssi_raw == 31:
                                    measurement.rssi = -51
                                elif 1 <= rssi_raw <= 30:
                                    measurement.rssi = -113 + (rssi_raw * 2)
                                
                                measurement.ber = ber_raw if ber_raw != 99 else 99.0
                                measurement.signal_bars = self._calculate_bars(measurement.rssi)
                                measurement.quality_score = self._calculate_quality(measurement.rssi, measurement.ber)
                                
                                print(f"Alternative parse: RSSI={measurement.rssi}, Quality={measurement.quality_score:.1f}")
                                break
            
            # ส่ง AT+CESQ สำหรับ LTE measurements (ถ้าต้องการ)
            cesq_responses = self._send_command_and_wait_direct("AT+CESQ")
            for response in cesq_responses:
                if '+CESQ:' in response:
                    match = re.search(r'\+CESQ:\s*(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
                    if match:
                        values = [int(x) for x in match.groups()]
                        rxlev, ber, rscp, ecn0, rsrq, rsrp = values
                        
                        if rsrq != 255:
                            measurement.rsrq = int(-19.5 + (rsrq * 0.5))
                        if rsrp != 255:
                            measurement.rsrp = -141 + rsrp
                        break
            
            # ดึงข้อมูล carrier
            if not measurement.carrier or measurement.carrier == "Unknown":
                cops_responses = self._send_command_and_wait_direct("AT+COPS?")
                for response in cops_responses:
                    if '+COPS:' in response:
                        match = re.search(r'"([^"]*)"', response)
                        if match:
                            measurement.carrier = match.group(1)
                            break
            
            # ใช้ SIM identity carrier ถ้ามี
            if self.sim_identity and self.sim_identity.carrier:
                measurement.carrier = self.sim_identity.carrier
            
            return measurement
            
        except Exception as e:
            print(f"Error measuring signal: {e}")
            self.error_occurred.emit(f"Error measuring signal: {e}")
            return None
    
    def _calculate_bars(self, rssi: int) -> int:
        """คำนวณจำนวนแท่งสัญญาณ"""
        if rssi >= -70:
            return 5
        elif rssi >= -80:
            return 4
        elif rssi >= -90:
            return 3
        elif rssi >= -100:
            return 2
        elif rssi >= -110:
            return 1
        else:
            return 0
    
    def _calculate_quality(self, rssi: int, ber: float) -> float:
        """คำนวณคุณภาพสัญญาณ"""
        if rssi == -999:
            return 0.0
        rssi_score = max(0, min(100, (rssi + 113) * 100 / 62))
        if ber < 99:
            ber_score = max(0, min(100, 100 - (ber * 10)))
        else:
            ber_score = 50  # ค่าเริ่มต้นถ้าไม่รู้
        return (rssi_score * 0.7) + (ber_score * 0.3)
    
    def run(self):
        try:
            self.status_updated.emit("🟢 Connected - Loading SIM information...")
            
            if self.include_sim_info and not self.sim_identity:
                self.sim_identity = self._get_sim_identity()
                if self.sim_identity:
                    self.sim_info_updated.emit(self.sim_identity)
                    self.status_updated.emit(f"📱 SIM Info loaded - {self.sim_identity.carrier}")
            
            self.status_updated.emit("🟢 Connected - Monitoring signal...")
            
            while self.monitoring:
                try:
                    measurement = self._measure_signal()
                    if measurement:
                        measurement.sim_info = self.sim_identity
                        self.signal_measured.emit(measurement)
                    else:
                        default_measurement = SignalMeasurement(
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                            rssi=-999,
                            quality_score=0.0,
                            signal_bars=0,
                            carrier="Unknown",
                            network_type="Unknown"
                        )
                        default_measurement.sim_info = self.sim_identity
                        self.signal_measured.emit(default_measurement)
                    
                    for _ in range(self.interval * 10):
                        if not self.monitoring:
                            break
                        self.msleep(100)
                        
                except Exception as e:
                    self.error_occurred.emit(f"Measurement error: {e}")
                    self.msleep(1000)
                    
        except Exception as e:
            self.error_occurred.emit(f"Monitoring error: {e}")
        finally:
            self.status_updated.emit("🔴 Monitoring stopped")
    
    def _get_sim_identity(self) -> Optional[SIMIdentityInfo]:
        try:
            sim_info = SIMIdentityInfo()
            
            # ดึง IMSI
            imsi_responses = self._send_command_and_wait_direct("AT+CIMI")
            for response in imsi_responses:
                if response and response.isdigit() and len(response) >= 15:
                    sim_info.imsi = response[:15]
                    self._parse_imsi(sim_info)
                    break
                else:
                    # หา IMSI ใน response ที่มีข้อความอื่นด้วย
                    imsi_match = re.search(r'(\d{15})', response)
                    if imsi_match:
                        sim_info.imsi = imsi_match.group(1)
                        self._parse_imsi(sim_info)
                        break
            
            # ดึง ICCID
            iccid_responses = self._send_command_and_wait_direct("AT+CCID")
            if not any('+CCID:' in r for r in iccid_responses):
                iccid_responses = self._send_command_and_wait_direct("AT+QCCID")
            
            for response in iccid_responses:
                if '+CCID:' in response or '+QCCID:' in response:
                    iccid_match = re.search(r'(\d{18,22})', response)
                    if iccid_match:
                        sim_info.iccid = iccid_match.group(1)
                        self._parse_iccid(sim_info)
                        break
            
            # ดึงเบอร์โทรศัพท์
            cnum_responses = self._send_command_and_wait_direct("AT+CNUM")
            for response in cnum_responses:
                if '+CNUM:' in response:
                    phone_match = re.search(r'"([+\d]+)"', response)
                    if phone_match:
                        sim_info.phone_number = phone_match.group(1)
                        break
            
            self._validate_sim_info(sim_info)
            return sim_info if sim_info.imsi else None
            
        except Exception as e:
            print(f"Error getting SIM identity: {e}")
            return None
    
    def _parse_imsi(self, sim_info: SIMIdentityInfo):
        """วิเคราะห์ IMSI"""
        if not sim_info.imsi or len(sim_info.imsi) < 15:
            return
        
        try:
            sim_info.mcc = sim_info.imsi[:3]
            
            if sim_info.mcc == "520":  # Thailand
                sim_info.mnc = sim_info.imsi[3:5]
                sim_info.msin = sim_info.imsi[5:]
            else:
                sim_info.mnc = sim_info.imsi[3:6]
                sim_info.msin = sim_info.imsi[6:]
            
            if sim_info.mcc in self.mcc_database:
                country_info = self.mcc_database[sim_info.mcc]
                sim_info.country = country_info['country']
            
            if sim_info.mcc == "520":
                if sim_info.mnc in self.thailand_mnc:
                    carrier_info = self.thailand_mnc[sim_info.mnc]
                    sim_info.carrier = carrier_info['carrier']
                    sim_info.home_network = True
                    sim_info.roaming = False
                else:
                    sim_info.carrier = f"Unknown Thai Network (MNC: {sim_info.mnc})"
            else:
                sim_info.home_network = False
                sim_info.roaming = True
                sim_info.carrier = f"Foreign Network ({sim_info.country})"
                
        except Exception as e:
            print(f"Error parsing IMSI: {e}")
    
    def _parse_iccid(self, sim_info: SIMIdentityInfo):
        """วิเคราะห์ ICCID"""
        if not sim_info.iccid:
            return
        
        try:
            if len(sim_info.iccid) >= 19:
                sim_info.iin = sim_info.iccid[:7]
                sim_info.account_id = sim_info.iccid[7:-1]
                sim_info.check_digit = sim_info.iccid[-1]
                sim_info.iccid_valid = self._luhn_check(sim_info.iccid)
                        
        except Exception as e:
            print(f"Error parsing ICCID: {e}")
    
    def _luhn_check(self, number: str) -> bool:
        """ตรวจสอบ Luhn checksum"""
        try:
            digits = [int(d) for d in number]
            checksum = 0
            
            for i in range(len(digits) - 2, -1, -2):
                digits[i] *= 2
                if digits[i] > 9:
                    digits[i] -= 9
            
            checksum = sum(digits)
            return checksum % 10 == 0
            
        except:
            return False
    
    def _validate_sim_info(self, sim_info: SIMIdentityInfo):
        """ตรวจสอบความถูกต้องของข้อมูล SIM"""
        try:
            if not sim_info.imsi or len(sim_info.imsi) != 15:
                sim_info.sim_valid = False
                return
            
            if sim_info.mcc not in self.mcc_database:
                sim_info.sim_valid = False
                
        except Exception as e:
            print(f"Error validating SIM: {e}")
    
    def start_monitoring(self):
        """เริ่มการตรวจสอบ"""
        if not self.serial_thread or not self.serial_thread.isRunning():
            self.error_occurred.emit("No active serial connection available")
            return
            
        self.monitoring = True
        self.start()
        
    def stop_monitoring(self):
        """หยุดการตรวจสอบ"""
        self.monitoring = False
        self.current_command = None
        self.temp_responses.clear()
        self.quit()
        self.wait()

class EnhancedSIMSignalQualityWindow(QDialog):
    """Enhanced Signal Quality Window with SIM Information"""
    
    def __init__(self, port: str = "", baudrate: int = 115200, parent=None, serial_thread=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.parent_window = parent
        self.shared_serial_thread = serial_thread
        self.monitoring_thread = None
        self.measurements_history = []
        self.auto_scroll = True
        self.sim_identity = None  # Store SIM info
        self.setup_signal_response_display()
        
        self.setup_ui()
        self.apply_styles()
        
        if self.shared_serial_thread and self.shared_serial_thread.isRunning():
            self.connection_status.setText("Using shared connection")
            self.start_btn.setEnabled(True)
        else:
            self.connection_status.setText("🔴 No shared connection")
            self.start_btn.setEnabled(False)
            QMessageBox.warning(self, "Connection Required", 
                              "Please ensure the main window has an active serial connection before using Signal Quality Checker.")
    
    def setup_signal_response_display(self):
        """เพิ่ม response display สำหรับ Signal Quality commands"""
        # เพิ่มใน create_realtime_panel หรือ create_analysis_panel
        signal_response_group = QGroupBox("Signal Commands & Responses")
        response_layout = QVBoxLayout()
        
        self.signal_response_display = QTextEdit()
        self.signal_response_display.setReadOnly(True)
        self.signal_response_display.setMaximumHeight(120)
        self.signal_response_display.setPlaceholderText("Signal quality commands and responses...")
        self.signal_response_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
        """)
        
        response_layout.addWidget(self.signal_response_display)
        signal_response_group.setLayout(response_layout)
        
        return signal_response_group
        
    def setup_ui(self):
        self.setWindowTitle("📶 Enhanced SIM Signal Quality Checker")
        self.setMinimumSize(1300, 900)
        self.resize(1300, 900)
        self.setModal(False)
        
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
                           Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Control Panel
        self.create_control_panel(layout)
        
        # Main Content (Splitter)
        self.create_main_content(layout)
    
    def create_control_panel(self, layout):
        control_frame = QGroupBox("🎛️ Controls & SIM Information")
        control_frame.setFixedHeight(160)  
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 12)
        main_layout.setSpacing(12)
        
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(20)
        
        # Connection Status
        self.connection_status = QLabel("🔴 Checking...")
        self.connection_status.setFont(QFont("Arial", 12, QFont.Bold))
        self.connection_status.setMinimumWidth(200)
        row1_layout.addWidget(self.connection_status)
        
        # SIM Quick Info
        self.sim_quick_info = QLabel("📱 SIM: Loading...")
        self.sim_quick_info.setFont(QFont("Arial", 11))
        self.sim_quick_info.setMinimumWidth(300)
        row1_layout.addWidget(self.sim_quick_info)
        
        row1_layout.addStretch()
        
        # Status & Time
        self.status_label = QLabel("Ready to start monitoring...")
        self.status_label.setFont(QFont("Arial", 11))
        self.status_label.setAlignment(Qt.AlignRight)
        row1_layout.addWidget(self.status_label)
        
        separator1 = QLabel("|")
        separator1.setFont(QFont("Arial", 12))
        row1_layout.addWidget(separator1)
        
        self.start_time_label = QLabel("")
        self.start_time_label.setFont(QFont("Arial", 11))
        self.start_time_label.setAlignment(Qt.AlignRight)
        self.start_time_label.setMinimumWidth(130)
        row1_layout.addWidget(self.start_time_label)
        
        main_layout.addLayout(row1_layout)
        
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(15)
        
        self.imsi_label = QLabel("IMSI: --")
        self.imsi_label.setFont(QFont("Arial", 10))
        self.imsi_label.setMinimumWidth(200)
        row2_layout.addWidget(self.imsi_label)
        
        self.iccid_label = QLabel("ICCID: --")
        self.iccid_label.setFont(QFont("Arial", 10))
        self.iccid_label.setMinimumWidth(200)
        row2_layout.addWidget(self.iccid_label)
        
        row2_layout.addStretch()
        main_layout.addLayout(row2_layout)
        
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(18)
        
        conn_info = QLabel(f"Port: {self.port}")
        conn_info.setFont(QFont("Arial", 11))
        row3_layout.addWidget(conn_info)
        
        separator2 = QLabel("|")
        separator2.setFont(QFont("Arial", 12))
        row3_layout.addWidget(separator2)
        
        # Interval Setting
        interval_label = QLabel("Interval:")
        interval_label.setFont(QFont("Arial", 11))
        row3_layout.addWidget(interval_label)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix("s")
        self.interval_spin.setFixedSize(65, 32)
        self.interval_spin.setFont(QFont("Arial", 10))
        row3_layout.addWidget(self.interval_spin)
        
        # Include SIM Info checkbox
        self.include_sim_check = QCheckBox("Include SIM Info")
        self.include_sim_check.setChecked(True)
        self.include_sim_check.setFont(QFont("Arial", 11))
        row3_layout.addWidget(self.include_sim_check)
        
        # Auto Scroll
        self.auto_scroll_check = QCheckBox("Auto Scroll")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.setFont(QFont("Arial", 11))
        row3_layout.addWidget(self.auto_scroll_check)
        
        # Control Buttons
        self.start_btn = QPushButton("▶️ Start")
        self.start_btn.setFixedSize(85, 32)
        self.start_btn.setFont(QFont("Arial", 10))
        row3_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setFixedSize(75, 32)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setFont(QFont("Arial", 10))
        row3_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setFixedSize(75, 32)
        self.clear_btn.setFont(QFont("Arial", 10))
        row3_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("📊 Export")
        self.export_btn.setFixedSize(85, 32)
        self.export_btn.setFont(QFont("Arial", 10))
        row3_layout.addWidget(self.export_btn)
        
        row3_layout.addStretch()
        
        main_layout.addLayout(row3_layout)
        
        control_frame.setLayout(main_layout)
        layout.addWidget(control_frame)
        
        # Connect signals
        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.clear_btn.clicked.connect(self.clear_data)
        self.export_btn.clicked.connect(self.export_data)
        self.auto_scroll_check.toggled.connect(self.toggle_auto_scroll)
    
    def create_main_content(self, layout):
        splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel - Real-time Display
        left_panel = self.create_realtime_panel()
        splitter.addWidget(left_panel)
        
        # Right Panel - Data & Analysis
        right_panel = self.create_analysis_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([650, 650])
        layout.addWidget(splitter)
    
    def create_realtime_panel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Current Signal Status
        current_group = QGroupBox("📊 Current Signal Status")
        current_layout = QGridLayout()
        
        self.current_labels = {}
        status_items = [
            ("RSSI:", "rssi", "--"),
            ("Quality:", "quality", "--"),
            ("Bars:", "bars", "--"),
            ("Carrier:", "carrier", "--"),
            ("Network:", "network", "--"),
            ("BER:", "ber", "--")
        ]
        
        for i, (label_text, key, default) in enumerate(status_items):
            label = QLabel(label_text)
            value = QLabel(default)
            value.setFont(QFont("Courier New", 12, QFont.Bold))
            
            row = i // 2
            col = (i % 2) * 2
            current_layout.addWidget(label, row, col)
            current_layout.addWidget(value, row, col + 1)
            
            self.current_labels[key] = value
        
        current_group.setLayout(current_layout)
        layout.addWidget(current_group)

        # เพิ่ม Signal Response Display
        signal_response_group = self.setup_signal_response_display()
        layout.addWidget(signal_response_group)
        
        # Signal Graph
        graph_group = QGroupBox("📈 Real-time Signal Graph")
        graph_layout = QVBoxLayout()
        
        self.signal_graph = ScrollableSignalGraph() if ENABLE_GRAPH_SCROLLING else SignalVisualizationWidget()
        graph_layout.addWidget(self.signal_graph)

        self.signal_graph.pointSelected.connect(self.on_graph_point_selected)

        if ENABLE_GRAPH_SCROLLING:
            self.graph_auto_check = QCheckBox("Follow live")
            self.graph_auto_check.setChecked(True)
            self.graph_auto_check.toggled.connect(
                lambda on: getattr(self.signal_graph, "set_follow_live", lambda *_: None)(on)
            )
            graph_layout.addWidget(self.graph_auto_check)

            self.graph_slider = QSlider(Qt.Horizontal)
            self.graph_slider.setMinimum(0)
            self.graph_slider.setSingleStep(1)
            self.graph_slider.setEnabled(True)
            self.graph_slider.valueChanged.connect(
                lambda v: (
                    getattr(self.signal_graph, "set_view_start", lambda *_: None)(v),
                    self.graph_auto_check.setChecked(False)
                )
            )
            graph_layout.addWidget(self.graph_slider)

        graph_group.setLayout(graph_layout)
        layout.addWidget(graph_group)
        
        # Signal Strength Indicator - แก้ไขส่วนนี้
        indicator_group = QGroupBox("📶 Signal Strength")
        indicator_layout = QVBoxLayout()
        
        # สร้าง HBoxLayout สำหรับแถวแรก
        row = QHBoxLayout()  # ← เพิ่มบรรทัดนี้
        
        # วิดเจ็ตแท่งสัญญาณแบบอนิเมชั่น
        self.signal_widget = SignalStrengthWidget()
        self.signal_widget.setToolTip("Live Signal (animated)")

        # ตัวเลข (x/5)
        self.signal_count_lbl = QLabel("(0/5)")
        self.signal_count_lbl.setAlignment(Qt.AlignVCenter)
        self.signal_count_lbl.setMinimumWidth(48)

        # row.addWidget(icon_lbl)
        row.addWidget(self.signal_widget, 1)
        row.addWidget(self.signal_count_lbl)

        indicator_layout.addLayout(row)

        # สไลเดอร์คุณภาพ (คงไว้เหมือนเดิม)
        self.signal_slider = QSlider(Qt.Horizontal)
        self.signal_slider.setRange(0, 100)
        self.signal_slider.setEnabled(False)
        indicator_layout.addWidget(self.signal_slider)

        # ป้ายคุณภาพ (คงไว้เหมือนเดิม)
        self.quality_label = QLabel("Quality: 0%")
        self.quality_label.setAlignment(Qt.AlignCenter)
        indicator_layout.addWidget(self.quality_label)
        
        indicator_group.setLayout(indicator_layout)
        layout.addWidget(indicator_group)
        
        panel.setLayout(layout)
        return panel
    
    def on_graph_point_selected(self, global_index: int, m: SignalMeasurement):
        """เมื่อผู้ใช้คลิกจุดบนกราฟ: เลือกแถวในตารางและอัปเดตกล่อง Current Signal Status"""
        try:
            # อัปเดต Current Signal Status
            self.current_labels['rssi'].setText(f"{m.rssi} dBm")
            self.current_labels['quality'].setText(f"{m.quality_score:.1f}%")
            self.current_labels['bars'].setText(f"{m.signal_bars}/5")
            self.current_labels['carrier'].setText(m.carrier)
            self.current_labels['network'].setText(m.network_type)
            ber_text, ber_tip, ber_unknown = self._format_ber_text(m.ber)
            self.current_labels['ber'].setText(ber_text)
            if ber_tip:
                self.current_labels['ber'].setToolTip(ber_tip)

            self.signal_widget.set_level(m.signal_bars)
            self.signal_count_lbl.setText(f"({m.signal_bars}/5)")
            self.signal_slider.setValue(int(m.quality_score))
            self.quality_label.setText(f"Quality: {m.quality_score:.1f}%")

            # คำนวดแถวในตารางจากดัชนีใน history
            total_rows = self.measurements_table.rowCount()
            total_hist = len(self.measurements_history)
            # ตารางจะลบหัวเมื่อเกิน 1000 แถว (ดู add_measurement_to_table) → หา offset ให้ตรง
            # (เมื่อ removeRow(0) คอลัมน์ # จะเลื่อนลงหนึ่ง)
            offset = max(0, total_hist - total_rows)
            row = max(0, min(global_index - offset, total_rows - 1))

            if total_rows > 0:
                self.measurements_table.selectRow(row)
                item = self.measurements_table.item(row, 0) or self.measurements_table.item(row, 1)
                if item:
                    self.measurements_table.scrollToItem(item)
            # แถบสถานะด้านบน
            self.status_label.setText(
                f"📍 #{global_index+1} at {m.timestamp} | RSSI {m.rssi} dBm | Q {m.quality_score:.1f}%"
            )
        except Exception as e:
            print(f"Error selecting point from graph: {e}")

    
    def create_analysis_panel(self):
        # แผงหลักด้านขวา
        panel = QWidget()

        # ผูกเลย์เอาต์เข้ากับ panel ตั้งแต่ตอนสร้าง (กันพลาด)
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)

        # แท็บหลัก
        tabs = QTabWidget(panel)

        # สำคัญ: เมธอดเหล่านี้ต้อง return QWidget เสมอ
        # ถ้าปัจจุบัน return เป็น QLayout หรือ int ให้แก้ให้ return QWidget ที่ setLayout เรียบร้อย
        sim_tab = self.create_sim_info_tab()              # ต้องเป็น QWidget
        meas_tab = self.create_measurements_tab()         # ต้องเป็น QWidget
        stats_tab = self.create_statistics_tab()          # ต้องเป็น QWidget
        rec_tab = self.create_recommendations_tab()       # ต้องเป็น QWidget

        tabs.addTab(sim_tab, "📱 SIM Info")
        tabs.addTab(meas_tab, "📋 Measurements")
        tabs.addTab(stats_tab, "📊 Statistics")
        tabs.addTab(rec_tab, "💡 Recommendations")

        vbox.addWidget(tabs)
        return panel
    
    def create_sim_info_tab(self):
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        # SIM Identity Section
        identity_group = QGroupBox("📱 SIM Identity")
        identity_layout = QGridLayout()
        
        self.sim_labels = {}
        
        # IMSI Information
        imsi_items = [
            ("Full IMSI:", "imsi_full"),
            ("MCC (Country Code):", "mcc_info"),
            ("MNC (Network Code):", "mnc_info"),
            ("MSIN (Subscriber ID):", "msin"),
            ("Country:", "country"),
            ("Home Network:", "home_network"),
            ("Phone Number:", "phone_number")
        ]
        
        for i, (label_text, key) in enumerate(imsi_items):
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 11))
            value = QLabel("Loading...")
            value.setFont(QFont("Courier New", 11))
            value.setWordWrap(True)
            
            identity_layout.addWidget(label, i, 0)
            identity_layout.addWidget(value, i, 1)
            self.sim_labels[key] = value
        
        identity_group.setLayout(identity_layout)
        layout.addWidget(identity_group)
        
        # ICCID Information Section
        iccid_group = QGroupBox("💳 ICCID Information")
        iccid_layout = QGridLayout()
        
        iccid_items = [
            ("Full ICCID:", "iccid_full"),
            ("IIN (Issuer ID):", "iin"),
            ("Account ID:", "account_id"),
            ("Check Digit:", "check_digit"),
            ("ICCID Valid:", "iccid_valid"),
            ("Card Length:", "card_length")
        ]
        
        for i, (label_text, key) in enumerate(iccid_items):
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 11))
            value = QLabel("Loading...")
            value.setFont(QFont("Courier New", 11))
            
            iccid_layout.addWidget(label, i, 0)
            iccid_layout.addWidget(value, i, 1)
            self.sim_labels[key] = value
        
        iccid_group.setLayout(iccid_layout)
        layout.addWidget(iccid_group)
        
        # Network Analysis Section
        network_group = QGroupBox("🌐 Network Analysis")
        network_layout = QGridLayout()
        
        network_items = [
            ("Current Carrier:", "current_carrier"),
            ("Network Type:", "network_type_detail"),
            ("Roaming Status:", "roaming_status"),
            ("SIM Validation:", "sim_validation"),
            ("Signal Quality:", "signal_assessment")
        ]
        
        for i, (label_text, key) in enumerate(network_items):
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 11))
            value = QLabel("--")
            value.setFont(QFont("Courier New", 11))
            
            network_layout.addWidget(label, i, 0)
            network_layout.addWidget(value, i, 1)
            self.sim_labels[key] = value
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        self.database_text = QTextEdit()
        self.database_text.setReadOnly(True)
        self.database_text.setMaximumHeight(150)
        self.database_text.setFont(QFont("Courier New", 10))
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        return tab
    
    def create_measurements_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.measurements_table = QTableWidget(0, 11) 
        self.measurements_table.setHorizontalHeaderLabels([
            "#",           
            "Time", 
            "RSSI (dBm)", 
            "Quality (%)", 
            "Bars", 
            "RSRP (dBm)", 
            "RSRQ (dB)", 
            "BER (%)", 
            "Carrier",
            "MCC", 
            "MNC"
        ])
        
        header = self.measurements_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        self.measurements_table.verticalHeader().setDefaultSectionSize(25)
        self.measurements_table.verticalHeader().setVisible(False)
        
        table_font = QFont("Arial", 10)
        self.measurements_table.setFont(table_font)
        
        column_widths = [40, 70, 85, 80, 50, 85, 80, 70, 120, 60, 60]  
        for i, width in enumerate(column_widths):
            self.measurements_table.setColumnWidth(i, width)
        
        layout.addWidget(self.measurements_table)
        
        # Summary info
        summary_layout = QHBoxLayout()
        self.total_measurements_label = QLabel("Total: 0 measurements")
        self.avg_quality_label = QLabel("Avg Quality: 0%")
        self.monitoring_time_label = QLabel("Time: 00:00:00")
        
        summary_font = QFont("Arial", 10)
        self.total_measurements_label.setFont(summary_font)
        self.avg_quality_label.setFont(summary_font)
        self.monitoring_time_label.setFont(summary_font)
        
        summary_layout.addWidget(self.total_measurements_label)
        summary_layout.addWidget(self.avg_quality_label)
        summary_layout.addWidget(self.monitoring_time_label)
        summary_layout.addStretch()
        
        layout.addLayout(summary_layout)
        
        tab.setLayout(layout)
        return tab
    
    def create_statistics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Statistics Display
        stats_group = QGroupBox("📊 Signal Statistics")
        stats_layout = QGridLayout()
        
        self.stats_labels = {}
        stats_items = [
            ("Average RSSI:", "avg_rssi"),
            ("Min RSSI:", "min_rssi"),
            ("Max RSSI:", "max_rssi"),
            ("Signal Range:", "range_rssi"),
            ("Average Quality:", "avg_quality"),
            ("Best Quality:", "max_quality"),
            ("Worst Quality:", "min_quality"),
            ("Stability Score:", "stability")
        ]
        
        for i, (label_text, key) in enumerate(stats_items):
            label = QLabel(label_text)
            value = QLabel("--")
            value.setFont(QFont("Courier New", 11))
            
            row = i // 2
            col = (i % 2) * 2
            stats_layout.addWidget(label, row, col)
            stats_layout.addWidget(value, row, col + 1)
            
            self.stats_labels[key] = value
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Quality Distribution
        dist_group = QGroupBox("📈 Quality Distribution")
        dist_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
        dist_layout = QVBoxLayout()
        
        self.distribution_text = QTextEdit()
        self.distribution_text.setReadOnly(True)
        self.distribution_text.setFont(QFont("Courier New", 11))
        self.distribution_text.setMinimumHeight(360)
        self.distribution_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        dist_layout.addWidget(self.distribution_text)
        
        dist_group.setLayout(dist_layout)
        layout.addWidget(dist_group, 1)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_recommendations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Recommendations
        rec_group = QGroupBox("💡 Signal Optimization & SIM Recommendations")
        rec_layout = QVBoxLayout()
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setFont(QFont("Arial", 11))
        rec_layout.addWidget(self.recommendations_text)
        
        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)
        
        tab.setLayout(layout)
        return tab
    
    def start_monitoring(self):
        try:
            if not self.shared_serial_thread or not self.shared_serial_thread.isRunning():
                QMessageBox.warning(self, "Connection Required", 
                                  "No active serial connection available.\nPlease ensure the main window is connected.")
                return
            
            interval = self.interval_spin.value()
            include_sim = self.include_sim_check.isChecked()
            
            self.stop_monitoring()
            
            self.monitoring_thread = EnhancedSignalQualityThread(
                self.shared_serial_thread, interval, include_sim
            )
            
            self.monitoring_thread.signal_measured.connect(self.update_signal_display)
            self.monitoring_thread.status_updated.connect(self.update_connection_status)
            self.monitoring_thread.error_occurred.connect(self.handle_error)
            self.monitoring_thread.sim_info_updated.connect(self.update_sim_info_display)
            
            # เพิ่มบรรทัดนี้
            if hasattr(self.monitoring_thread, 'command_response_signal'):
                self.monitoring_thread.command_response_signal.connect(self.update_signal_response_display)
            
            self.monitoring_thread.start_monitoring()

            # หลังจาก self.monitoring_thread.start_monitoring()
            if hasattr(self.parent, 'display_manager'):
                self.parent.display_manager.filter_manager.set_signal_monitoring(True)
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.interval_spin.setEnabled(False)
            self.include_sim_check.setEnabled(False)
            
            self.start_time = datetime.now()
            self.start_time_label.setText(f"Started: {self.start_time.strftime('%H:%M:%S')}")
            self.status_label.setText("🚀 Starting monitoring...")
            
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_monitoring_time)
            self.timer.start(1000)
            
        except Exception as e:
            QMessageBox.warning(self, "Start Error", f"Failed to start monitoring: {e}")
    
    def update_signal_response_display(self, text):
        """อัพเดตการแสดงผล response ของ Signal Quality"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_text = f"[{timestamp}] {text}"
        
        current_text = self.signal_response_display.toPlainText()
        if current_text:
            self.signal_response_display.setPlainText(current_text + "\n" + formatted_text)
        else:
            self.signal_response_display.setPlainText(formatted_text)
        
        # เลื่อนไปท้ายสุด
        cursor = self.signal_response_display.textCursor()
        cursor.movePosition(cursor.End)
        self.signal_response_display.setTextCursor(cursor)

        # จำกัดจำนวนบรรทัด
        lines = self.signal_response_display.toPlainText().split('\n')
        if len(lines) > 100:
            self.signal_response_display.setPlainText('\n'.join(lines[-100:]))

    def stop_monitoring(self):
        try:
            if self.monitoring_thread:
                self.monitoring_thread.stop_monitoring()
                self.monitoring_thread = None
            
            if hasattr(self, 'timer'):
                self.timer.stop()
            
            # … หลัง self.timer.stop() และก่อน/หลังตั้งสถานะปุ่มก็ได้
            p = getattr(self, 'parent', None)
            if p and hasattr(p, 'display_manager'):
                p.display_manager.filter_manager.set_signal_monitoring(False)

            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.interval_spin.setEnabled(True)
            self.include_sim_check.setEnabled(True)
            
            if self.shared_serial_thread and self.shared_serial_thread.isRunning():
                self.connection_status.setText("Using shared connection")
                self.status_label.setText("⏹️ Monitoring stopped - Connection available")
            else:
                self.connection_status.setText("🔴 No shared connection")
                self.status_label.setText("⏹️ Monitoring stopped - No connection")
            
        except Exception as e:
            print(f"Error stopping monitoring: {e}")
    
    def update_sim_info_display(self, sim_info: SIMIdentityInfo):
        try:
            self.sim_identity = sim_info
            
            if sim_info.carrier and sim_info.country:
                self.sim_quick_info.setText(f"📱 SIM: {sim_info.carrier} ({sim_info.country})")
            else:
                self.sim_quick_info.setText("📱 SIM: Information loaded")
            
            self.imsi_label.setText(f"IMSI: {sim_info.imsi or '--'}")
            self.iccid_label.setText(f"ICCID: {sim_info.iccid or '--'}")
            
            self.sim_labels['imsi_full'].setText(sim_info.imsi or "Not available")
            self.sim_labels['mcc_info'].setText(f"{sim_info.mcc} ({sim_info.country})" if sim_info.mcc else "Not available")
            self.sim_labels['mnc_info'].setText(f"{sim_info.mnc} ({sim_info.carrier})" if sim_info.mnc else "Not available")
            self.sim_labels['msin'].setText(sim_info.msin or "Not available")
            self.sim_labels['country'].setText(sim_info.country or "Unknown")
            self.sim_labels['home_network'].setText("✅ Yes" if sim_info.home_network else "❌ No (Roaming)")
            self.sim_labels['phone_number'].setText(sim_info.phone_number or "Not available")
            
            # ICCID Info
            self.sim_labels['iccid_full'].setText(sim_info.iccid or "Not available")
            self.sim_labels['iin'].setText(sim_info.iin or "Not available")
            self.sim_labels['account_id'].setText(sim_info.account_id or "Not available")
            self.sim_labels['check_digit'].setText(sim_info.check_digit or "Not available")
            self.sim_labels['iccid_valid'].setText("✅ Valid" if sim_info.iccid_valid else "❌ Invalid")
            self.sim_labels['card_length'].setText(f"{len(sim_info.iccid)} digits" if sim_info.iccid else "Unknown")
            
            # Network Analysis
            self.sim_labels['current_carrier'].setText(sim_info.carrier or "Unknown")
            self.sim_labels['roaming_status'].setText("❌ Roaming" if sim_info.roaming else "🏠 Home Network")
            self.sim_labels['sim_validation'].setText("✅ Valid SIM" if sim_info.sim_valid else "❌ Invalid SIM")
            
        except Exception as e:
            print(f"Error updating SIM info display: {e}")
    
    def get_iso_code(self, mcc: str) -> str:
        mcc_db = {
            "520": "TH", "525": "SG", "502": "MY", "510": "ID",
            "515": "PH", "454": "HK", "460": "CN", "405": "IN", "310": "US"
        }
        return mcc_db.get(mcc, "Unknown")
    
    def get_network_type(self, mcc: str, mnc: str) -> str:
        if mcc == "520":  # Thailand
            thai_mnc = {
                "00": "GSM", "01": "GSM/3G/4G/5G", "03": "3G/4G/5G",
                "05": "GSM/3G/4G/5G", "15": "3G/4G/5G", "18": "3G/4G/5G",
                "23": "4G/5G", "25": "4G/5G", "47": "4G/5G", "99": "GSM/3G"
            }
            return thai_mnc.get(mnc, "Unknown")
        return "Unknown"
    
    def _format_ber_text(self, ber: float):
        if ber >= 99:
            return ("--", "BER not available (reported as 99)", True)
        return (f"{ber:.1f}%", None, False)

    
    def update_signal_display(self, measurement: SignalMeasurement):
        try:
            self.measurements_history.append(measurement)
            
            self.current_labels['rssi'].setText(f"{measurement.rssi} dBm")
            self.current_labels['quality'].setText(f"{measurement.quality_score:.1f}%")
            self.current_labels['bars'].setText(f"{measurement.signal_bars}/5")
            self.current_labels['carrier'].setText(measurement.carrier)
            self.current_labels['network'].setText(measurement.network_type)
            ber_text, ber_tip, ber_unknown = self._format_ber_text(measurement.ber)
            self.current_labels['ber'].setText(ber_text)
            if ber_tip:
                self.current_labels['ber'].setToolTip(ber_tip)
            if ber_unknown:
                self.current_labels['ber'].setStyleSheet("color: #6c757d; font-weight: bold;")
            else:
                self.current_labels['ber'].setStyleSheet("")
            
            quality_color = self.get_quality_color(measurement.quality_score)
            self.current_labels['quality'].setStyleSheet(f"color: {quality_color}; font-weight: bold;")
            
            bars_visual = self.create_signal_bars_visual(measurement.signal_bars)
            self.signal_widget.set_level(measurement.signal_bars)   # อัปเดตแท่ง
            self.signal_count_lbl.setText(f"({measurement.signal_bars}/5)")

            
            self.signal_slider.setValue(int(measurement.quality_score))
            self.quality_label.setText(f"Quality: {measurement.quality_score:.1f}%")
            
            self.signal_graph.add_measurement(measurement)
            if ENABLE_GRAPH_SCROLLING and hasattr(self, "graph_slider") and hasattr(self.signal_graph, "_history"):
                hist_len = len(self.signal_graph._history)
                win = getattr(self.signal_graph, "_window_size", 50)
                max_start = max(0, hist_len - win)

                self.graph_slider.blockSignals(True)
                self.graph_slider.setMaximum(max_start)
                if getattr(self.signal_graph, "_follow_live", True):
                    self.graph_slider.setValue(max_start)
                self.graph_slider.blockSignals(False)
            
            self.add_measurement_to_table(measurement)
            
            self.update_statistics()
            
            self.update_recommendations()
            
            if hasattr(self, 'sim_labels'):
                self.sim_labels['network_type_detail'].setText(measurement.network_type)
                
                numeric_quality_text = f"{measurement.rssi} dBm | {measurement.quality_score:.1f}%"
                self.sim_labels['signal_assessment'].setText(numeric_quality_text)
            
        except Exception as e:
            print(f"Error updating signal display: {e}")
    
    def add_measurement_to_table(self, measurement: SignalMeasurement):
        try:
            row = self.measurements_table.rowCount()
            self.measurements_table.insertRow(row)

            if row >= 1000:
                self.measurements_table.removeRow(0)
                row = 999
                self._update_row_numbers()

            mcc = measurement.sim_info.mcc if measurement.sim_info else "--"
            mnc = measurement.sim_info.mnc if measurement.sim_info else "--"

            row_number = row + 1

            ber_text, ber_tip, ber_unknown = self._format_ber_text(measurement.ber)

            items = [
                str(row_number),
                measurement.timestamp,
                str(measurement.rssi),
                f"{measurement.quality_score:.1f}",
                str(measurement.signal_bars),
                str(measurement.rsrp) if measurement.rsrp > -999 else "--",
                str(measurement.rsrq) if measurement.rsrq > -999 else "--",
                ber_text.replace("%",""),  
                measurement.carrier,
                mcc,
                mnc
            ]

            for col, text in enumerate(items):
                table_item = QTableWidgetItem(text)

                if col == 3:
                    color = QColor(self.get_quality_color(measurement.quality_score))
                    table_item.setForeground(color)

                elif col == 0:
                    table_item.setForeground(QColor("#6c757d"))
                    table_item.setTextAlignment(Qt.AlignCenter)

                elif col == 7 and ber_unknown:
                    table_item.setForeground(QColor("#6c757d"))      
                    table_item.setBackground(QColor("#f1f3f5"))      
                    if ber_tip:
                        table_item.setToolTip(ber_tip)

                self.measurements_table.setItem(row, col, table_item)

            if self.auto_scroll:
                self.measurements_table.scrollToBottom()

        except Exception as e:
            print(f"Error adding measurement to table: {e}")

    
    def update_connection_status(self, status: str):
        self.connection_status.setText(status)
        
        if "Connected" in status:
            self.status_label.setText("📶 Monitoring signal quality...")
        elif "stopped" in status:
            self.status_label.setText("⏹️ Monitoring stopped")
        elif "SIM Info loaded" in status:
            self.status_label.setText("📱 SIM information loaded successfully")
    
    def handle_error(self, error: str):
        self.status_label.setText(f"❌ Error: {error}")
        print(f"Monitoring error: {error}")
        
        if "connection" in error.lower():
            self.stop_monitoring()
    
    def update_statistics(self):
        try:
            if not self.measurements_history:
                return
            
            rssi_values = [m.rssi for m in self.measurements_history if m.rssi > -999]
            quality_values = [m.quality_score for m in self.measurements_history]
            
            if rssi_values and quality_values:
                self.stats_labels['avg_rssi'].setText(f"{sum(rssi_values)/len(rssi_values):.1f} dBm")
                self.stats_labels['min_rssi'].setText(f"{min(rssi_values)} dBm")
                self.stats_labels['max_rssi'].setText(f"{max(rssi_values)} dBm")
                self.stats_labels['range_rssi'].setText(f"{max(rssi_values) - min(rssi_values)} dB")
                
                self.stats_labels['avg_quality'].setText(f"{sum(quality_values)/len(quality_values):.1f}%")
                self.stats_labels['max_quality'].setText(f"{max(quality_values):.1f}%")
                self.stats_labels['min_quality'].setText(f"{min(quality_values):.1f}%")
                
                if len(rssi_values) > 1:
                    variance = sum((x - sum(rssi_values)/len(rssi_values))**2 for x in rssi_values) / (len(rssi_values) - 1)
                    stability = max(0, min(100, 100 - (variance * 2)))
                    self.stats_labels['stability'].setText(f"{stability:.1f}%")
            
            self.total_measurements_label.setText(f"Total: {len(self.measurements_history)} measurements")
            
            if quality_values:
                self.avg_quality_label.setText(f"Avg Quality: {sum(quality_values)/len(quality_values):.1f}%")
            
            self.create_quality_distribution()
            
        except Exception as e:
            print(f"Error updating statistics: {e}")

    @staticmethod
    def _calc_quality_from_rssi_ber(rssi: int, ber: float) -> float:
        if rssi is None or rssi <= -999: return 0.0
        rssi_score = max(0, min(100, (rssi + 113) * 100.0 / 62.0))
        ber_score  = 50.0 if ber is None or ber >= 99 else max(0, min(100, 100.0 - (ber * 10.0)))
        return (rssi_score * 0.7) + (ber_score * 0.3)

    def _quality_samples(self):
        samples = []
        for m in getattr(self, "measurements_history", []):
            if not m or m.rssi is None or m.rssi <= -999: 
                continue
            q = (m.quality_score if getattr(m, "quality_score", None) not in (None, 0)
                else self._calc_quality_from_rssi_ber(m.rssi, getattr(m, "ber", 99)))
            if q > 0: samples.append(q)
        return samples
    
    def _build_quality_distribution_text(self) -> str:
        qualities = self._quality_samples()
        total = len(qualities)
        header = ["📊 QUALITY DISTRIBUTION", "======================="]
        if total == 0:
            return "\n".join(header + ["", "No data yet — start monitoring to collect samples."])
        bins = [(90,101,"Excellent","🟢"), (80,90,"Very Good","✅"),
                (70,80,"Good","📶"), (60,70,"Fair","🟠"), (0,60,"Poor","🔴")]
        BAR_WIDTH = 42
        lines = header + [""]
        for lo, hi, label, icon in bins:
            c = sum(1 for q in qualities if lo <= q < hi)
            pct = (c/total)*100.0
            bar = "█"*round(pct/100*BAR_WIDTH) + "░"*(BAR_WIDTH-round(pct/100*BAR_WIDTH))
            lines.append(f"{icon} {label:<11} [{bar}] {c:>3} ({pct:>5.1f}%)")
        lines += ["", f"Total Measurements: {total}", f"Avg Quality: {sum(qualities)/total:.1f}%"]
        if getattr(self, "sim_identity", None):
            si = self.sim_identity
            lines.append(f"SIM: {si.carrier} (MCC: {si.mcc}, MNC: {si.mnc})")
        return "\n".join(lines)

    
    def create_quality_distribution(self):
        try:
            if not self.measurements_history:
                return
            
            ranges = [
                (90, 100, "Excellent", "🟢"),   # Office building = Excellent
                (80, 90, "Good", "✅"),         # Satellite antenna = Good
                (70, 80, "Fair", "📶"),         # Antenna bars = Fair
                (60, 70, "Poor", "🟠"),         # Red circle = Poor
                (0, 60, "Very Poor", "🔴")      # Warning sign = Very Poor
            ]

            distribution_text = "📊 QUALITY DISTRIBUTION\n"
            distribution_text += "=" * 40 + "\n\n"

            
            total = len(self.measurements_history)
            
            for min_q, max_q, label, icon in ranges:
                count = sum(1 for m in self.measurements_history 
                          if min_q <= m.quality_score <= max_q)
                percentage = (count / total * 100) if total > 0 else 0
                
                BAR_WIDTH = 40
                bar_length = round(percentage * BAR_WIDTH / 100)
                bar = "█" * bar_length + "░" * (BAR_WIDTH - bar_length)
                
                distribution_text += f"{icon} {label:<12} [{bar}] {count:>3} ({percentage:>5.1f}%)\n"
            
            distribution_text += f"\n📈 Total Measurements: {total}\n"
            
            if hasattr(self, 'start_time'):
                duration = datetime.now() - self.start_time
                distribution_text += f"⏱️ Monitoring Time: {str(duration).split('.')[0]}\n"
            
            if self.sim_identity:
                distribution_text += f"📱 SIM: {self.sim_identity.carrier} (MCC: {self.sim_identity.mcc}, MNC: {self.sim_identity.mnc})\n"
            
            self.distribution_text.setText(distribution_text)
            
        except Exception as e:
            print(f"Error creating quality distribution: {e}")
    
    def update_recommendations(self):
        try:
            if not self.measurements_history:
                return
            
            latest_measurement = self.measurements_history[-1]
            
            # แก้ไข: ใช้ f-string หรือ .format() ให้ถูกต้อง
            recommendations_text = f"""
🔍 ENHANCED SIGNAL ANALYSIS & RECOMMENDATIONS
=============================================

📱 Current Status:
• Signal Strength: {latest_measurement.rssi} dBm
• Quality Score: {latest_measurement.quality_score:.1f}%
• Signal Grade: {self.get_signal_grade(latest_measurement.rssi)}
• Network: {latest_measurement.network_type}
• Carrier: {latest_measurement.carrier}

"""
            # แก้ไข: ลบบรรทัดที่ไม่ได้ใช้งาน (recommendations_text.format(...))
            
            if latest_measurement.sim_info:
                sim_info = latest_measurement.sim_info
                # แก้ไข: เปลี่ยนอีโมจิจา 📏 เป็น 📱
                recommendations_text += f"""
📱 SIM Information:
• IMSI: {sim_info.imsi}
• MCC: {sim_info.mcc} ({sim_info.country})
• MNC: {sim_info.mnc} ({sim_info.carrier})
• ICCID: {sim_info.iccid[:8]}...{sim_info.iccid[-4:] if sim_info.iccid else ''}
• Home Network: {'✅ Yes' if sim_info.home_network else '❌ No (Roaming)'}
• SIM Valid: {'✅ Yes' if sim_info.sim_valid else '❌ No'}

"""
            
            recommendations = self.generate_recommendations()
            if recommendations:
                recommendations_text += "💡 Recommendations:\n"
                for rec in recommendations:
                    recommendations_text += f"   • {rec}\n"
            
            if len(self.measurements_history) >= 5:
                recent_quality = [m.quality_score for m in self.measurements_history[-5:]]
                trend = (
                    "📈 Improving" if recent_quality[-1] > recent_quality[0]
                    else "📉 Declining" if recent_quality[-1] < recent_quality[0]
                    else "➡️ Stable"
                )
                recommendations_text += f"\n📊 Recent Trend: {trend}\n"
            
            if self.sim_identity:
                # แก้ไข: เพิ่ม emoji ที่เหมาะสมและแก้ไขรูปแบบ
                roaming_status = '🌍 International Roaming' if self.sim_identity.roaming else '🏠 Home Network'
                iccid_validation = '✅ Passed' if self.sim_identity.iccid_valid else '❌ Failed'
                
                recommendations_text += f"""

📚 MCC/MNC Analysis:
• Country Code (MCC): {self.sim_identity.mcc} = {self.sim_identity.country}
• Network Code (MNC): {self.sim_identity.mnc} = {self.sim_identity.carrier}
• Network Type: {self.get_network_type(self.sim_identity.mcc, self.sim_identity.mnc)}
• ISO Country: {self.get_iso_code(self.sim_identity.mcc)}
• Roaming Status: {roaming_status}

💳 ICCID Analysis:
• Full ICCID: {self.sim_identity.iccid}
• Issuer ID (IIN): {self.sim_identity.iin}
• Check Digit Validation: {iccid_validation}
• Card Length: {len(self.sim_identity.iccid) if self.sim_identity.iccid else 0} digits

"""
            
            # แก้ไข: ปรับปรุงส่วน Connection Info
            connection_status = "✅ Active" if self.shared_serial_thread and self.shared_serial_thread.isRunning() else "❌ Inactive"
            sim_info_included = "✅ Yes" if self.include_sim_check.isChecked() else "❌ No"
            
            recommendations_text += f"""
🔗 Connection Info:
• Using shared serial connection from main window
• Port: {self.port}
• Baudrate: {self.baudrate}
• Connection status: {connection_status}
• SIM Info included: {sim_info_included}

📊 Monitoring Statistics:
• Total measurements: {len(self.measurements_history)}
• Average quality: {sum(m.quality_score for m in self.measurements_history) / len(self.measurements_history):.1f}%
• Best signal: {max(m.rssi for m in self.measurements_history if m.rssi > -999)} dBm
• Worst signal: {min(m.rssi for m in self.measurements_history if m.rssi > -999)} dBm

ℹ️ Note: This Signal Quality Checker uses the same serial connection as the main window.
If you see connection issues, please check the main window's serial connection.
"""
            
            # แก้ไข: เพิ่มการตั้งค่าข้อความและเลื่อนตำแหน่ง
            self.recommendations_text.setText(recommendations_text)
            
            # เลื่อนไปด้านบนเสมอ
            cursor = self.recommendations_text.textCursor()
            cursor.movePosition(cursor.Start)
            self.recommendations_text.setTextCursor(cursor)
            
        except Exception as e:
            error_msg = f"Error updating recommendations: {e}"
            print(error_msg)
            
            # แสดงข้อความ error ใน recommendations tab
            error_text = f"""
❌ ERROR IN RECOMMENDATIONS
==========================

An error occurred while generating recommendations:
{str(e)}

🔧 Troubleshooting:
• Check console for detailed error messages
• Verify SIM data is available  
• Restart monitoring if needed
• Check serial connection status

💡 Try:
• Stop and start monitoring again
• Check main window connection
• Verify port settings
• Restart the application if needed

Debug Info:
• Measurements: {len(self.measurements_history) if hasattr(self, 'measurements_history') else 'Unknown'}
• SIM Identity: {'Available' if hasattr(self, 'sim_identity') and self.sim_identity else 'Not available'}
• Serial Thread: {'Running' if hasattr(self, 'shared_serial_thread') and self.shared_serial_thread and self.shared_serial_thread.isRunning() else 'Not running'}
"""
            
            try:
                self.recommendations_text.setText(error_text)
            except:
                print("Failed to display error message in recommendations text widget")
    
    def generate_recommendations(self) -> List[str]:
        if not self.measurements_history:
            return []
        
        recommendations = []
        latest = self.measurements_history[-1]
        
        # Signal Quality Recommendations
        if latest.rssi < -100:
            recommendations.extend([
                "📍 Signal is weak - try moving to a better location",
                "🔧 Check antenna connection and positioning",
                "📡 Consider using a signal booster"
            ])
        elif latest.rssi < -85:
            recommendations.append("📶 Signal is fair - positioning might help")

        if latest.ber > 5.0:
            recommendations.extend([
                "⚪ High bit error rate detected",
                "🔄 Try reconnecting to network"
            ])

        if latest.quality_score < 50:
            recommendations.append("📞 Contact service provider if quality remains poor")

        # SIM-specific recommendations
        if latest.sim_info:
            sim_info = latest.sim_info
            
            if sim_info.roaming:
                recommendations.extend([
                    "🌍 Currently roaming - data charges may apply",
                    "📱 Consider local SIM for better rates"
                ])
            
            if not sim_info.sim_valid:
                recommendations.extend([
                    "⚠️ SIM validation failed - check SIM card",
                    "📱 Try removing and reinserting SIM card"
                ])
            
            if not sim_info.iccid_valid:
                recommendations.append("💳 ICCID validation failed - SIM card may be damaged")
            
            if sim_info.mcc == "520":  # Thailand
                if sim_info.mnc in ["01", "03", "23"]:  # AIS
                    recommendations.append("📡 AIS network - good coverage in urban areas")
                elif sim_info.mnc in ["05", "18"]:  # dtac
                    recommendations.append("📡 dtac network - strong 4G/5G coverage")
                elif sim_info.mnc in ["15", "25"]:  # TrueMove H
                    recommendations.append("📡 TrueMove H network - extensive rural coverage")
        
        if len(self.measurements_history) >= 10:
            recent_rssi = [m.rssi for m in self.measurements_history[-10:] if m.rssi > -999]
            if recent_rssi and (max(recent_rssi) - min(recent_rssi)) > 20:
                recommendations.append("⚡ Signal is unstable - check for interference")
        
        if not self.shared_serial_thread or not self.shared_serial_thread.isRunning():
            recommendations.append("🔒 Check main window serial connection for consistent monitoring")
        
        if not recommendations:
            recommendations.append("✅ Signal quality and SIM status are good - no issues detected")
        
        return recommendations
    
    def update_monitoring_time(self):
        if hasattr(self, 'start_time'):
            duration = datetime.now() - self.start_time
            duration_str = str(duration).split('.')[0]
            self.monitoring_time_label.setText(f"Time: {duration_str}")
    
    def toggle_auto_scroll(self, enabled: bool):
        self.auto_scroll = enabled
    
    def _update_row_numbers(self):
        try:
            for row in range(self.measurements_table.rowCount()):
                row_number = row + 1
                item = QTableWidgetItem(str(row_number))
                item.setForeground(QColor("#6c757d"))
                item.setTextAlignment(Qt.AlignCenter)
                self.measurements_table.setItem(row, 0, item)
        except Exception as e:
            print(f"Error updating row numbers: {e}")
    
    def clear_data(self):
        reply = QMessageBox.question(self, "Clear Data", 
                                "Are you sure you want to clear all measurement data?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.measurements_history.clear()
            self.measurements_table.setRowCount(0)
            self.signal_graph.clear_measurements()
            
            for label in self.current_labels.values():
                label.setText("--")
            
            for label in self.stats_labels.values():
                label.setText("--")
            
            self.signal_widget.set_level(0)
            self.signal_count_lbl.setText("(0/5)")

            self.signal_slider.setValue(0)
            self.quality_label.setText("Quality: 0%")
            self.distribution_text.clear()
            self.recommendations_text.clear()
            
            self.total_measurements_label.setText("Total: 0 measurements")
            self.avg_quality_label.setText("Avg Quality: 0%")

    def export_data(self):
        if not self.measurements_history:
            QMessageBox.warning(self, "No Data", "No measurement data to export")
            return
        
        try:
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"Enhanced_Signal_Quality_Data_{timestamp}.csv"
            
            # Show file dialog to let user choose save location
            from PyQt5.QtWidgets import QFileDialog
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Signal Quality Data",
                default_filename,  # Default filename
                "CSV Files (*.csv);;All Files (*.*)",
                # options=QFileDialog.DontUseNativeDialog
            )
            
            # If user cancelled the dialog, filename will be empty
            if not filename:
                return
            
            # Ensure .csv extension if not provided
            if not filename.lower().endswith('.csv'):
                filename += '.csv'
            
            # Write the data to the selected file
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                f.write("Row_Number,Timestamp,RSSI_dBm,Quality_Percent,Signal_Bars,RSRP_dBm,RSRQ_dB,BER_Percent,")
                f.write("Carrier,Network_Type,MCC,MNC,IMSI,ICCID,Country,Home_Network\n")
                
                for i, m in enumerate(self.measurements_history, 1):  
                    sim_info = m.sim_info
                    f.write(f"{i},{m.timestamp},{m.rssi},{m.quality_score:.1f},{m.signal_bars},")  
                    f.write(f"{m.rsrp if m.rsrp > -999 else ''},{m.rsrq if m.rsrq > -999 else ''},")
                    f.write(f"{m.ber if m.ber < 99 else ''},{m.carrier},{m.network_type},")
                    
                    if sim_info:
                        f.write(f"{sim_info.mcc},{sim_info.mnc},{sim_info.imsi},")
                        f.write(f"{sim_info.iccid},{sim_info.country},{sim_info.home_network}\n")
                    else:
                        f.write(",,,,\n")
            
            QMessageBox.information(self, "Export Successful", 
                                f"Enhanced data exported successfully!\nFile: {filename}")
                                
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Failed to export data: {e}")

    def get_quality_color(self, quality: float) -> str:
        if quality >= 90:
            return "#2ecc71"  # Green
        elif quality >= 75:
            return "#f39c12"  # Orange  
        elif quality >= 50:
            return "#e67e22"  # Dark Orange
        elif quality >= 25:
            return "#e74c3c"  # Red
        else:
            return "#95a5a6"  # Gray
    
    def get_signal_grade(self, rssi: int) -> str:
        return f"{rssi} dBm"
    
    def create_signal_bars_visual(self, bars: int) -> str:
        filled = "█" * bars
        empty = "░" * (5 - bars)
        return f"📶 {filled}{empty} ({bars}/5)"
    
    def apply_styles(self):
        self.setStyleSheet(get_stylesheet())
    
    def closeEvent(self, event):
        try:
            self.stop_monitoring()
        except:
            pass
        event.accept()

class SignalVisualizationWidget(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.measurements = []
        self.max_points = 50
        self.setMinimumHeight(200)
        self.setStyleSheet("background-color: white; border: 1px solid #dc3545;")
        
    def add_measurement(self, measurement: SignalMeasurement):
        self.measurements.append(measurement)
        if len(self.measurements) > self.max_points:
            self.measurements.pop(0)
        self.update()
        
    def clear_measurements(self):
        self.measurements.clear()
        self.update()
        
    def paintEvent(self, event):
        """Enhanced paintEvent with gray zones for no signal"""
        if not self.measurements:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        margin = 40
        graph_rect = QRect(margin, margin, 
                          rect.width() - 2*margin, 
                          rect.height() - 2*margin)
        
        # Get valid RSSI values
        valid_rssi_values = [m.rssi for m in self.measurements if m.rssi > -999]
        
        if not valid_rssi_values:
            # No valid data - show gray background
            painter.setPen(QColor("#bdc3c7"))
            painter.setBrush(QColor("#ecf0f1"))
            painter.drawRect(graph_rect)
            
            painter.setPen(QColor("#7f8c8d"))
            font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(font)
            painter.drawText(graph_rect, Qt.AlignCenter, "No Signal Data")
            return
        
        # Calculate range from valid values
        min_rssi = min(valid_rssi_values)
        max_rssi = max(valid_rssi_values)
        
        if max_rssi == min_rssi:
            max_rssi = min_rssi + 10
        
        # Draw border
        painter.setPen(QColor("#dc3545"))
        painter.drawRect(graph_rect)
        
        # Draw Y-axis labels
        painter.setPen(QColor("#000000"))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        painter.drawText(5, margin, f"{max_rssi:.0f}")
        painter.drawText(5, margin + graph_rect.height()//2, f"{(max_rssi+min_rssi)/2:.0f}")
        painter.drawText(5, margin + graph_rect.height() - 5, f"{min_rssi:.0f}")
        
        # Draw gray zones for no-signal periods
        self._draw_no_signal_background(painter, graph_rect, min_rssi, max_rssi)
        
        # Draw signal lines and points
        self._draw_signal_data(painter, graph_rect, min_rssi, max_rssi)
    
    def _draw_no_signal_background(self, painter, graph_rect, min_rssi, max_rssi):
        """Draw gray background for no-signal periods"""
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(200, 200, 200, 100))
        
        for i, measurement in enumerate(self.measurements):
            if measurement.rssi <= -999:
                # Calculate X position for this no-signal point
                x = graph_rect.left() + (i * graph_rect.width() / max(1, len(self.measurements) - 1))
                
                # Draw a narrow gray rectangle
                gray_rect = QRect(
                    int(x - 5), 
                    graph_rect.top(),
                    10,
                    graph_rect.height()
                )
                painter.drawRect(gray_rect)
    
    def _draw_signal_data(self, painter, graph_rect, min_rssi, max_rssi):
        """Draw signal lines and points"""
        # Collect valid points
        valid_points = []
        for i, measurement in enumerate(self.measurements):
            if measurement.rssi > -999:
                x = graph_rect.left() + (i * graph_rect.width() / max(1, len(self.measurements) - 1))
                y = graph_rect.bottom() - ((measurement.rssi - min_rssi) * graph_rect.height() / (max_rssi - min_rssi))
                valid_points.append((int(x), int(y), i))
        
        # Draw lines between valid points
        if len(valid_points) > 1:
            painter.setPen(QColor("#dc3545"))
            painter.setBrush(Qt.NoBrush)
            
            for i in range(1, len(valid_points)):
                prev_x, prev_y, _ = valid_points[i-1]
                curr_x, curr_y, _ = valid_points[i]
                painter.drawLine(prev_x, prev_y, curr_x, curr_y)
        
        # Draw valid signal points
        painter.setPen(QColor("#dc3545"))
        painter.setBrush(QColor("#dc3545"))
        
        for x, y, _ in valid_points:
            painter.drawEllipse(x-2, y-2, 4, 4)
        
        # Draw no-signal markers
        painter.setPen(QColor("#95a5a6"))
        painter.setBrush(Qt.NoBrush)
        
        for i, measurement in enumerate(self.measurements):
            if measurement.rssi <= -999:
                x = graph_rect.left() + (i * graph_rect.width() / max(1, len(self.measurements) - 1))
                y = graph_rect.bottom() - 10
                
                # Draw X marker
                painter.drawLine(int(x-3), int(y-3), int(x+3), int(y+3))
                painter.drawLine(int(x-3), int(y+3), int(x+3), int(y-3))

class ScrollableSignalGraph(SignalVisualizationWidget):
    pointSelected = pyqtSignal(int, SignalMeasurement)  # ส่ง (global_index, measurement)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []          
        self._view_start = 0        
        self._window_size = 50      
        self._follow_live = True    
        self._dragging = False
        self._last_x = 0
        self._click_moved = False  # ใหม่: แยก "ลาก" กับ "คลิก"

    def add_measurement(self, measurement):
        self._history.append(measurement) 
        self._on_new_point()

    def clear_measurements(self):
        self._history.clear()
        self._refresh_view_slice()
        self.update()

    # ---------- public controls ----------
    def set_follow_live(self, enabled: bool):
        self._follow_live = bool(enabled)
        if self._follow_live:
            self._snap_to_tail()
        self.update()

    def set_view_start(self, idx: int):
        if not self._history:
            return
        max_start = max(0, len(self._history) - self._window_size)
        self._view_start = max(0, min(int(idx), max_start))
        self._refresh_view_slice()
        self.update()

    def set_window_size(self, n: int):
        self._window_size = max(5, int(n))
        self._snap_to_tail()
        self._refresh_view_slice()
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._last_x = e.x()
            self._click_moved = False
            self.set_follow_live(False)

    def mouseMoveEvent(self, e):
        if self._dragging and self._history:
            dx = e.x() - self._last_x
            self._last_x = e.x()
            step = int(dx / 8)   
            if step:
                self.set_view_start(self._view_start - step)
                self._click_moved = True  # มีการลาก

    def mouseReleaseEvent(self, e):
        # ถ้าไม่ได้ลาก ให้ถือว่าเป็นการ "คลิกเลือกจุด"
        if e.button() == Qt.LeftButton and not self._click_moved and self.measurements:
            margin = 40
            rect = self.rect()
            graph_rect = QRect(margin, margin, rect.width() - 2*margin, rect.height() - 2*margin)

            x = max(graph_rect.left(), min(e.x(), graph_rect.right()))
            if len(self.measurements) == 1:
                local_idx = 0
            else:
                ratio = (x - graph_rect.left()) / max(1, graph_rect.width())
                local_idx = int(round(ratio * (len(self.measurements) - 1)))
            local_idx = max(0, min(local_idx, len(self.measurements) - 1))

            global_idx = self._view_start + local_idx
            m = self.measurements[local_idx]
            self.pointSelected.emit(global_idx, m)

        self._dragging = False

    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if dy:
            self.set_window_size(self._window_size + (-5 if dy > 0 else 5))

    # ---------- helpers ----------
    def _snap_to_tail(self):
        if self._history:
            self._view_start = max(0, len(self._history) - self._window_size)

    def _refresh_view_slice(self):
        start = self._view_start
        end = min(len(self._history), start + self._window_size)
        self.measurements = self._history[start:end]

    def _on_new_point(self):
        if self._follow_live:
            self._snap_to_tail()
        self._refresh_view_slice()
        self.update()

    def paintEvent(self, event):
        """Enhanced paintEvent with gray zones for no signal periods"""
        if not self.measurements:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        margin = 40
        graph_rect = QRect(margin, margin, 
                          rect.width() - 2*margin, 
                          rect.height() - 2*margin)
        
        # Get valid RSSI values for scaling
        valid_rssi_values = [m.rssi for m in self.measurements if m.rssi > -999]
        
        if not valid_rssi_values:
            # If no valid values, just show gray background
            painter.setPen(QColor("#bdc3c7"))
            painter.setBrush(QColor("#ecf0f1"))
            painter.drawRect(graph_rect)
            
            # Draw "No Signal" text
            painter.setPen(QColor("#7f8c8d"))
            font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(font)
            painter.drawText(graph_rect, Qt.AlignCenter, "No Signal Data")
            return
        
        # Calculate Y-axis range from valid values only
        min_rssi = min(valid_rssi_values)
        max_rssi = max(valid_rssi_values)
        
        if max_rssi == min_rssi:
            max_rssi = min_rssi + 10
        
        # Draw graph border
        painter.setPen(QColor("#dc3545"))
        painter.drawRect(graph_rect)
        
        # Draw Y-axis labels
        painter.setPen(QColor("#000000"))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        painter.drawText(5, margin, f"{max_rssi:.0f}")
        painter.drawText(5, margin + graph_rect.height()//2, f"{(max_rssi+min_rssi)/2:.0f}")
        painter.drawText(5, margin + graph_rect.height() - 5, f"{min_rssi:.0f}")
        
        # Calculate X positions and Y positions for all points
        points_data = []
        for i, measurement in enumerate(self.measurements):
            x = graph_rect.left() + (i * graph_rect.width() / max(1, len(self.measurements) - 1))
            
            if measurement.rssi > -999:
                # Valid signal - calculate Y position
                y = graph_rect.bottom() - ((measurement.rssi - min_rssi) * graph_rect.height() / (max_rssi - min_rssi))
                points_data.append({
                    'x': x, 'y': y, 'valid': True, 
                    'rssi': measurement.rssi, 'measurement': measurement
                })
            else:
                # No signal - use special marker
                points_data.append({
                    'x': x, 'y': None, 'valid': False, 
                    'rssi': measurement.rssi, 'measurement': measurement
                })
        
        # Draw gray zones for no-signal periods
        self._draw_no_signal_zones(painter, graph_rect, points_data)
        
        # Draw signal line segments (only for valid points)
        self._draw_signal_lines(painter, points_data)
        
        # Draw points
        self._draw_signal_points(painter, graph_rect, points_data)
    
    def _draw_no_signal_zones(self, painter, graph_rect, points_data):
        """Draw gray background zones for periods with no signal"""
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(200, 200, 200, 100))  # Light gray with transparency
        
        # Find consecutive no-signal periods
        no_signal_zones = []
        start_idx = None
        
        for i, point in enumerate(points_data):
            if not point['valid']:
                if start_idx is None:
                    start_idx = i
            else:
                if start_idx is not None:
                    # End of no-signal zone
                    no_signal_zones.append((start_idx, i - 1))
                    start_idx = None
        
        # Handle case where no-signal zone extends to the end
        if start_idx is not None:
            no_signal_zones.append((start_idx, len(points_data) - 1))
        
        # Draw gray rectangles for each no-signal zone
        for start_idx, end_idx in no_signal_zones:
            if start_idx < len(points_data) and end_idx < len(points_data):
                left_x = points_data[start_idx]['x']
                right_x = points_data[end_idx]['x']
                
                # Extend the zone slightly for better visual coverage
                zone_width = max(10, right_x - left_x)
                
                gray_rect = QRect(
                    int(left_x - 5), 
                    graph_rect.top(),
                    int(zone_width + 10),
                    graph_rect.height()
                )
                painter.drawRect(gray_rect)

    def _draw_signal_lines(self, painter, points_data):
        """Draw lines connecting valid signal points"""
        painter.setPen(QColor("#dc3545"))
        painter.setBrush(Qt.NoBrush)
        
        valid_points = [p for p in points_data if p['valid']]
        
        if len(valid_points) > 1:
            for i in range(1, len(valid_points)):
                prev_point = valid_points[i-1]
                curr_point = valid_points[i]
                
                painter.drawLine(
                    int(prev_point['x']), int(prev_point['y']),
                    int(curr_point['x']), int(curr_point['y'])
                )
    
    def _draw_signal_points(self, painter, graph_rect, points_data):
        """Draw points for signal measurements"""
        for point in points_data:
            if point['valid']:
                # Valid signal point - red circle
                painter.setPen(QColor("#dc3545"))
                painter.setBrush(QColor("#dc3545"))
                painter.drawEllipse(
                    int(point['x'] - 3), int(point['y'] - 3), 6, 6
                )
            else:
                # No signal point - gray X marker at bottom
                painter.setPen(QColor("#95a5a6"))
                painter.setBrush(Qt.NoBrush)
                
                x = int(point['x'])
                y = graph_rect.bottom() - 10
                
                # Draw X marker
                painter.drawLine(x - 4, y - 4, x + 4, y + 4)
                painter.drawLine(x - 4, y + 4, x + 4, y - 4)

# ==================== INTEGRATION FUNCTIONS ====================

def show_enhanced_sim_signal_quality_window(port: str = "", baudrate: int = 115200, parent=None, serial_thread=None):
    
    try:
        window = EnhancedSIMSignalQualityWindow(port, baudrate, parent, serial_thread)
        window.show()
        return window
    except Exception as e:
        if parent:
            QMessageBox.warning(parent, "Error", f"Cannot open Enhanced Signal Quality window: {e}")
        else:
            print(f"Error opening Enhanced Signal Quality window: {e}")
        return None


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = show_enhanced_sim_signal_quality_window("COM9", 115200)
    if window:
        sys.exit(app.exec_())