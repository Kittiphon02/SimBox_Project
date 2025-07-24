# sim_model.py
import serial
import time
import re

class Sim:
    def __init__(self, phone, imsi, iccid, carrier ):
        self.phone = phone
        self.imsi = imsi
        self.iccid = iccid
        self.carrier = carrier
        self.signal = None

def read_sim_info(port, baudrate=115200):
    """อ่านข้อมูลซิมพร้อมตรวจสอบสถานะ"""
    try:
        ser = serial.Serial(port, baudrate, timeout=3)
        time.sleep(0.3)
        
        # ตรวจสอบสถานะ SIM ก่อน
        ser.write(b'AT+CPIN?\r\n')
        time.sleep(0.5)
        cpin_response = ser.read(200).decode(errors="ignore")
        
        # ถ้า SIM ไม่พร้อมให้คืนค่าว่าง
        if "CPIN: READY" not in cpin_response:
            ser.close()
            return {
                "phone": "-",
                "imsi": "-",
                "iccid": "-",
                "error": "SIM not ready or not inserted",
                "cpin_status": cpin_response.strip()
            }
        
        # อ่านเบอร์โทร
        ser.write(b'AT+CNUM\r')
        time.sleep(0.3)
        response = ser.read_all().decode(errors="ignore")
        
        # อ่าน IMSI
        ser.write(b'AT+CIMI\r')
        time.sleep(0.3)
        imsi = ser.read_all().decode(errors="ignore")
        
        # อ่าน ICCID
        ser.write(b'AT+CCID\r')
        time.sleep(0.3)
        iccid = ser.read_all().decode(errors="ignore")
        
        ser.close()

        # ประมวลผลเบอร์โทร
        phone = ""
        for line in response.splitlines():
            if "+CNUM:" in line:
                try:
                    phone = line.split(",")[1].replace('"', '').strip()
                except:
                    phone = ""
        
        # ประมวลผล IMSI
        imsi_clean = ''.join([c for c in imsi if c.isdigit()])
        
        # ประมวลผล ICCID
        iccid_clean = ''.join([c for c in iccid if c.isdigit()])

        # ตรวจสอบความถูกต้องของ IMSI
        if len(imsi_clean) < 15:
            return {
                "phone": phone if phone else "-",
                "imsi": "-",
                "iccid": iccid_clean if iccid_clean else "-",
                "error": "Invalid IMSI length"
            }

        return {
            "phone": phone if phone else "-",
            "imsi": imsi_clean if imsi_clean else "-",
            "iccid": iccid_clean if iccid_clean else "-"
        }
        
    except Exception as e:
        return {
            "phone": "-",
            "imsi": "-",
            "iccid": "-",
            "error": str(e)
        }
    
def read_signal_strength(port, baudrate=115200):
    """ส่ง AT+CSQ แล้วคืนค่าเป็น '-81 dBm' หรือ 'Unknown'"""
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        ser.write(b'AT+CSQ\r\n')
        time.sleep(0.2)
        raw = ser.read_all().decode(errors='ignore')
        ser.close()
        m = re.search(r'\+CSQ: (\d+),', raw)
        if not m:
            return 'N/A'
        rssi = int(m.group(1))
        if rssi == 99:
            return 'Unknown'
        dbm = -113 + 2*rssi
        return f'{dbm} dBm'
    except:
        return 'Error'

def load_sim_data(port="COM3", baudrate=115200):
    """โหลดข้อมูล SIM พร้อมตรวจสอบสถานะ"""
    info = read_sim_info(port, baudrate)
    
    # ตรวจสอบว่ามีซิมหรือไม่
    if info.get("imsi", "-") == "-" or info.get("imsi", "-") == "":
        # ไม่มีซิมหรือซิมไม่พร้อม
        sim = Sim("-", "-", "-", "No SIM")
        sim.signal = "▁▁▁▁ No SIM"
        return [sim]
    
    # ตรวจสอบและตั้งค่าค่ายตาม IMSI 
    carrier = "Unknown"
    if info["imsi"].startswith("52001"):
        carrier = "AIS"
    elif info["imsi"].startswith("52005"):
        carrier = "DTAC"
    elif info["imsi"].startswith("52003"):
        carrier = "TRUE"

    # เอา ICCID มาเป็นสถานะ (ถ้าไม่มีให้ "Unknown")
    iccid = info.get("iccid", "-")

    sim = Sim(info["phone"], info["imsi"], iccid, carrier)
    
    # อ่านสัญญาณเฉพาะเมื่อมีซิม
    if info["imsi"] != "-":
        sim.signal = read_signal_strength_with_sim_check(port, baudrate)
    else:
        sim.signal = "▁▁▁▁ No SIM"
    
    return [sim]

def read_signal_strength_with_sim_check(port, baudrate=115200):
    """อ่านสัญญาณพร้อมตรวจสอบสถานะซิม"""
    try:
        ser = serial.Serial(port, baudrate, timeout=3)
        time.sleep(0.1)
        
        # ตรวจสอบสถานะ SIM ก่อน
        ser.write(b'AT+CPIN?\r\n')
        time.sleep(0.3)
        cpin_response = ser.read(200).decode(errors='ignore')
        
        if "CPIN: READY" not in cpin_response:
            ser.close()
            if "SIM NOT INSERTED" in cpin_response:
                return '▁▁▁▁ No SIM Card'
            elif "SIM PIN" in cpin_response:
                return '▁▁▁▁ PIN Required'
            else:
                return '▁▁▁▁ SIM Not Ready'
        
        # ตรวจสอบการลงทะเบียนเครือข่าย
        ser.write(b'AT+CREG?\r\n')
        time.sleep(0.3)
        creg_response = ser.read(200).decode(errors='ignore')
        
        if "+CREG: 0,1" not in creg_response and "+CREG: 0,5" not in creg_response:
            ser.close()
            return '▁▁▁▁ No Network'
        
        # อ่านค่าสัญญาณ
        ser.write(b'AT+CSQ\r\n')
        time.sleep(0.2)
        raw = ser.read(200).decode(errors='ignore')
        ser.close()
        
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
            return f'▁▃▅█ {dbm} dBm (Excellent)'
        elif dbm >= -85:
            return f'▁▃▅▇ {dbm} dBm (Good)'
        elif dbm >= -100:
            return f'▁▃▁▁ {dbm} dBm (Fair)'
        elif dbm >= -110:
            return f'▁▁▁▁ {dbm} dBm (Poor)'
        else:
            return f'▁▁▁▁ {dbm} dBm (Very Poor)'
            
    except Exception as e:
        return '▁▁▁▁ Error'