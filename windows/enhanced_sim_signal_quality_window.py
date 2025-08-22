# enhanced_sim_signal_quality_window.py


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
    QHeaderView, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QFont, QTextCursor, QPalette, QColor, QPixmap, QPainter

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
    
    def __init__(self, serial_thread, interval: int = 5, include_sim_info: bool = True):
        super().__init__()
        self.serial_thread = serial_thread
        self.interval = interval
        self.monitoring = False
        self.include_sim_info = include_sim_info
        self.sim_identity = None  # Cache SIM info
        
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
        
        if self.serial_thread:
            self.serial_thread.at_response_signal.connect(self.handle_at_response)
        
        self.pending_command = None
        self.command_responses = {}
        
    def start_monitoring(self):
        if not self.serial_thread or not self.serial_thread.isRunning():
            self.error_occurred.emit("No active serial connection available")
            return
            
        self.monitoring = True
        self.start()
        
    def stop_monitoring(self):
        self.monitoring = False
        self.quit()
        self.wait()
        
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
    
    def handle_at_response(self, response):
        if not self.pending_command:
            return
            
        if self.pending_command not in self.command_responses:
            self.command_responses[self.pending_command] = []
        
        self.command_responses[self.pending_command].append(response)
        
        if "OK" in response or "ERROR" in response:
            self.pending_command = None
    
    def _send_command_and_wait(self, command: str, timeout: float = 3.0) -> List[str]:
        if not self.serial_thread or not self.serial_thread.isRunning():
            return ["ERROR: No connection"]
        
        try:
            self.command_responses.clear()
            self.pending_command = command
            
            success = self.serial_thread.send_command(command)
            if not success:
                return ["ERROR: Failed to send command"]
            
            wait_time = 0
            while self.pending_command and wait_time < timeout:
                self.msleep(100)
                wait_time += 0.1
            
            responses = self.command_responses.get(command, [])
            return responses if responses else ["ERROR: No response"]
            
        except Exception as e:
            return [f"ERROR: {e}"]
    
    def _get_sim_identity(self) -> Optional[SIMIdentityInfo]:
        try:
            sim_info = SIMIdentityInfo()
            
            imsi_responses = self._send_command_and_wait("AT+CIMI")
            for response in imsi_responses:
                imsi_match = re.search(r'(\d{15})', response)
                if imsi_match:
                    sim_info.imsi = imsi_match.group(1)
                    self._parse_imsi(sim_info)
                    break
            
            iccid_responses = self._send_command_and_wait("AT+CCID")
            if "ERROR" in str(iccid_responses):
                iccid_responses = self._send_command_and_wait("AT+QCCID")
            
            for response in iccid_responses:
                iccid_match = re.search(r'(\d{18,22})', response)
                if iccid_match:
                    sim_info.iccid = iccid_match.group(1)
                    self._parse_iccid(sim_info)
                    break
            
            cnum_responses = self._send_command_and_wait("AT+CNUM")
            for response in cnum_responses:
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
        try:
            digits = [int(d) for d in number]
            checksum = 0
            
            # Process from right to left, doubling every second digit
            for i in range(len(digits) - 2, -1, -2):
                digits[i] *= 2
                if digits[i] > 9:
                    digits[i] -= 9
            
            checksum = sum(digits)
            return checksum % 10 == 0
            
        except:
            return False
    
    def _validate_sim_info(self, sim_info: SIMIdentityInfo):
        try:
            if not sim_info.imsi or len(sim_info.imsi) != 15:
                sim_info.sim_valid = False
                return
            
            if sim_info.mcc not in self.mcc_database:
                sim_info.sim_valid = False
            
            if sim_info.iccid and not sim_info.iccid_valid:
                pass
                
        except Exception as e:
            print(f"Error validating SIM: {e}")
    
    def _measure_signal(self) -> Optional[SignalMeasurement]:
        try:
            measurement = SignalMeasurement(
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
            
            csq_responses = self._send_command_and_wait("AT+CSQ")
            for response in csq_responses:
                match = re.search(r'\+CSQ:\s*(\d+),(\d+)', response)
                if match:
                    rssi_raw = int(match.group(1))
                    ber_raw = int(match.group(2))
                    
                    if rssi_raw == 0:
                        measurement.rssi = -113
                    elif rssi_raw == 31:
                        measurement.rssi = -51
                    elif 1 <= rssi_raw <= 30:
                        measurement.rssi = -113 + (rssi_raw * 2)
                    
                    if ber_raw != 99:
                        measurement.ber = ber_raw * 0.1
                    
                    measurement.signal_bars = self._calculate_bars(measurement.rssi)
                    measurement.quality_score = self._calculate_quality(measurement.rssi, measurement.ber)
                    break
            
            cesq_responses = self._send_command_and_wait("AT+CESQ")
            for response in cesq_responses:
                match = re.search(r'\+CESQ:\s*(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
                if match:
                    values = [int(x) for x in match.groups()]
                    rxlev, ber, rscp, ecn0, rsrq, rsrp = values
                    
                    if rsrq != 255:
                        measurement.rsrq = int(-19.5 + (rsrq * 0.5))
                    if rsrp != 255:
                        measurement.rsrp = -141 + rsrp
                    break
            
            if not measurement.carrier or measurement.carrier == "Unknown":
                cops_responses = self._send_command_and_wait("AT+COPS?")
                for response in cops_responses:
                    match = re.search(r'"([^"]*)"', response)
                    if match:
                        measurement.carrier = match.group(1)
                        break
            
            if self.sim_identity and self.sim_identity.carrier:
                measurement.carrier = self.sim_identity.carrier
            
            creg_responses = self._send_command_and_wait("AT+CREG?")
            for response in creg_responses:
                if "+CREG:" in response:
                    measurement.network_type = "4G/LTE"
                    break
            
            return measurement
            
        except Exception as e:
            print(f"Error measuring signal: {e}")
            return None
    
    def _calculate_bars(self, rssi: int) -> int:
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
        if rssi == -999:
            return 0.0
        
        rssi_score = max(0, min(100, (rssi + 113) * 100 / 62))
        
        ber_score = max(0, min(100, 100 - (ber * 10))) if ber < 99 else 50
        
        return (rssi_score * 0.7) + (ber_score * 0.3)


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
        
        self.setup_ui()
        self.apply_styles()
        
        if self.shared_serial_thread and self.shared_serial_thread.isRunning():
            self.connection_status.setText("🔗 Using shared connection")
            self.start_btn.setEnabled(True)
        else:
            self.connection_status.setText("🔴 No shared connection")
            self.start_btn.setEnabled(False)
            QMessageBox.warning(self, "Connection Required", 
                              "Please ensure the main window has an active serial connection before using Signal Quality Checker.")
    
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
        
        # Signal Graph
        graph_group = QGroupBox("📈 Real-time Signal Graph")
        graph_layout = QVBoxLayout()
        
        self.signal_graph = ScrollableSignalGraph() if ENABLE_GRAPH_SCROLLING else SignalVisualizationWidget()
        graph_layout.addWidget(self.signal_graph)

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
        
        # Signal Strength Indicator
        indicator_group = QGroupBox("📶 Signal Strength")
        indicator_layout = QVBoxLayout()
        
        self.signal_bars_label = QLabel("📶 ░░░░░ (0/5)")
        self.signal_bars_label.setFont(QFont("Courier New", 14, QFont.Bold))
        self.signal_bars_label.setAlignment(Qt.AlignCenter)
        indicator_layout.addWidget(self.signal_bars_label)
        
        self.signal_slider = QSlider(Qt.Horizontal)
        self.signal_slider.setRange(0, 100)
        self.signal_slider.setEnabled(False)
        indicator_layout.addWidget(self.signal_slider)
        
        self.quality_label = QLabel("Quality: 0%")
        self.quality_label.setAlignment(Qt.AlignCenter)
        indicator_layout.addWidget(self.quality_label)
        
        indicator_group.setLayout(indicator_layout)
        layout.addWidget(indicator_group)
        
        panel.setLayout(layout)
        return panel
    
    def create_analysis_panel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Tabs for different views
        tab_widget = QTabWidget()
        
        sim_tab = self.create_sim_info_tab()
        tab_widget.addTab(sim_tab, "📱 SIM Info")
        
        # Tab 2: Measurements Table
        measurements_tab = self.create_measurements_tab()
        tab_widget.addTab(measurements_tab, "📋 Measurements")
        
        # Tab 3: Statistics
        stats_tab = self.create_statistics_tab()
        tab_widget.addTab(stats_tab, "📊 Statistics")
        
        # Tab 4: Recommendations
        rec_tab = self.create_recommendations_tab()
        tab_widget.addTab(rec_tab, "💡 Recommendations")
        
        layout.addWidget(tab_widget)
        panel.setLayout(layout)
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
        
        # MCC/MNC Database Info
        # database_group = QGroupBox("📚 MCC/MNC Database")
        # database_layout = QVBoxLayout()
        
        self.database_text = QTextEdit()
        self.database_text.setReadOnly(True)
        self.database_text.setMaximumHeight(150)
        self.database_text.setFont(QFont("Courier New", 10))
        # self.database_text.setText("MCC/MNC database information will be displayed here when SIM is detected...")
        # database_layout.addWidget(self.database_text)
        
        # database_group.setLayout(database_layout)
        # layout.addWidget(database_group)
        
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
        dist_layout = QVBoxLayout()
        
        self.distribution_text = QTextEdit()
        self.distribution_text.setMaximumHeight(200)
        self.distribution_text.setReadOnly(True)
        self.distribution_text.setFont(QFont("Courier New", 10))
        dist_layout.addWidget(self.distribution_text)
        
        dist_group.setLayout(dist_layout)
        layout.addWidget(dist_group)
        
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
            
            self.monitoring_thread.start_monitoring()
            
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
    
    def stop_monitoring(self):
        try:
            if self.monitoring_thread:
                self.monitoring_thread.stop_monitoring()
                self.monitoring_thread = None
            
            if hasattr(self, 'timer'):
                self.timer.stop()
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.interval_spin.setEnabled(True)
            self.include_sim_check.setEnabled(True)
            
            if self.shared_serial_thread and self.shared_serial_thread.isRunning():
                self.connection_status.setText("🔗 Using shared connection")
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
            
            # MCC/MNC Database Info
            self.update_mcc_mnc_database_info(sim_info)
            
        except Exception as e:
            print(f"Error updating SIM info display: {e}")
    
#     def update_mcc_mnc_database_info(self, sim_info: SIMIdentityInfo):
#         try:
#             if not sim_info.mcc:
#                 return
                
#             database_text = f"""
# 📚 MCC/MNC DATABASE INFORMATION
# {'='*50}

# 🌍 Mobile Country Code (MCC): {sim_info.mcc}
#    • Country: {sim_info.country or 'Unknown'}
#    • ISO Code: {self.get_iso_code(sim_info.mcc)}

# 📡 Mobile Network Code (MNC): {sim_info.mnc}
#    • Carrier: {sim_info.carrier or 'Unknown'}
#    • Network Type: {self.get_network_type(sim_info.mcc, sim_info.mnc)}

# 🏔️ Complete IMSI Breakdown:
#    • Full IMSI: {sim_info.imsi}
#    • MCC: {sim_info.mcc} (Country: {sim_info.country})
#    • MNC: {sim_info.mnc} (Network: {sim_info.carrier})
#    • MSIN: {sim_info.msin} (Subscriber ID)

# 💳 ICCID Analysis:
#    • Full ICCID: {sim_info.iccid}
#    • IIN: {sim_info.iin} (Issuer Identification)
#    • Account ID: {sim_info.account_id}
#    • Check Digit: {sim_info.check_digit}
#    • Luhn Validation: {'✅ Passed' if sim_info.iccid_valid else '❌ Failed'}

# 🔍 Network Analysis:
#    • Home Network: {'Yes' if sim_info.home_network else 'No'}
#    • Roaming: {'Active' if sim_info.roaming else 'Inactive'}
#    • SIM Status: {'Valid' if sim_info.sim_valid else 'Invalid'}
# """
            
#             self.database_text.setText(database_text)
            
#         except Exception as e:
#             print(f"Error updating database info: {e}")
    
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
            self.signal_bars_label.setText(bars_visual)
            
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
                
                quality_assessment = self.get_signal_grade(measurement.rssi)
                self.sim_labels['signal_assessment'].setText(quality_assessment)
            
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
    
    def create_quality_distribution(self):
        try:
            if not self.measurements_history:
                return
            
            ranges = [
                (90, 100, "Excellent", "🟢"),   # Office building = Excellent
                (75, 89, "Good", "✅"),         # Satellite antenna = Good
                (50, 74, "Fair", "📶"),         # Antenna bars = Fair
                (25, 49, "Poor", "🟠"),         # Red circle = Poor
                (0, 24, "Very Poor", "🔴")      # Warning sign = Very Poor
            ]

            distribution_text = "📊 QUALITY DISTRIBUTION\n"
            distribution_text += "=" * 40 + "\n\n"

            
            total = len(self.measurements_history)
            
            for min_q, max_q, label, icon in ranges:
                count = sum(1 for m in self.measurements_history 
                          if min_q <= m.quality_score <= max_q)
                percentage = (count / total * 100) if total > 0 else 0
                
                bar_length = int(percentage / 5)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                
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
            
            # ✅ แก้ไข: ใช้ f-string หรือ .format() ให้ถูกต้อง
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
            # ✅ ลบบรรทัดที่ไม่ได้ใช้งาน (recommendations_text.format(...))
            
            if latest_measurement.sim_info:
                sim_info = latest_measurement.sim_info
                # ✅ แก้ไข: เปลี่ยนอิโมจิจาก 🏔️ เป็น 📱
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
                # ✅ แก้ไข: เพิ่ม emoji ที่เหมาะสมและแก้ไขรูปแบบ
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
            
            # ✅ แก้ไข: ปรับปรุงส่วน Connection Info
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

    ℹ️  Note: This Signal Quality Checker uses the same serial connection as the main window.
    If you see connection issues, please check the main window's serial connection.
    """
            
            # ✅ แก้ไข: เพิ่มการตั้งค่าข้อความและเลื่อนตำแหน่ง
            self.recommendations_text.setText(recommendations_text)
            
            # เลื่อนไปด้านบนเสมอ
            cursor = self.recommendations_text.textCursor()
            cursor.movePosition(cursor.Start)
            self.recommendations_text.setTextCursor(cursor)
            
        except Exception as e:
            error_msg = f"Error updating recommendations: {e}"
            print(error_msg)
            
            # ✅ แสดงข้อความ error ใน recommendations tab
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
            
            self.signal_bars_label.setText("📶 ░░░░░ (0/5)")
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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Enhanced_Signal_Quality_Data_{timestamp}.csv"
            
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

    def create_measurements_tab_old_version(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.measurements_table = QTableWidget(0, 9) 
        self.measurements_table.setHorizontalHeaderLabels([
            "#",           
            "Time", 
            "RSSI (dBm)", 
            "Quality (%)", 
            "Bars", 
            "RSRP (dBm)", 
            "RSRQ (dB)", 
            "BER (%)", 
            "Carrier"
        ])
        
        header = self.measurements_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        self.measurements_table.verticalHeader().setDefaultSectionSize(25)
        self.measurements_table.verticalHeader().setVisible(False)
        
        table_font = QFont("Arial", 10)
        self.measurements_table.setFont(table_font)
        
        self.measurements_table.setColumnWidth(0, 40)   # Row Number
        self.measurements_table.setColumnWidth(1, 70)   # Time
        self.measurements_table.setColumnWidth(2, 85)   # RSSI
        self.measurements_table.setColumnWidth(3, 80)   # Quality
        self.measurements_table.setColumnWidth(4, 50)   # Bars
        self.measurements_table.setColumnWidth(5, 85)   # RSRP
        self.measurements_table.setColumnWidth(6, 80)   # RSRQ
        self.measurements_table.setColumnWidth(7, 70)   # BER
        self.measurements_table.setColumnWidth(8, 120)  # Carrier
        
        layout.addWidget(self.measurements_table)
        
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
        if rssi >= -70:
            return "A+ (Excellent)"
        elif rssi >= -80:
            return "B+ (Very Good)"
        elif rssi >= -90:
            return "B (Good)"
        elif rssi >= -100:
            return "C (Fair)"
        elif rssi >= -110:
            return "D (Poor)"
        else:
            return "F (Very Poor)"
    
    def create_signal_bars_visual(self, bars: int) -> str:
        filled = "█" * bars
        empty = "░" * (5 - bars)
        return f"📶 {filled}{empty} ({bars}/5)"
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #fdf2f2;
                border: 2px solid #dc3545;
                border-radius: 10px;
            }
            
            QGroupBox {
                font-size: 13px;
                font-weight: 600;
                color: #721c24;
                border: 2px solid #dc3545;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                background-color: #fff5f5;
            }
            
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #a91e2c;
                font-weight: bold;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
                border: 1px solid #a71e2a;
            }
            
            QPushButton:pressed {
                background: #dc3545;
            }
            
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
            
            QTabWidget::pane {
                border: 2px solid #dc3545;
                border-radius: 8px;
                background-color: #fff5f5;
            }
            
            QTabBar::tab {
                background-color: #f8d7da;
                color: #721c24;
                padding: 6px 12px;
                margin-right: 2px;
                border: 1px solid #f5c6cb;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #f1b0b7;
            }
            
            QTableWidget {
                border: 1px solid #dc3545;
                border-radius: 4px;
                background-color: white;
                gridline-color: #f5c6cb;
                font-size: 10px;
                selection-background-color: #f8d7da;
            }
            
            QTableWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid #f5c6cb;
                min-height: 20px;
            }
            
            QTableWidget::item:selected {
                background-color: #f8d7da;
                color: #721c24;
            }
            
            QHeaderView::section {
                background-color: #dc3545;
                color: white;
                padding: 6px 8px;
                border: 1px solid #c82333;
                font-size: 10px;
                font-weight: bold;
                min-height: 25px;
            }
            
            QTextEdit {
                border: 1px solid #dc3545;
                border-radius: 4px;
                background-color: white;
                color: #212529;
                padding: 5px;
            }
            
            QComboBox, QSpinBox {
                border: 1px solid #dc3545;
                border-radius: 4px;
                padding: 2px 5px;
                background-color: white;
                min-width: 80px;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #dc3545;
                height: 6px;
                background: #f8d7da;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background: #dc3545;
                border: 1px solid #c82333;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
            
            QSlider::sub-page:horizontal {
                background: #dc3545;
                border-radius: 3px;
            }
            
            QCheckBox {
                color: #721c24;
                font-weight: 500;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #dc3545;
                border-radius: 2px;
                background-color: white;
            }
            
            QCheckBox::indicator:checked {
                background-color: #dc3545;
                image: none;
            }
            
            QSplitter::handle {
                background-color: #dc3545;
                width: 3px;
                height: 3px;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
    
    def closeEvent(self, event):
        try:
            self.stop_monitoring()
        except:
            pass
        event.accept()


# SignalVisualizationWidget class (same as before)
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
        if not self.measurements:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        margin = 40
        graph_rect = QRect(margin, margin, 
                          rect.width() - 2*margin, 
                          rect.height() - 2*margin)
        
        rssi_values = [m.rssi for m in self.measurements if m.rssi > -999]
        if not rssi_values:
            return
        
        min_rssi = min(rssi_values)
        max_rssi = max(rssi_values)
        
        if max_rssi == min_rssi:
            max_rssi = min_rssi + 10
        
        painter.setPen(QColor("#dc3545"))
        painter.drawRect(graph_rect)
        
        painter.setPen(QColor("#000000"))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        painter.drawText(5, margin, f"{max_rssi:.0f}")
        painter.drawText(5, margin + graph_rect.height()//2, f"{(max_rssi+min_rssi)/2:.0f}")
        painter.drawText(5, margin + graph_rect.height() - 5, f"{min_rssi:.0f}")
        
        if len(rssi_values) > 1:
            painter.setPen(QColor("#dc3545"))
            painter.setBrush(QColor("#dc3545"))
            
            points = []
            for i, measurement in enumerate(self.measurements):
                if measurement.rssi > -999:
                    x = graph_rect.left() + (i * graph_rect.width() / max(1, len(self.measurements) - 1))
                    y = graph_rect.bottom() - ((measurement.rssi - min_rssi) * graph_rect.height() / (max_rssi - min_rssi))
                    points.append((int(x), int(y)))
            
            for i in range(1, len(points)):
                painter.drawLine(points[i-1][0], points[i-1][1], points[i][0], points[i][1])
            
            for point in points:
                painter.drawEllipse(point[0]-2, point[1]-2, 4, 4)


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

class ScrollableSignalGraph(SignalVisualizationWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []          
        self._view_start = 0        
        self._window_size = 50      
        self._follow_live = True    
        self._dragging = False
        self._last_x = 0

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
            self.set_follow_live(False)

    def mouseMoveEvent(self, e):
        if self._dragging and self._history:
            dx = e.x() - self._last_x
            self._last_x = e.x()
            step = int(dx / 8)   
            if step:
                self.set_view_start(self._view_start - step)

    def mouseReleaseEvent(self, e):
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


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = show_enhanced_sim_signal_quality_window("COM9", 115200)
    if window:
        sys.exit(app.exec_())