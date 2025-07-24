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


def normalize_phone_number(phone):
    """ปรับรูปแบบเบอร์โทรศัพท์ให้เป็นมาตรฐาน
    
    Args:
        phone (str): เบอร์โทรศัพท์ที่ต้องการปรับรูปแบบ
        
    Returns:
        str: เบอร์โทรศัพท์ที่ปรับรูปแบบแล้ว
    """
    if not phone:
        return ""
    
    # ลบ - และ space
    phone = phone.replace('-', '').replace(' ', '')
    
    # แปลงรูปแบบ +66 หรือ 66 ให้เป็น 0
    if phone.startswith('+66'):
        phone = '0' + phone[3:]
    elif phone.startswith('66'):
        phone = '0' + phone[2:]
    
    return phone


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
    """แปลง UCS2 hex string เป็นข้อความ
    
    Args:
        hex_str (str): UCS2 hex string
        
    Returns:
        str: ข้อความที่แปลงแล้ว
    """
    if not hex_str:
        return ""
        
    try:
        # ลบช่องว่างและปรับความยาว
        hex_str = hex_str.replace(" ", "").upper()
        
        if len(hex_str) % 2 != 0:
            hex_str = hex_str.ljust((len(hex_str) + 3) // 4 * 4, '0')
        
        # แปลงเป็น bytes และ decode
        bytes_data = bytes.fromhex(hex_str)
        
        # ลอง decode หลายวิธี
        for encoding in ['utf-16-be', 'utf-16-le', 'utf-8']:
            try:
                return bytes_data.decode(encoding, errors='strict')
            except UnicodeDecodeError:
                continue
        
        # fallback
        return bytes_data.decode('utf-16-be', errors='replace')
        
    except Exception as e:
        print(f"Error decoding UCS2: {e}")
        return hex_str


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