# at_command_helper.py
"""
AT Command Helper สำหรับการตรวจสอบคุณภาพสัญญาณและข้อมูล SIM
รวมการวิเคราะห์ IMSI และ ICCID เพื่อการตรวจสอบแบบละเอียด
"""

import serial
import time
import re
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class SignalData:
    """โครงสร้างข้อมูลสัญญาณ"""
    rssi: int = -999  # Received Signal Strength Indicator
    rsrp: int = -999  # Reference Signal Received Power (4G)
    rsrq: int = -999  # Reference Signal Received Quality (4G)
    sinr: int = -999  # Signal to Interference plus Noise Ratio
    ber: float = 99.0  # Bit Error Rate
    rscp: int = -999  # Received Signal Code Power (3G)
    ecio: int = -999  # Ec/Io (3G)
    cell_id: str = ""
    lac: str = ""  # Location Area Code
    network_type: str = "Unknown"  # 2G/3G/4G/5G
    frequency_band: str = ""
    signal_bars: int = 0  # 0-5 bars
    quality_score: float = 0.0  # 0-100%


@dataclass
class SIMIdentity:
    """โครงสร้างข้อมูล SIM Identity"""
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
    fraud_risk: str = "LOW"  # LOW/MEDIUM/HIGH


class ATCommandHelper:
    """Helper สำหรับจัดการคำสั่ง AT แบบละเอียด"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self.is_connected = False
        
        # Network databases
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
        
        # Thailand MNC database (MCC=520)
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
        
        # ICCID IIN database
        self.iin_database = {
            "8966": {"country": "Thailand", "issuer": "AIS", "type": "Standard"},
            "89660": {"country": "Thailand", "issuer": "AIS", "type": "Prepaid"},
            "89665": {"country": "Thailand", "issuer": "dtac", "type": "Standard"},
            "896605": {"country": "Thailand", "issuer": "dtac", "type": "Prepaid"},
            "89661": {"country": "Thailand", "issuer": "TrueMove H", "type": "Standard"},
            "896601": {"country": "Thailand", "issuer": "TrueMove", "type": "Legacy"},
            "89660020": {"country": "Thailand", "issuer": "TOT", "type": "Enterprise"},
            "8965": {"country": "Singapore", "issuer": "SingTel", "type": "Standard"}
        }
        
    def connect(self) -> bool:
        """เชื่อมต่อกับโมเด็ม"""
        try:
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # ทดสอบการเชื่อมต่อ
            response = self.send_command("AT")
            if "OK" in response:
                self.is_connected = True
                return True
            
            return False
            
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """ตัดการเชื่อมต่อ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
        self.is_connected = False
    
    def send_command(self, command: str, wait_time: float = 1.0) -> str:
        """ส่งคำสั่ง AT และรับผลลัพธ์"""
        if not self.is_connected:
            return "ERROR: Not connected"
        
        try:
            # ล้าง buffer
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()
            
            # ส่งคำสั่ง
            self.connection.write(f"{command}\r\n".encode())
            time.sleep(wait_time)
            
            # อ่านผลลัพธ์
            response = ""
            while self.connection.in_waiting:
                chunk = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                time.sleep(0.1)
            
            return response.strip()
            
        except Exception as e:
            return f"ERROR: {e}"
    
    def send_command_with_retry(self, command: str, max_retries: int = 3) -> str:
        """ส่งคำสั่ง AT พร้อมการลองใหม่"""
        for attempt in range(max_retries):
            response = self.send_command(command)
            if "ERROR" not in response or "OK" in response:
                return response
            time.sleep(0.5)  # รอก่อนลองใหม่
        
        return response


class SignalQualityAnalyzer:
    """วิเคราะห์คุณภาพสัญญาณแบบครอบคลุม"""
    
    def __init__(self, at_helper: ATCommandHelper):
        self.at_helper = at_helper
        
        # Signal quality thresholds
        self.rssi_thresholds = {
            'excellent': (-50, -70),
            'good': (-70, -85),
            'fair': (-85, -100),
            'poor': (-100, -113)
        }
        
        self.rsrp_thresholds = {  # for 4G
            'excellent': (-44, -80),
            'good': (-80, -90),
            'fair': (-90, -100),
            'poor': (-100, -140)
        }
    
    def get_basic_signal_info(self) -> SignalData:
        """ดึงข้อมูลสัญญาณพื้นฐาน (AT+CSQ)"""
        signal_data = SignalData()
        
        try:
            response = self.at_helper.send_command("AT+CSQ")
            match = re.search(r'\+CSQ:\s*(\d+),(\d+)', response)
            
            if match:
                rssi_raw = int(match.group(1))
                ber_raw = int(match.group(2))
                
                # แปลง RSSI (0-31) เป็น dBm
                if rssi_raw == 0:
                    signal_data.rssi = -113
                elif rssi_raw == 31:
                    signal_data.rssi = -51
                elif 1 <= rssi_raw <= 30:
                    signal_data.rssi = -113 + (rssi_raw * 2)
                
                # แปลง BER
                if ber_raw != 99:
                    signal_data.ber = ber_raw * 0.1
                
                # คำนวณ signal bars (0-5)
                signal_data.signal_bars = self._calculate_signal_bars(signal_data.rssi)
                
        except Exception as e:
            print(f"Error getting basic signal: {e}")
        
        return signal_data
    
    def get_extended_signal_info(self) -> SignalData:
        """ดึงข้อมูลสัญญาณขยาย (AT+CESQ)"""
        signal_data = self.get_basic_signal_info()
        
        try:
            response = self.at_helper.send_command("AT+CESQ")
            # +CESQ: rxlev,ber,rscp,ecn0,rsrq,rsrp
            match = re.search(r'\+CESQ:\s*(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
            
            if match:
                values = [int(x) for x in match.groups()]
                rxlev, ber, rscp, ecn0, rsrq, rsrp = values
                
                # 3G parameters
                if rscp != 255:  # Valid RSCP
                    signal_data.rscp = -121 + rscp
                if ecn0 != 255:  # Valid Ec/Io
                    signal_data.ecio = -24 + (ecn0 * 0.5)
                
                # 4G parameters
                if rsrq != 255:  # Valid RSRQ
                    signal_data.rsrq = -19.5 + (rsrq * 0.5)
                if rsrp != 255:  # Valid RSRP
                    signal_data.rsrp = -141 + rsrp
                
        except Exception as e:
            print(f"Error getting extended signal: {e}")
        
        return signal_data
    
    def get_network_info(self) -> Dict[str, Any]:
        """ดึงข้อมูลเครือข่าย"""
        network_info = {
            'operator': 'Unknown',
            'network_type': 'Unknown',
            'cell_id': '',
            'lac': '',
            'registered': False,
            'roaming': False
        }
        
        try:
            # ดึงข้อมูลผู้ให้บริการ
            response = self.at_helper.send_command("AT+COPS?")
            match = re.search(r'\+COPS:\s*\d+,\d+,"([^"]*)"', response)
            if match:
                network_info['operator'] = match.group(1)
            
            # ดึงข้อมูลการลงทะเบียนเครือข่าย
            response = self.at_helper.send_command("AT+CREG?")
            match = re.search(r'\+CREG:\s*\d+,(\d+)(?:,"([^"]*)",?"([^"]*)")?', response)
            if match:
                reg_status = int(match.group(1))
                network_info['registered'] = reg_status in [1, 5]  # Home or Roaming
                network_info['roaming'] = reg_status == 5
                
                if match.group(2) and match.group(3):
                    network_info['lac'] = match.group(2)
                    network_info['cell_id'] = match.group(3)
            
            # ตรวจสอบประเภทเครือข่าย
            response = self.at_helper.send_command("AT+COPS=3,2;+COPS?")
            if "52001" in response or "52003" in response or "52023" in response:
                network_info['network_type'] = "4G/5G"
            elif "52005" in response or "52018" in response:
                network_info['network_type'] = "4G/5G"  
            elif "52015" in response or "52025" in response:
                network_info['network_type'] = "4G/5G"
            else:
                network_info['network_type'] = "3G/4G"
                
        except Exception as e:
            print(f"Error getting network info: {e}")
        
        return network_info
    
    def get_comprehensive_signal_info(self) -> Dict[str, Any]:
        """ดึงข้อมูลสัญญาณแบบครบถ้วน"""
        signal_data = self.get_extended_signal_info()
        network_info = self.get_network_info()
        
        # คำนวณคะแนนคุณภาพรวม
        quality_score = self._calculate_quality_score(signal_data)
        signal_grade = self._get_signal_grade(signal_data.rssi)
        
        # สร้าง Unicode signal bars
        signal_bars_visual = self._create_signal_bars(signal_data.signal_bars)
        
        # คำแนะนำ
        recommendations = self._generate_recommendations(signal_data, network_info)
        
        return {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'signal_data': signal_data,
            'network_info': network_info,
            'quality_score': quality_score,
            'signal_grade': signal_grade,
            'signal_bars_visual': signal_bars_visual,
            'recommendations': recommendations,
            'raw_measurements': {
                'rssi_dbm': signal_data.rssi,
                'rsrp_dbm': signal_data.rsrp,
                'rsrq_db': signal_data.rsrq,
                'sinr_db': signal_data.sinr,
                'ber_percent': signal_data.ber
            }
        }
    
    def _calculate_signal_bars(self, rssi: int) -> int:
        """คำนวณจำนวน signal bars (0-5)"""
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
    
    def _calculate_quality_score(self, signal_data: SignalData) -> float:
        """คำนวณคะแนนคุณภาพรวม (0-100)"""
        scores = []
        
        # RSSI score
        if signal_data.rssi > -999:
            rssi_score = max(0, min(100, (signal_data.rssi + 113) * 100 / 62))
            scores.append(rssi_score)
        
        # RSRP score (for 4G)
        if signal_data.rsrp > -999:
            rsrp_score = max(0, min(100, (signal_data.rsrp + 140) * 100 / 96))
            scores.append(rsrp_score)
        
        # BER score (lower is better)
        if signal_data.ber < 99:
            ber_score = max(0, min(100, 100 - (signal_data.ber * 10)))
            scores.append(ber_score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _get_signal_grade(self, rssi: int) -> Tuple[str, str]:
        """ประเมินเกรดสัญญาณ"""
        if rssi >= -70:
            return "A+ (ممتاز)", "#2ecc71"  # Excellent - Green
        elif rssi >= -80:
            return "B+ (جيد جداً)", "#27ae60"  # Very Good - Dark Green
        elif rssi >= -90:
            return "B (جيد)", "#f39c12"     # Good - Orange
        elif rssi >= -100:
            return "C (متوسط)", "#e67e22"   # Fair - Dark Orange
        elif rssi >= -110:
            return "D (ضعيف)", "#e74c3c"    # Poor - Red
        else:
            return "F (ضعيف جداً)", "#95a5a6" # Very Poor - Gray
    
    def _create_signal_bars(self, bars: int) -> str:
        """สร้าง Unicode signal bars"""
        filled = "█" * bars
        empty = "░" * (5 - bars)
        return f"📶 {filled}{empty} ({bars}/5)"
    
    def _generate_recommendations(self, signal_data: SignalData, network_info: Dict) -> List[str]:
        """สร้างคำแนะนำ"""
        recommendations = []
        
        if signal_data.rssi < -100:
            recommendations.extend([
                "📍 Move to a location with better signal coverage",
                "🔧 Check antenna connection and positioning",
                "📡 Consider using signal booster or repeater"
            ])
        
        if signal_data.ber > 5.0:
            recommendations.extend([
                "⚠️ High bit error rate detected",
                "🔄 Try reconnecting to network",
                "📞 Contact service provider if issue persists"
            ])
        
        if not network_info.get('registered', False):
            recommendations.extend([
                "❌ Not registered to network",
                "🔄 Try manual network selection",
                "📱 Restart modem or check SIM card"
            ])
        
        if network_info.get('roaming', False):
            recommendations.append("📍 Currently roaming - data charges may apply")
        
        if not recommendations:
            recommendations.append("✅ Signal quality is good - no issues detected")
        
        return recommendations


class SIMCardValidator:
    """วิเคราะห์ IMSI และ ICCID แบบละเอียด"""
    
    def __init__(self, at_helper: ATCommandHelper):
        self.at_helper = at_helper
        
    def get_sim_identity(self) -> SIMIdentity:
        """ดึงข้อมูล SIM Identity"""
        sim_identity = SIMIdentity()
        
        try:
            # ดึง IMSI
            response = self.at_helper.send_command("AT+CIMI")
            imsi_match = re.search(r'(\d{15})', response)
            if imsi_match:
                sim_identity.imsi = imsi_match.group(1)
                self._parse_imsi(sim_identity)
            
            # ดึง ICCID
            response = self.at_helper.send_command("AT+CCID")
            iccid_match = re.search(r'(\d{18,22})', response)
            if iccid_match:
                sim_identity.iccid = iccid_match.group(1)
                self._parse_iccid(sim_identity)
            
            # ดึงเบอร์โทร
            response = self.at_helper.send_command("AT+CNUM")
            phone_match = re.search(r'"([+\d]+)"', response)
            if phone_match:
                sim_identity.phone_number = phone_match.group(1)
            
            # ตรวจสอบความถูกต้องโดยรวม
            self._validate_sim_card(sim_identity)
            
        except Exception as e:
            print(f"Error getting SIM identity: {e}")
        
        return sim_identity
    
    def _parse_imsi(self, sim_identity: SIMIdentity):
        """แยกวิเคราะห์ IMSI"""
        if not sim_identity.imsi or len(sim_identity.imsi) < 15:
            return
        
        try:
            # แยก MCC, MNC, MSIN
            sim_identity.mcc = sim_identity.imsi[:3]
            
            # MNC อาจเป็น 2 หรือ 3 หลัก
            if sim_identity.mcc == "520":  # Thailand
                sim_identity.mnc = sim_identity.imsi[3:5]
                sim_identity.msin = sim_identity.imsi[5:]
            else:
                # ลองทั้ง 2 และ 3 หลัก
                sim_identity.mnc = sim_identity.imsi[3:6]
                sim_identity.msin = sim_identity.imsi[6:]
            
            # ค้นหาข้อมูลประเทศ
            if sim_identity.mcc in self.at_helper.mcc_database:
                country_info = self.at_helper.mcc_database[sim_identity.mcc]
                sim_identity.country = country_info['country']
            
            # ค้นหาข้อมูล Carrier (สำหรับไทย)
            if sim_identity.mcc == "520":
                if sim_identity.mnc in self.at_helper.thailand_mnc:
                    carrier_info = self.at_helper.thailand_mnc[sim_identity.mnc]
                    sim_identity.carrier = carrier_info['carrier']
                    sim_identity.home_network = True
                    sim_identity.roaming = False
            else:
                sim_identity.home_network = False
                sim_identity.roaming = True
                sim_identity.carrier = "Foreign Network"
                
        except Exception as e:
            print(f"Error parsing IMSI: {e}")
    
    def _parse_iccid(self, sim_identity: SIMIdentity):
        """แยกวิเคราะห์ ICCID"""
        if not sim_identity.iccid:
            return
        
        try:
            # แยกส่วนต่างๆ
            if len(sim_identity.iccid) >= 19:
                # Standard format: IIN (7) + Account (11) + Check (1)
                sim_identity.iin = sim_identity.iccid[:7]
                sim_identity.account_id = sim_identity.iccid[7:-1]
                sim_identity.check_digit = sim_identity.iccid[-1]
                
                # ตรวจสอบ Check Digit ด้วย Luhn Algorithm
                sim_identity.iccid_valid = self._luhn_check(sim_identity.iccid)
                
                # ค้นหาข้อมูล Issuer
                for iin_prefix in sorted(self.at_helper.iin_database.keys(), key=len, reverse=True):
                    if sim_identity.iccid.startswith(iin_prefix):
                        issuer_info = self.at_helper.iin_database[iin_prefix]
                        if not sim_identity.carrier:  # ถ้ายังไม่มีจาก IMSI
                            sim_identity.carrier = issuer_info['issuer']
                        break
                        
        except Exception as e:
            print(f"Error parsing ICCID: {e}")
    
    def _luhn_check(self, number: str) -> bool:
        """ตรวจสอบ Check Digit ด้วย Luhn Algorithm"""
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
    
    def _validate_sim_card(self, sim_identity: SIMIdentity):
        """ตรวจสอบความถูกต้องโดยรวม"""
        try:
            # ตรวจสอบ IMSI
            if not sim_identity.imsi or len(sim_identity.imsi) != 15:
                sim_identity.sim_valid = False
                sim_identity.fraud_risk = "HIGH"
                return
            
            # ตรวจสอบ MCC ที่รู้จัก
            if sim_identity.mcc not in self.at_helper.mcc_database:
                sim_identity.fraud_risk = "MEDIUM"
            
            # ตรวจสอบความสอดคล้องระหว่าง IMSI และ ICCID
            if sim_identity.iccid and len(sim_identity.iccid) >= 7:
                # Thailand SIMs should start with 8966
                if sim_identity.mcc == "520" and not sim_identity.iccid.startswith("8966"):
                    sim_identity.fraud_risk = "MEDIUM"
                elif sim_identity.mcc != "520" and sim_identity.iccid.startswith("8966"):
                    sim_identity.fraud_risk = "MEDIUM"
            
            # ตรวจสอบ ICCID Check Digit
            if not sim_identity.iccid_valid:
                sim_identity.fraud_risk = "HIGH"
            
            # ตรวจสอบรูปแบบเบอร์โทร
            if sim_identity.phone_number:
                if sim_identity.mcc == "520":  # Thailand
                    if not (sim_identity.phone_number.startswith("66") or 
                           sim_identity.phone_number.startswith("0")):
                        sim_identity.fraud_risk = "MEDIUM"
                        
        except Exception as e:
            print(f"Error validating SIM: {e}")


class NetworkPerformanceTester:
    """ทดสอบประสิทธิภาพเครือข่าย"""
    
    def __init__(self, at_helper: ATCommandHelper):
        self.at_helper = at_helper
        
    def test_signal_stability(self, duration_seconds: int = 30) -> Dict[str, Any]:
        """ทดสอบเสถียรภาพสัญญาณ"""
        measurements = []
        start_time = time.time()
        
        try:
            analyzer = SignalQualityAnalyzer(self.at_helper)
            
            while time.time() - start_time < duration_seconds:
                signal_data = analyzer.get_basic_signal_info()
                measurements.append({
                    'timestamp': time.time(),
                    'rssi': signal_data.rssi,
                    'ber': signal_data.ber
                })
                time.sleep(2)  # วัดทุก 2 วินาที
            
            # คำนวณสถิติ
            rssi_values = [m['rssi'] for m in measurements if m['rssi'] > -999]
            
            if rssi_values:
                stability_result = {
                    'total_measurements': len(measurements),
                    'valid_measurements': len(rssi_values),
                    'avg_rssi': sum(rssi_values) / len(rssi_values),
                    'min_rssi': min(rssi_values),
                    'max_rssi': max(rssi_values),
                    'rssi_variance': self._calculate_variance(rssi_values),
                    'stability_score': self._calculate_stability_score(rssi_values),
                    'measurements': measurements
                }
                
                return stability_result
                
        except Exception as e:
            print(f"Error in stability test: {e}")
        
        return {'error': 'Failed to complete stability test'}
    
    def test_data_connectivity(self) -> Dict[str, Any]:
        """ทดสอบการเชื่อมต่อข้อมูล"""
        try:
            results = {
                'pdp_context_active': False,
                'ip_address': '',
                'dns_resolution': False,
                'connectivity_score': 0
            }
            
            # ตรวจสอบ PDP Context
            response = self.at_helper.send_command("AT+CGACT?")
            if "+CGACT: 1,1" in response:
                results['pdp_context_active'] = True
                results['connectivity_score'] += 30
            
            # ตรวจสอบ IP Address
            response = self.at_helper.send_command("AT+CGPADDR=1")
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', response)
            if ip_match:
                results['ip_address'] = ip_match.group(1)
                results['connectivity_score'] += 40
            
            # ทดสอบ DNS (ping Google DNS)
            response = self.at_helper.send_command("AT+CPING=\"8.8.8.8\",1,32,1000")
            if "OK" in response and "ERROR" not in response:
                results['dns_resolution'] = True
                results['connectivity_score'] += 30
            
            return results
            
        except Exception as e:
            return {'error': f'Data connectivity test failed: {e}'}
    
    def test_handover_capability(self) -> Dict[str, Any]:
        """ทดสอบความสามารถ Handover ระหว่าง Cell"""
        try:
            results = {
                'neighbor_cells': [],
                'handover_capable': False,
                'serving_cell': {},
                'handover_score': 0
            }
            
            # ดึงข้อมูล Serving Cell
            response = self.at_helper.send_command("AT+CENG?")
            if "+CENG:" in response:
                # Parse serving cell info
                lines = response.split('\n')
                for line in lines:
                    if "+CENG:" in line:
                        cell_info = self._parse_cell_info(line)
                        if cell_info.get('serving', False):
                            results['serving_cell'] = cell_info
                        else:
                            results['neighbor_cells'].append(cell_info)
            
            # ประเมินความสามารถ Handover
            if len(results['neighbor_cells']) > 0:
                results['handover_capable'] = True
                results['handover_score'] = min(100, len(results['neighbor_cells']) * 20)
            
            return results
            
        except Exception as e:
            return {'error': f'Handover test failed: {e}'}
    
    def _calculate_variance(self, values: List[float]) -> float:
        """คำนวณ variance"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance
    
    def _calculate_stability_score(self, rssi_values: List[float]) -> float:
        """คำนวณคะแนนเสถียรภาพ (0-100)"""
        if not rssi_values:
            return 0.0
        
        variance = self._calculate_variance(rssi_values)
        
        # คะแนนเสถียรภาพ: variance ต่ำ = คะแนนสูง
        if variance <= 1.0:
            return 100.0
        elif variance <= 4.0:
            return 80.0
        elif variance <= 9.0:
            return 60.0
        elif variance <= 16.0:
            return 40.0
        else:
            return 20.0
    
    def _parse_cell_info(self, cell_line: str) -> Dict[str, Any]:
        """แยกวิเคราะห์ข้อมูล Cell"""
        cell_info = {
            'cell_id': '',
            'lac': '',
            'rssi': -999,
            'serving': False
        }
        
        try:
            # Parse different cell info formats
            if "CENG:" in cell_line:
                parts = cell_line.split(',')
                if len(parts) >= 4:
                    cell_info['serving'] = parts[0].strip().endswith('0')
                    cell_info['rssi'] = int(parts[1].strip()) if parts[1].strip().isdigit() else -999
                    cell_info['cell_id'] = parts[2].strip().replace('"', '')
                    cell_info['lac'] = parts[3].strip().replace('"', '')
                    
        except Exception:
            pass
        
        return cell_info


# ==================== SIM INFO WINDOW ====================

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QTabWidget, QWidget, QProgressBar, QGroupBox, QGridLayout,
    QScrollArea, QFrame, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor


class SIMAnalysisThread(QThread):
    """Thread สำหรับการวิเคราะห์ SIM แบบ Background"""
    
    progress_updated = pyqtSignal(int, str)
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, port: str, baudrate: int = 115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.should_stop = False
        self.analysis_options = {
            'analyze_signal': True,
            'analyze_sim': True,
            'test_performance': True,
            'detailed_scan': True
        }
    
    def run(self):
        """การทำงานหลักของ Thread"""
        try:
            self.progress_updated.emit(0, "🔌 Connecting to modem...")
            
            # สร้างการเชื่อมต่อ
            at_helper = ATCommandHelper(self.port, self.baudrate)
            if not at_helper.connect():
                self.error_occurred.emit("❌ Failed to connect to modem")
                return
            
            analysis_results = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'connection_info': {
                    'port': self.port,
                    'baudrate': self.baudrate,
                    'connected': True
                }
            }
            
            try:
                # วิเคราะห์ SIM Identity
                if self.analysis_options.get('analyze_sim', True) and not self.should_stop:
                    self.progress_updated.emit(10, "🆔 Analyzing SIM identity...")
                    sim_validator = SIMCardValidator(at_helper)
                    sim_identity = sim_validator.get_sim_identity()
                    analysis_results['sim_identity'] = sim_identity
                    
                # วิเคราะห์สัญญาณ
                if self.analysis_options.get('analyze_signal', True) and not self.should_stop:
                    self.progress_updated.emit(25, "📶 Analyzing signal quality...")
                    signal_analyzer = SignalQualityAnalyzer(at_helper)
                    signal_info = signal_analyzer.get_comprehensive_signal_info()
                    analysis_results['signal_analysis'] = signal_info
                    
                # ทดสอบประสิทธิภาพ
                if self.analysis_options.get('test_performance', True) and not self.should_stop:
                    self.progress_updated.emit(50, "🚀 Testing network performance...")
                    performance_tester = NetworkPerformanceTester(at_helper)
                    
                    # ทดสอบเสถียرภาพสัญญาณ (15 วินาที)
                    self.progress_updated.emit(55, "📊 Testing signal stability...")
                    stability_result = performance_tester.test_signal_stability(15)
                    analysis_results['stability_test'] = stability_result
                    
                    # ทดสอบการเชื่อมต่อข้อมูล
                    if not self.should_stop:
                        self.progress_updated.emit(70, "🌐 Testing data connectivity...")
                        connectivity_result = performance_tester.test_data_connectivity()
                        analysis_results['connectivity_test'] = connectivity_result
                    
                    # ทดสอบ Handover
                    if not self.should_stop:
                        self.progress_updated.emit(85, "📡 Testing handover capability...")
                        handover_result = performance_tester.test_handover_capability()
                        analysis_results['handover_test'] = handover_result
                
                # สแกนข้อมูลเพิ่มเติม
                if self.analysis_options.get('detailed_scan', True) and not self.should_stop:
                    self.progress_updated.emit(90, "🔍 Performing detailed scan...")
                    additional_info = self._get_additional_info(at_helper)
                    analysis_results['additional_info'] = additional_info
                
                self.progress_updated.emit(100, "✅ Analysis completed successfully!")
                self.analysis_completed.emit(analysis_results)
                
            finally:
                at_helper.disconnect()
                
        except Exception as e:
            self.error_occurred.emit(f"Analysis failed: {e}")
    
    def stop_analysis(self):
        """หยุดการวิเคราะห์"""
        self.should_stop = True
        
    def _get_additional_info(self, at_helper: ATCommandHelper) -> Dict[str, Any]:
        """ดึงข้อมูลเพิ่มเติม"""
        additional_info = {}
        
        try:
            # ข้อมูลโมเด็ม
            manufacturer = at_helper.send_command("AT+CGMI").replace("OK", "").strip()
            model = at_helper.send_command("AT+CGMM").replace("OK", "").strip()
            firmware = at_helper.send_command("AT+CGMR").replace("OK", "").strip()
            imei = at_helper.send_command("AT+CGSN").replace("OK", "").strip()
            
            additional_info['modem'] = {
                'manufacturer': manufacturer,
                'model': model,
                'firmware': firmware,
                'imei': imei
            }
            
            # ข้อมูลการสนับสนุนเครือข่าย
            bands_response = at_helper.send_command("AT+QNWINFO")
            additional_info['network_support'] = {
                'current_bands': bands_response,
                'supports_lte': "LTE" in bands_response.upper(),
                'supports_5g': "5G" in bands_response.upper() or "NR" in bands_response.upper()
            }
            
        except Exception as e:
            additional_info['error'] = f"Failed to get additional info: {e}"
        
        return additional_info


class SIMInfoWindow(QDialog):
    """หน้าต่างแสดงข้อมูล SIM แบบละเอียด"""
    
    def __init__(self, port: str, baudrate: int = 115200, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.analysis_thread = None
        self.analysis_results = {}
        
        self.setup_ui()
        self.apply_styles()
        
        # เริ่มการวิเคราะห์อัตโนมัติ
        QTimer.singleShot(500, self.start_analysis)
    
    def setup_ui(self):
        """สร้าง UI"""
        self.setWindowTitle(f"📱 SIM Information Analysis - {self.port}")
        self.setMinimumSize(1000, 800)
        self.setModal(False)
        
        layout = QVBoxLayout(self)
        
        # Header
        self.create_header(layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(True)
        self.progress_label = QLabel("🚀 Preparing analysis...")
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        # Tabs
        self.create_tabs(layout)
        
        # Footer
        self.create_footer(layout)
    
    def create_header(self, layout):
        """สร้างส่วนหัว"""
        header_frame = QFrame()
        header_layout = QHBoxLayout()
        
        # Icon & Title
        icon_label = QLabel("📱")
        icon_label.setFont(QFont("Arial", 28))
        header_layout.addWidget(icon_label)
        
        title_layout = QVBoxLayout()
        self.title_label = QLabel("SIM Information Analysis")
        self.title_label.setFont(QFont("Arial", 20, QFont.Bold))
        
        self.subtitle_label = QLabel(f"Port: {self.port} | Baudrate: {self.baudrate}")
        self.subtitle_label.setFont(QFont("Arial", 12))
        
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Status
        self.status_label = QLabel("🔄 Analyzing...")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(self.status_label)
        
        header_frame.setLayout(header_layout)
        layout.addWidget(header_frame)
        
        self.header_frame = header_frame
    
    def create_tabs(self, layout):
        """สร้าง tabs"""
        self.tab_widget = QTabWidget()
        
        # Tab 1: Signal Analysis
        self.create_signal_tab()
        
        # Tab 2: SIM Information
        self.create_sim_tab()
        
        # Tab 3: Performance Tests
        self.create_performance_tab()
        
        # Tab 4: Raw Data
        self.create_raw_data_tab()
        
        layout.addWidget(self.tab_widget)
    
    def create_signal_tab(self):
        """Tab วิเคราะห์สัญญาณ"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        # Current Signal Status
        signal_group = QGroupBox("📶 Signal Quality Analysis")
        signal_layout = QGridLayout()
        
        # สร้าง labels สำหรับแสดงผล
        labels = [
            ("RSSI (dBm):", "rssi_value"),
            ("Signal Grade:", "signal_grade"),
            ("Signal Bars:", "signal_bars"),
            ("Quality Score:", "quality_score"),
            ("Network Type:", "network_type"),
            ("Carrier:", "carrier"),
            ("Cell ID:", "cell_id"),
            ("Registration:", "registration")
        ]
        
        self.signal_labels = {}
        for i, (label_text, key) in enumerate(labels):
            label = QLabel(label_text)
            value = QLabel("--")
            value.setFont(QFont("Courier New", 11))
            
            signal_layout.addWidget(label, i, 0)
            signal_layout.addWidget(value, i, 1)
            self.signal_labels[key] = value
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group)
        
        # Signal Recommendations
        rec_group = QGroupBox("💡 Recommendations")
        rec_layout = QVBoxLayout()
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setMaximumHeight(150)
        self.recommendations_text.setReadOnly(True)
        rec_layout.addWidget(self.recommendations_text)
        
        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        self.tab_widget.addTab(tab, "📶 Signal Analysis")
    
    def create_sim_tab(self):
        """Tab ข้อมูล SIM"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        # SIM Identity
        identity_group = QGroupBox("🆔 SIM Identity")
        identity_layout = QGridLayout()
        
        # IMSI Analysis
        imsi_labels = [
            ("Full IMSI:", "imsi_full"),
            ("MCC (Country):", "imsi_mcc"),
            ("MNC (Network):", "imsi_mnc"),
            ("MSIN (Subscriber):", "imsi_msin"),
            ("Country:", "sim_country"),
            ("Carrier:", "sim_carrier"),
            ("Phone Number:", "phone_number")
        ]
        
        self.imsi_labels = {}
        for i, (label_text, key) in enumerate(imsi_labels):
            label = QLabel(label_text)
            value = QLabel("--")
            value.setFont(QFont("Courier New", 11))
            
            identity_layout.addWidget(label, i, 0)
            identity_layout.addWidget(value, i, 1)
            self.imsi_labels[key] = value
        
        identity_group.setLayout(identity_layout)
        layout.addWidget(identity_group)
        
        # ICCID Analysis
        iccid_group = QGroupBox("💳 ICCID Analysis")
        iccid_layout = QGridLayout()
        
        iccid_labels = [
            ("Full ICCID:", "iccid_full"),
            ("IIN (Issuer):", "iccid_iin"),
            ("Account ID:", "iccid_account"),
            ("Check Digit:", "iccid_check"),
            ("Validation:", "iccid_valid"),
            ("Card Issuer:", "card_issuer"),
            ("Fraud Risk:", "fraud_risk")
        ]
        
        self.iccid_labels = {}
        for i, (label_text, key) in enumerate(iccid_labels):
            label = QLabel(label_text)
            value = QLabel("--")
            value.setFont(QFont("Courier New", 11))
            
            iccid_layout.addWidget(label, i, 0)
            iccid_layout.addWidget(value, i, 1)
            self.iccid_labels[key] = value
        
        iccid_group.setLayout(iccid_layout)
        layout.addWidget(iccid_group)
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        self.tab_widget.addTab(tab, "🆔 SIM Information")
    
    def create_performance_tab(self):
        """Tab ทดสอบประสิทธิภาพ"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        # Signal Stability
        stability_group = QGroupBox("📊 Signal Stability Test")
        stability_layout = QVBoxLayout()
        
        self.stability_text = QTextEdit()
        self.stability_text.setMaximumHeight(200)
        self.stability_text.setReadOnly(True)
        self.stability_text.setFont(QFont("Courier New", 10))
        stability_layout.addWidget(self.stability_text)
        
        stability_group.setLayout(stability_layout)
        layout.addWidget(stability_group)
        
        # Network Performance
        perf_group = QGroupBox("🚀 Network Performance")
        perf_layout = QVBoxLayout()
        
        self.performance_text = QTextEdit()
        self.performance_text.setMaximumHeight(200)
        self.performance_text.setReadOnly(True)
        self.performance_text.setFont(QFont("Courier New", 10))
        perf_layout.addWidget(self.performance_text)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        self.tab_widget.addTab(tab, "🚀 Performance")
    
    def create_raw_data_tab(self):
        """Tab ข้อมูลดิบ"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        raw_group = QGroupBox("🔍 Raw Analysis Data")
        raw_layout = QVBoxLayout()
        
        self.raw_data_text = QTextEdit()
        self.raw_data_text.setReadOnly(True)
        self.raw_data_text.setFont(QFont("Courier New", 10))
        raw_layout.addWidget(self.raw_data_text)
        
        raw_group.setLayout(raw_layout)
        layout.addWidget(raw_group)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🔍 Raw Data")
    
    def create_footer(self, layout):
        """สร้างส่วนท้าย"""
        footer_layout = QHBoxLayout()
        
        # Export buttons
        self.export_text_btn = QPushButton("📄 Export Text Report")
        self.export_json_btn = QPushButton("📊 Export JSON Data")
        self.refresh_btn = QPushButton("🔄 Refresh Analysis")
        
        self.export_text_btn.setFixedWidth(150)
        self.export_json_btn.setFixedWidth(150)
        self.refresh_btn.setFixedWidth(130)
        
        # Initially disabled until analysis completes
        self.export_text_btn.setEnabled(False)
        self.export_json_btn.setEnabled(False)
        
        footer_layout.addWidget(self.export_text_btn)
        footer_layout.addWidget(self.export_json_btn)
        footer_layout.addWidget(self.refresh_btn)
        footer_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("❌ Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addLayout(footer_layout)
        
        # Connect signals
        self.export_text_btn.clicked.connect(self.export_text_report)
        self.export_json_btn.clicked.connect(self.export_json_data)
        self.refresh_btn.clicked.connect(self.start_analysis)
    
    def start_analysis(self):
        """เริ่มการวิเคราะห์"""
        try:
            if self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.stop_analysis()
                self.analysis_thread.wait(3000)  # รอ 3 วินาที
            
            self.status_label.setText("🔄 Analyzing...")
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_bar.setValue(0)
            
            self.analysis_thread = SIMAnalysisThread(self.port, self.baudrate)
            self.analysis_thread.progress_updated.connect(self.update_progress)
            self.analysis_thread.analysis_completed.connect(self.analysis_finished)
            self.analysis_thread.error_occurred.connect(self.analysis_error)
            
            self.analysis_thread.start()
            
        except Exception as e:
            self.analysis_error(f"Failed to start analysis: {e}")
    
    def update_progress(self, value: int, message: str):
        """อัพเดทความคืบหน้า"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def analysis_finished(self, results: Dict[str, Any]):
        """เมื่อการวิเคราะห์เสร็จสิ้น"""
        try:
            self.analysis_results = results
            
            # ซ่อน progress bar
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.status_label.setText("✅ Analysis Complete")
            
            # อัพเดทข้อมูลใน UI
            self.update_signal_display_enhanced(results)
            self.update_sim_display(results)
            self.update_performance_display(results)
            self.update_raw_data_display(results)
            
            # เปิดใช้งาน export buttons
            self.export_text_btn.setEnabled(True)
            self.export_json_btn.setEnabled(True)
            
        except Exception as e:
            self.analysis_error(f"Error displaying results: {e}")
    
    def analysis_error(self, error_message: str):
        """จัดการข้อผิดพลาด"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.status_label.setText("❌ Analysis Failed")
        
        QMessageBox.warning(self, "Analysis Error", error_message)
    
    def update_signal_display(self, results: Dict[str, Any]):
        """อัพเดทการแสดงผลสัญญาณ"""
        try:
            signal_analysis = results.get('signal_analysis', {})
            signal_data = signal_analysis.get('signal_data')
            network_info = signal_analysis.get('network_info', {})
            
            if signal_data:
                # อัพเดท signal labels
                self.signal_labels['rssi_value'].setText(f"{signal_data.rssi} dBm")
                self.signal_labels['quality_score'].setText(f"{signal_analysis.get('quality_score', 0):.1f}%")
                
                signal_grade = signal_analysis.get('signal_grade', ('Unknown', '#000000'))
                grade_text, color = signal_grade if isinstance(signal_grade, tuple) else (signal_grade, '#000000')
                self.signal_labels['signal_grade'].setText(grade_text)
                self.signal_labels['signal_grade'].setStyleSheet(f"color: {color}; font-weight: bold;")
                
                self.signal_labels['signal_bars'].setText(signal_analysis.get('signal_bars_visual', '--'))
                self.signal_labels['network_type'].setText(network_info.get('network_type', 'Unknown'))
                self.signal_labels['carrier'].setText(network_info.get('operator', 'Unknown'))
                self.signal_labels['cell_id'].setText(network_info.get('cell_id', '--'))
                
                reg_status = "✅ Registered" if network_info.get('registered') else "❌ Not Registered"
                if network_info.get('roaming'):
                    reg_status += " (Roaming)"
                self.signal_labels['registration'].setText(reg_status)
            
            # อัพเดทคำแนะนำ
            recommendations = signal_analysis.get('recommendations', [])
            if recommendations:
                rec_text = "\n".join([f"• {rec}" for rec in recommendations])
                self.recommendations_text.setText(rec_text)
            
        except Exception as e:
            print(f"Error updating signal display: {e}")
    
    def update_sim_display(self, results: Dict[str, Any]):
        """อัพเดทการแสดงข้อมูล SIM"""
        try:
            sim_identity = results.get('sim_identity')
            
            if sim_identity:
                # IMSI information
                self.imsi_labels['imsi_full'].setText(sim_identity.imsi or '--')
                self.imsi_labels['imsi_mcc'].setText(f"{sim_identity.mcc} ({sim_identity.country})" if sim_identity.mcc else '--')
                self.imsi_labels['imsi_mnc'].setText(sim_identity.mnc or '--')
                self.imsi_labels['imsi_msin'].setText(sim_identity.msin or '--')
                self.imsi_labels['sim_country'].setText(sim_identity.country or 'Unknown')
                self.imsi_labels['sim_carrier'].setText(sim_identity.carrier or 'Unknown')
                self.imsi_labels['phone_number'].setText(sim_identity.phone_number or '--')
                
                # ICCID information
                self.iccid_labels['iccid_full'].setText(sim_identity.iccid or '--')
                self.iccid_labels['iccid_iin'].setText(sim_identity.iin or '--')
                self.iccid_labels['iccid_account'].setText(sim_identity.account_id or '--')
                self.iccid_labels['iccid_check'].setText(sim_identity.check_digit or '--')
                
                # Validation status
                valid_text = "✅ Valid" if sim_identity.iccid_valid else "❌ Invalid"
                valid_color = "#2ecc71" if sim_identity.iccid_valid else "#e74c3c"
                self.iccid_labels['iccid_valid'].setText(valid_text)
                self.iccid_labels['iccid_valid'].setStyleSheet(f"color: {valid_color}; font-weight: bold;")
                
                # Fraud risk
                risk_colors = {'LOW': '#2ecc71', 'MEDIUM': '#f39c12', 'HIGH': '#e74c3c'}
                risk_color = risk_colors.get(sim_identity.fraud_risk, '#95a5a6')
                self.iccid_labels['fraud_risk'].setText(sim_identity.fraud_risk)
                self.iccid_labels['fraud_risk'].setStyleSheet(f"color: {risk_color}; font-weight: bold;")
                
                # เดา card issuer จาก carrier
                card_issuer = sim_identity.carrier if sim_identity.carrier != 'Unknown' else '--'
                self.iccid_labels['card_issuer'].setText(card_issuer)
            
        except Exception as e:
            print(f"Error updating SIM display: {e}")
    
    # def update_performance_display(self, results: Dict[str, Any]):
    #     """อัพเดทการแสดงประสิทธิภาพ"""
    #     try:
            # Signal Stability
    def update_performance_display(self, results: Dict[str, Any]):
        """อัพเดทการแสดงประสิทธิภาพ"""
        try:
            # Signal Stability Test
            stability_test = results.get('stability_test', {})
            if stability_test and 'error' not in stability_test:
                stability_text = f"""
📊 SIGNAL STABILITY TEST RESULTS
{'='*50}

📈 Measurement Summary:
   • Total Measurements: {stability_test.get('total_measurements', 0)}
   • Valid Readings: {stability_test.get('valid_measurements', 0)}
   • Test Duration: ~{stability_test.get('total_measurements', 0) * 2} seconds

📶 RSSI Analysis:
   • Average RSSI: {stability_test.get('avg_rssi', 0):.1f} dBm
   • Minimum RSSI: {stability_test.get('min_rssi', 0):.1f} dBm  
   • Maximum RSSI: {stability_test.get('max_rssi', 0):.1f} dBm
   • Signal Range: {stability_test.get('max_rssi', 0) - stability_test.get('min_rssi', 0):.1f} dB

📊 Stability Metrics:
   • Variance: {stability_test.get('rssi_variance', 0):.2f}
   • Stability Score: {stability_test.get('stability_score', 0):.1f}/100
   • Signal Quality: {"🟢 Stable" if stability_test.get('stability_score', 0) > 80 else "🟡 Moderate" if stability_test.get('stability_score', 0) > 60 else "🔴 Unstable"}

🎯 ASCII Signal Graph:
"""
                
                # สร้าง ASCII graph
                measurements = stability_test.get('measurements', [])
                if measurements:
                    rssi_values = [m['rssi'] for m in measurements if m['rssi'] > -999]
                    if rssi_values:
                        graph = self._create_ascii_graph(rssi_values)
                        stability_text += graph
                
                self.stability_text.setText(stability_text)
            else:
                self.stability_text.setText("❌ Signal stability test failed or not available")
            
            # Network Performance
            connectivity_test = results.get('connectivity_test', {})
            handover_test = results.get('handover_test', {})
            
            perf_text = f"""
🚀 NETWORK PERFORMANCE TESTS
{'='*50}

🌐 Data Connectivity Test:
   • PDP Context: {"✅ Active" if connectivity_test.get('pdp_context_active') else "❌ Inactive"}
   • IP Address: {connectivity_test.get('ip_address', 'Not assigned')}
   • DNS Resolution: {"✅ Working" if connectivity_test.get('dns_resolution') else "❌ Failed"}
   • Connectivity Score: {connectivity_test.get('connectivity_score', 0)}/100

📡 Handover Capability:
   • Handover Support: {"✅ Available" if handover_test.get('handover_capable') else "❌ Not Available"}
   • Neighbor Cells: {len(handover_test.get('neighbor_cells', []))} detected
   • Handover Score: {handover_test.get('handover_score', 0)}/100

🏗️ Serving Cell Info:
"""
            
            serving_cell = handover_test.get('serving_cell', {})
            if serving_cell:
                perf_text += f"   • Cell ID: {serving_cell.get('cell_id', 'Unknown')}\n"
                perf_text += f"   • LAC: {serving_cell.get('lac', 'Unknown')}\n"
                perf_text += f"   • RSSI: {serving_cell.get('rssi', 'Unknown')} dBm\n"
            else:
                perf_text += "   • No serving cell information available\n"
            
            # Neighbor cells
            neighbor_cells = handover_test.get('neighbor_cells', [])
            if neighbor_cells:
                perf_text += f"\n📱 Neighbor Cells ({len(neighbor_cells)}):\n"
                for i, cell in enumerate(neighbor_cells[:5]):  # Show max 5
                    perf_text += f"   {i+1}. Cell ID: {cell.get('cell_id', 'Unknown')} | RSSI: {cell.get('rssi', 'Unknown')} dBm\n"
                if len(neighbor_cells) > 5:
                    perf_text += f"   ... and {len(neighbor_cells) - 5} more cells\n"
            
            self.performance_text.setText(perf_text)
            
        except Exception as e:
            print(f"Error updating performance display: {e}")
    
    def update_raw_data_display(self, results: Dict[str, Any]):
        """อัพเดทการแสดงข้อมูลดิบ"""
        try:
            # Format results as JSON with proper indentation
            formatted_json = json.dumps(results, indent=2, default=str, ensure_ascii=False)
            self.raw_data_text.setText(formatted_json)
        except Exception as e:
            self.raw_data_text.setText(f"Error formatting raw data: {e}")
    
    def _create_ascii_graph(self, values: List[float]) -> str:
        """สร้างกราฟ ASCII สำหรับค่า RSSI"""
        try:
            if not values or len(values) < 2:
                return "   📊 Insufficient data for graph\n"
            
            # Normalize values for display (0-20 range)
            min_val = min(values)
            max_val = max(values)
            
            if max_val == min_val:
                return "   📊 Signal remained constant\n"
            
            normalized = []
            for val in values:
                norm = int(((val - min_val) / (max_val - min_val)) * 15) + 1
                normalized.append(max(1, min(15, norm)))
            
            # Create ASCII graph
            graph_lines = []
            
            # Top border
            graph_lines.append("   ┌" + "─" * min(len(normalized), 50) + "┐")
            
            # Graph data (from top to bottom)
            for level in range(15, 0, -1):
                line = "   │"
                for i, val in enumerate(normalized[:50]):  # Limit width
                    if val >= level:
                        line += "█"
                    elif val >= level - 0.5:
                        line += "▄"
                    else:
                        line += " "
                line += "│"
                
                # Add scale on the right
                if level == 15:
                    line += f"  {max_val:.1f} dBm (Max)"
                elif level == 8:
                    line += f"  {(max_val + min_val)/2:.1f} dBm (Avg)"
                elif level == 1:
                    line += f"  {min_val:.1f} dBm (Min)"
                
                graph_lines.append(line)
            
            # Bottom border
            graph_lines.append("   └" + "─" * min(len(normalized), 50) + "┘")
            
            # Time axis
            time_line = "   "
            for i in range(0, min(len(normalized), 50), 10):
                time_line += f"{i*2:>10}s"
            graph_lines.append(time_line)
            
            return "\n".join(graph_lines) + "\n\n"
            
        except Exception as e:
            return f"   📊 Graph generation error: {e}\n"
    
    def export_text_report(self):
        """ส่งออกรายงานเป็น Text"""
        try:
            if not self.analysis_results:
                QMessageBox.warning(self, "No Data", "No analysis results to export")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SIM_Analysis_Report_{timestamp}.txt"
            
            # สร้างรายงาน
            report = self._generate_text_report(self.analysis_results)
            
            # บันทึกไฟล์
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                QMessageBox.information(self, "Export Successful", 
                                      f"Report exported successfully!\nFile: {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Failed to save report: {e}")
                
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to generate report: {e}")
    
    def export_json_data(self):
        """ส่งออกข้อมูลเป็น JSON"""
        try:
            if not self.analysis_results:
                QMessageBox.warning(self, "No Data", "No analysis results to export")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SIM_Analysis_Data_{timestamp}.json"
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.analysis_results, f, indent=2, default=str, ensure_ascii=False)
                
                QMessageBox.information(self, "Export Successful", 
                                      f"Data exported successfully!\nFile: {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Failed to save data: {e}")
                
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export data: {e}")
    
    def _generate_text_report(self, results: Dict[str, Any]) -> str:
        """สร้างรายงาน Text แบบละเอียด"""
        report = f"""
{'='*80}
                    SIM INFORMATION ANALYSIS REPORT
{'='*80}

🕒 Analysis Time: {results.get('timestamp', 'Unknown')}
🔌 Connection: {results.get('connection_info', {}).get('port', 'Unknown')} @ {results.get('connection_info', {}).get('baudrate', 'Unknown')} baud

{'='*80}
                           🆔 SIM IDENTITY ANALYSIS
{'='*80}
"""
        
        sim_identity = results.get('sim_identity')
        if sim_identity:
            report += f"""
📱 SIM Card Information:
   • Phone Number: {sim_identity.phone_number or 'Not available'}
   • Country: {sim_identity.country or 'Unknown'}
   • Carrier: {sim_identity.carrier or 'Unknown'}
   • Home Network: {'Yes' if sim_identity.home_network else 'No (Roaming)'}
   • Fraud Risk Level: {sim_identity.fraud_risk}

🔢 IMSI Analysis:
   • Full IMSI: {sim_identity.imsi or 'Not available'}
   • MCC (Mobile Country Code): {sim_identity.mcc or 'N/A'}
   • MNC (Mobile Network Code): {sim_identity.mnc or 'N/A'}
   • MSIN (Mobile Subscriber ID): {sim_identity.msin or 'N/A'}

💳 ICCID Analysis:
   • Full ICCID: {sim_identity.iccid or 'Not available'}
   • IIN (Issuer Identification): {sim_identity.iin or 'N/A'}
   • Account Identifier: {sim_identity.account_id or 'N/A'}
   • Check Digit: {sim_identity.check_digit or 'N/A'}
   • Validation Status: {'✅ Valid' if sim_identity.iccid_valid else '❌ Invalid'}

"""
        
        report += f"""
{'='*80}
                         📶 SIGNAL QUALITY ANALYSIS  
{'='*80}
"""
        
        signal_analysis = results.get('signal_analysis', {})
        if signal_analysis:
            signal_data = signal_analysis.get('signal_data')
            network_info = signal_analysis.get('network_info', {})
            
            if signal_data:
                grade_text = signal_analysis.get('signal_grade', 'Unknown')
                if isinstance(grade_text, tuple):
                    grade_text = grade_text[0]
                
                report += f"""
📡 Signal Measurements:
   • RSSI (Signal Strength): {signal_data.rssi} dBm
   • Signal Quality Grade: {grade_text}
   • Signal Bars: {signal_data.signal_bars}/5
   • Quality Score: {signal_analysis.get('quality_score', 0):.1f}%
   • Bit Error Rate: {signal_data.ber}%

🌐 Network Information:
   • Operator: {network_info.get('operator', 'Unknown')}
   • Network Type: {network_info.get('network_type', 'Unknown')}
   • Registration Status: {'Registered' if network_info.get('registered') else 'Not Registered'}
   • Roaming Status: {'Active' if network_info.get('roaming') else 'Home Network'}
   • Cell ID: {network_info.get('cell_id', 'Unknown')}
   • Location Area Code: {network_info.get('lac', 'Unknown')}

💡 Recommendations:
"""
                recommendations = signal_analysis.get('recommendations', [])
                for rec in recommendations:
                    report += f"   • {rec}\n"
        
        # Performance Tests
        report += f"""

{'='*80}
                        🚀 NETWORK PERFORMANCE TESTS
{'='*80}
"""
        
        stability_test = results.get('stability_test', {})
        if stability_test and 'error' not in stability_test:
            report += f"""
📊 Signal Stability Test:
   • Total Measurements: {stability_test.get('total_measurements', 0)}
   • Average RSSI: {stability_test.get('avg_rssi', 0):.1f} dBm
   • Signal Range: {stability_test.get('max_rssi', 0) - stability_test.get('min_rssi', 0):.1f} dB
   • Stability Score: {stability_test.get('stability_score', 0):.1f}/100
   • Assessment: {"Excellent" if stability_test.get('stability_score', 0) > 90 else "Good" if stability_test.get('stability_score', 0) > 70 else "Fair" if stability_test.get('stability_score', 0) > 50 else "Poor"}

"""
        
        connectivity_test = results.get('connectivity_test', {})
        if connectivity_test:
            report += f"""
🌐 Data Connectivity Test:
   • PDP Context: {"Active" if connectivity_test.get('pdp_context_active') else "Inactive"}
   • IP Address: {connectivity_test.get('ip_address', 'Not assigned')}
   • DNS Resolution: {"Working" if connectivity_test.get('dns_resolution') else "Failed"}
   • Overall Score: {connectivity_test.get('connectivity_score', 0)}/100

"""
        
        handover_test = results.get('handover_test', {})
        if handover_test:
            report += f"""
📡 Handover Capability Test:
   • Handover Support: {"Available" if handover_test.get('handover_capable') else "Not Available"}
   • Neighbor Cells Detected: {len(handover_test.get('neighbor_cells', []))}
   • Handover Score: {handover_test.get('handover_score', 0)}/100

"""
        
        # Additional Information
        additional_info = results.get('additional_info', {})
        if additional_info and 'error' not in additional_info:
            modem_info = additional_info.get('modem', {})
            if modem_info:
                report += f"""
{'='*80}
                           📱 MODEM INFORMATION
{'='*80}

🔧 Hardware Details:
   • Manufacturer: {modem_info.get('manufacturer', 'Unknown')}
   • Model: {modem_info.get('model', 'Unknown')}
   • Firmware Version: {modem_info.get('firmware', 'Unknown')}
   • IMEI: {modem_info.get('imei', 'Unknown')}

"""
            
            network_support = additional_info.get('network_support', {})
            if network_support:
                report += f"""
🌐 Network Capabilities:
   • LTE Support: {'Yes' if network_support.get('supports_lte') else 'No'}
   • 5G Support: {'Yes' if network_support.get('supports_5g') else 'No'}
   • Current Bands: {network_support.get('current_bands', 'Unknown')}

"""
        
        report += f"""
{'='*80}
                              📋 SUMMARY
{'='*80}

This comprehensive analysis provides detailed insights into your SIM card
and network connection quality. Use this information to:

• Optimize signal reception and network performance
• Verify SIM card authenticity and detect potential fraud
• Troubleshoot connectivity issues
• Monitor network stability over time

For technical support or questions about this report, please contact
your network service provider or system administrator.

Report generated by SIM Information Analysis System
{'='*80}
"""
        
        return report
    
    def apply_styles(self):
        """ใช้สไตล์โทนสีแดงทางการ"""
        self.setStyleSheet("""
            QDialog {
                background-color: #fdf2f2;
                border: 2px solid #dc3545;
                border-radius: 10px;
            }
            
            QGroupBox {
                font-size: 14px;
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
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
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
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #f5c6cb;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            
            QTabBar::tab:selected {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #f1b0b7;
            }
            
            QProgressBar {
                border: 2px solid #dc3545;
                border-radius: 8px;
                background-color: #f8d7da;
                text-align: center;
                font-weight: bold;
                color: #721c24;
                height: 25px;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                border-radius: 6px;
                margin: 1px;
            }
            
            QTextEdit {
                border: 1px solid #dc3545;
                border-radius: 4px;
                background-color: white;
                color: #212529;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 5px;
            }
            
            QLabel {
                color: #212529;
                font-size: 12px;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Header specific styles
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #fff5f5;
                border: 2px solid #f5c6cb;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)
        
        self.title_label.setStyleSheet("""
            QLabel {
                color: #721c24;
                font-weight: bold;
            }
        """)
        
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-style: italic;
            }
        """)
    
    def closeEvent(self, event):
        """จัดการเมื่อปิดหน้าต่าง"""
        try:
            if self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.stop_analysis()
                self.analysis_thread.wait(3000)  # รอ 3 วินาที
        except:
            pass
        event.accept()


# ==================== INTEGRATION FUNCTIONS ====================

def show_sim_analysis_window(port: str, baudrate: int = 115200, parent=None):
    """แสดงหน้าต่าง SIM Analysis"""
    try:
        window = SIMInfoWindow(port, baudrate, parent)
        window.setModal(False)
        window.show()
        return window
    except Exception as e:
        if parent:
            QMessageBox.warning(parent, "Error", f"Cannot open SIM Analysis window: {e}")
        else:
            print(f"Error opening SIM Analysis window: {e}")
        return None


def create_at_command_helper(port: str, baudrate: int = 115200) -> ATCommandHelper:
    """สร้าง AT Command Helper"""
    return ATCommandHelper(port, baudrate)


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    import sys
    
    # Test AT Command Helper
    print("=== AT Command Helper Test ===")
    at_helper = ATCommandHelper("COM9")  # เปลี่ยนเป็นพอร์ตที่ถูกต้อง
    
    if at_helper.connect():
        print("✅ Connected to modem")
        
        # Test Signal Analysis
        signal_analyzer = SignalQualityAnalyzer(at_helper)
        signal_info = signal_analyzer.get_comprehensive_signal_info()
        print(f"📶 Signal Quality: {signal_info['quality_score']:.1f}%")
        print(f"📱 Signal Grade: {signal_info['signal_grade']}")
        
        # Test SIM Validation
        sim_validator = SIMCardValidator(at_helper)
        sim_identity = sim_validator.get_sim_identity()
        print(f"🆔 IMSI: {sim_identity.imsi}")
        print(f"💳 ICCID: {sim_identity.iccid}")
        print(f"🏠 Carrier: {sim_identity.carrier}")
        print(f"⚠️ Fraud Risk: {sim_identity.fraud_risk}")
        
        at_helper.disconnect()
    else:
        print("❌ Failed to connect to modem")
    
    # Launch GUI
    print("\n=== Launching SIM Analysis Window ===")
    app = QApplication(sys.argv)
    
    window = show_sim_analysis_window("COM9", 115200)  # เปลี่ยนเป็นพอร์ตที่ถูกต้อง
    
    if window:
        sys.exit(app.exec_())