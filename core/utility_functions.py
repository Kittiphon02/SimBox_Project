# core/utility_functions.py
"""
ฟังก์ชันยูทิลิตี้สำหรับโปรแกรม SIM Management System
"""

import serial.tools.list_ports
import re
from datetime import datetime


def list_serial_ports():
    """ดึงรายชื่อพอร์ต Serial ที่มีในระบบ 
    
    Returns:
        list: รายการ tuple ของ (device, description)
        เช่น [("COM9", "Simcom HS-USB AT PORT 9001"), ...]
    """
    return [(p.device, p.description) for p in serial.tools.list_ports.comports()]


def normalize_phone_number(raw: str) -> str:
    """แปลงเบอร์โทรให้ถูกต้อง เช่น +66653988461 → 0653988461"""
    if not raw:
        return ""
    
    raw = str(raw).strip()
    # ถ้ามี payload ต่อหลังเบอร์ให้ตัดทิ้ง (เช่น "+66653988461|0E...") 
    if "|" in raw:
        raw = raw.split("|", 1)[0]
    print(f"🔍 DEBUG normalize: Input = '{raw}'")
    
    # ลบอักขระพิเศษ
    raw = raw.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    
    # แปลงรูปแบบต่างๆ
    if raw.startswith("+66"):
        raw = "0" + raw[3:]
        print(f"🔍 DEBUG normalize: After +66 conversion = '{raw}'")
    elif raw.startswith("66") and len(raw) > 10:
        raw = "0" + raw[2:]
        print(f"🔍 DEBUG normalize: After 66 conversion = '{raw}'")
    
    # เก็บแค่ตัวเลข
    digits = ''.join(filter(str.isdigit, raw))
    print(f"🔍 DEBUG normalize: Digits only = '{digits}'")
    
    # ตรวจสอบความยาว
    if len(digits) >= 10:
        result = digits[-10:]  # เอา 10 หลักสุดท้าย
    elif len(digits) >= 9:
        result = "0" + digits[-9:]  # เติม 0 ข้างหน้าถ้าขาด
    else:
        result = digits
    
    print(f"✅ DEBUG normalize: Final result = '{result}'")
    return result


def format_datetime_for_display(dt_str):
    """แปลงรูปแบบวันที่เวลาสำหรับการแสดงผล
    
    Args:
        dt_str (str): สตริงวันที่เวลา
        
    Returns:
        tuple: (date_formatted, time_formatted)
    """
    try:
        if ',' in dt_str:
            # รูปแบบ YY/MM/DD,HH:MM:SS+TZ
            date_part, time_part = dt_str.split(',', 1)
            
            # ตัดเอา timezone ออก
            if '+' in time_part:
                time_part = time_part.split('+', 1)[0]
            
            # แปลง YY/MM/DD เป็น DD/MM/YYYY
            y, m, d = date_part.split('/')
            year = int(y) + 2000 if int(y) < 100 else int(y)
            formatted_date = f"{d.zfill(2)}/{m.zfill(2)}/{year}"
            
            return formatted_date, time_part.strip()
        else:
            # รูปแบบ YYYY-MM-DD HH:MM:SS
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S")
            
    except Exception:
        return dt_str, ""


def validate_phone_number(phone):
    """ตรวจสอบความถูกต้องของเบอร์โทรศัพท์
    
    Args:
        phone (str): เบอร์โทรศัพท์ที่ต้องการตรวจสอบ
        
    Returns:
        bool: True ถ้าเบอร์ถูกต้อง
    """
    if not phone:
        return False
    
    # ลบตัวอักษรที่ไม่ใช่ตัวเลข
    phone_digits = re.sub(r'[^\d]', '', phone)
    
    # ตรวจสอบความยาว (9-10 หลัก สำหรับเบอร์ไทย)
    return len(phone_digits) >= 9 and len(phone_digits) <= 10


def encode_text_to_ucs2(text):
    """เข้ารหัสข้อความเป็น UCS2 สำหรับส่ง SMS
    
    Args:
        text (str): ข้อความที่ต้องการเข้ารหัส
        
    Returns:
        str: ข้อความที่เข้ารหัสเป็น UCS2 hex
    """
    try:
        return text.encode('utf-16-be').hex().upper()
    except Exception as e:
        print(f"Error encoding to UCS2: {e}")
        return ""

def decode_ucs2_to_text(hex_str):
    """
    แปลงข้อความจาก UCS2 hex format - เวอร์ชันปรับปรุง
    
    Args:
        hex_str: UCS2 hex string
    
    Returns:
        str: ข้อความที่แปลงแล้ว
    """
    if not hex_str:
        return ""
    
    try:
        # ทำความสะอาด hex string
        hex_clean = hex_str.replace(" ", "").strip().strip('"')
        
        # ตรวจสอบว่าเป็น hex ที่ถูกต้อง
        if len(hex_clean) % 2 != 0:
            return hex_str
        
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_clean):
            return hex_str
        
        # วิธี 1: แปลง UCS2 ทีละ 4 ตัวอักษร (สำหรับ Unicode)
        if len(hex_clean) % 4 == 0:
            text = ""
            for i in range(0, len(hex_clean), 4):
                hex_chunk = hex_clean[i:i+4]
                try:
                    char_code = int(hex_chunk, 16)
                    if char_code > 0 and char_code < 65536:
                        text += chr(char_code)
                except:
                    continue
            
            if text:
                return text.replace('\x00', '').strip()
        
        # วิธี 2: ใช้ UTF-16BE
        try:
            bytes_data = bytes.fromhex(hex_clean)
            decoded = bytes_data.decode('utf-16-be', errors='ignore')
            return decoded.replace('\x00', '').strip()
        except:
            pass
        
        # วิธี 3: ใช้ UTF-8 (สำหรับข้อความธรรมดา)
        try:
            bytes_data = bytes.fromhex(hex_clean)
            decoded = bytes_data.decode('utf-8', errors='ignore')
            return decoded.strip()
        except:
            pass
        
        return hex_str
        
    except Exception as e:
        print(f"[ERROR] UCS2 text decode failed: {e}")
        return hex_str
    
def decode_ucs2_phone_number(hex_str):
    """
    แปลงหมายเลขโทรศัพท์จาก UCS2 hex format และแปลงเป็นรูปแบบไทย (0xxxxxxxxx)
    
    Args:
        hex_str: UCS2 hex string เช่น "002B00360036003600350033003900380038003400360031"
    
    Returns:
        str: หมายเลขโทรศัพท์รูปแบบไทย เช่น "0653988461"
    """
    if not hex_str:
        return "Unknown"
    
    # ทำความสะอาด hex string
    hex_clean = hex_str.replace(" ", "").strip().strip('"')
    
    try:
        # ตรวจสอบว่าเป็น hex ที่ถูกต้อง
        if len(hex_clean) % 4 != 0:
            return hex_str
        
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_clean):
            return hex_str
        
        # แปลง UCS2 ทีละ 4 ตัวอักษร (2 bytes)
        phone_number = ""
        for i in range(0, len(hex_clean), 4):
            hex_chunk = hex_clean[i:i+4]
            if len(hex_chunk) == 4:
                try:
                    char_code = int(hex_chunk, 16)
                    if char_code > 0 and char_code < 65536:
                        character = chr(char_code)
                        phone_number += character
                except (ValueError, OverflowError):
                    continue
        
        if phone_number and len(phone_number) > 5:
            # แปลงเป็นรูปแบบไทย
            return normalize_phone_number(phone_number.strip())
        
        # Fallback: ใช้ UTF-16BE
        try:
            bytes_data = bytes.fromhex(hex_clean)
            utf16_decoded = bytes_data.decode('utf-16-be', errors='ignore')
            cleaned = utf16_decoded.replace('\x00', '').strip()
            
            if cleaned and len(cleaned) > 5:
                return normalize_phone_number(cleaned)
        except:
            pass
        
        return hex_str
        
    except Exception as e:
        print(f"[ERROR] UCS2 phone decode failed: {e}")
        return hex_str
    
def normalize_phone_number(phone_str):
    """
    แปลงหมายเลขโทรศัพท์เป็นรูปแบบไทย (0xxxxxxxxx)
    
    Args:
        phone_str: หมายเลขโทรในรูปแบบต่างๆ เช่น "+66653988461", "66653988461", "0653988461"
    
    Returns:
        str: หมายเลขโทรรูปแบบไทย เช่น "0653988461"
    """
    if not phone_str or not isinstance(phone_str, str):
        return phone_str
    
    # ลบช่องว่างและตัวอักษรพิเศษ
    clean_phone = phone_str.strip().replace(" ", "").replace("-", "")
    
    # กรณี +66xxxxxxxxx -> 0xxxxxxxxx
    if clean_phone.startswith("+66"):
        return "0" + clean_phone[3:]
    
    # กรณี 66xxxxxxxxx -> 0xxxxxxxxx
    elif clean_phone.startswith("66") and len(clean_phone) == 11:
        return "0" + clean_phone[2:]
    
    # กรณี 0xxxxxxxxx (ถูกต้องแล้ว)
    elif clean_phone.startswith("0") and len(clean_phone) == 10:
        return clean_phone
    
    # กรณีอื่นๆ คืนค่าเดิม
    else:
        return phone_str

def get_carrier_from_imsi(imsi):
    """ระบุผู้ให้บริการจาก IMSI
    Args:
        imsi (str): IMSI number
    Returns:
        str: ชื่อผู้ให้บริการ
    """
    if not imsi or len(imsi) < 5:
        return "Unknown"
    
    # รหัสผู้ให้บริการในประเทศไทย
    carrier_codes = {
        "52001": "AIS",
        "52005": "DTAC", 
        "52003": "TRUE",
        "52000": "CAT",
        "52015": "TOT",
        "52018": "dtac",
        "52023": "AIS",
        "52047": "NT"
    }
    
    # ตรวจสอบ 5 หลักแรก
    mcc_mnc = imsi[:5]
    return carrier_codes.get(mcc_mnc, "Unknown")


def format_signal_strength(rssi):
    """แปลงค่า RSSI เป็นข้อความและแท่งสัญญาณ
    
    Args:
        rssi (int): ค่า RSSI
        
    Returns:
        str: ข้อความแสดงสัญญาณพร้อมแท่งสัญญาณ Unicode
    """
    if rssi == 99:
        return '▁▁▁▁ Unknown'
    elif rssi == 0:
        return '▁▁▁▁ No Signal'
    
    # แปลงเป็น dBm
    dbm = -113 + 2 * rssi
    
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


def get_signal_color_by_strength(signal_text):
    """กำหนดสีตามความแรงสัญญาณ
    
    Args:
        signal_text (str): ข้อความสัญญาณ
        
    Returns:
        str: รหัสสี hex
    """
    try:
        # ตรวจสอบสถานะพิเศษ
        if 'No SIM' in signal_text or 'SIM Not Ready' in signal_text:
            return '#95a5a6'  # สีเทา - ไม่มีซิม
        elif 'No Network' in signal_text:
            return '#e67e22'  # สีส้ม - ไม่มีเครือข่าย
        elif 'PIN Required' in signal_text:
            return '#f39c12'  # สีเหลือง - ต้องใส่ PIN
        elif 'Error' in signal_text:
            return '#e74c3c'  # สีแดง - ข้อผิดพลาด
        elif 'Unknown' in signal_text:
            return '#95a5a6'  # สีเทา - ไม่ทราบ
        
        # ตรวจสอบ bars pattern
        if '▁▃▅█' in signal_text:
            return '#27ae60'  # เขียวสด - Excellent
        elif '▁▃▅▇' in signal_text:
            return '#2ecc71'  # เขียว - Good
        elif '▁▃▁▁' in signal_text:
            return '#f39c12'  # เหลือง/ส้ม - Fair
        elif '▁▁▁▁' in signal_text:
            if 'No Signal' in signal_text:
                return '#e74c3c'  # แดง - ไม่มีสัญญาณ
            else:
                return '#95a5a6'  # เทา - Poor
        else:
            # Fallback สำหรับ dBm values
            match = re.search(r'-?(\d+)', signal_text)
            if not match:
                return '#95a5a6'
            dbm_value = -int(match.group(1))
            if dbm_value >= -70:
                return '#27ae60'
            elif dbm_value >= -85:
                return '#2ecc71'
            elif dbm_value >= -100:
                return '#f39c12'
            elif dbm_value >= -110:
                return '#e74c3c'
            else:
                return '#95a5a6'
    except (ValueError, AttributeError):
        return '#95a5a6'  # fallback color


def get_timestamp_formatted():
    """ดึงเวลาปัจจุบันในรูปแบบที่กำหนด
    
    Returns:
        str: เวลาในรูปแบบ YYYY-MM-DD HH:MM:SS
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_get_attr(obj, attr_name, default="-"):
    """ดึงค่า attribute อย่างปลอดภัย
    
    Args:
        obj: อ็อบเจ็กต์ที่ต้องการดึงค่า
        attr_name (str): ชื่อ attribute
        default: ค่าเริ่มต้นถ้าไม่มี attribute
        
    Returns:
        ค่าของ attribute หรือค่าเริ่มต้น
    """
    return getattr(obj, attr_name, default) if hasattr(obj, attr_name) else default