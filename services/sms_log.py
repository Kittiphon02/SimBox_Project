import csv
import os
import json
from datetime import datetime
from pathlib import Path
from core.utility_functions import normalize_phone_number
import pytz
import portalocker

def get_log_directory():
    """ดึง log directory จาก settings.json พร้อม fallback ให้ปลอดภัย"""
    try:
        with open('settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        log_dir = settings.get('log_dir', './log')
        
        # ตรวจสอบว่าเป็น network path หรือไม่
        if log_dir.startswith('//') or log_dir.startswith('\\\\'):
            # แปลงเป็น Windows format ถ้าต้องการ
            network_path_str = log_dir.replace('//', '\\\\')
            network_path = Path(network_path_str)
            
            try:
                # ลองสร้าง directory และทดสอบการเข้าถึง
                network_path.mkdir(parents=True, exist_ok=True)
                
                # ทดสอบการเขียนไฟล์
                import time
                test_file = network_path / f"test_access_{int(time.time())}.tmp"
                test_file.write_text("test", encoding='utf-8')
                test_file.unlink()
                
                print(f"✅ Using network log directory: {network_path}")
                return str(network_path)
                
            except PermissionError as e:
                print(f"⚠️ Permission denied for network directory ({e}), using local backup")
            except FileNotFoundError as e:
                print(f"⚠️ Network path not found ({e}), using local backup")
            except Exception as e:
                print(f"⚠️ Network directory unavailable ({e}), using local backup")
                
            # Fallback to local
            local_backup = Path('./log')
            local_backup.mkdir(exist_ok=True)
            return str(local_backup)
        else:
            # Local path
            local_path = Path(log_dir)
            local_path.mkdir(exist_ok=True)
            return str(local_path)
            
    except FileNotFoundError:
        print("⚠️ settings.json not found, using default local directory")
        local_path = Path('./log')
        local_path.mkdir(exist_ok=True)
        return str(local_path)
    except Exception as e:
        print(f"Error reading settings: {e}")
        # Fallback to local
        local_path = Path('./log')
        local_path.mkdir(exist_ok=True)
        return str(local_path)

def ensure_dir_for_file(filepath: str):
    """สร้างโฟลเดอร์ให้ filepath ถ้ายังไม่มี"""
    folder = os.path.dirname(filepath)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

def get_log_file_path(filename: str):
    """ดึง path เต็มของไฟล์ log"""
    log_dir = get_log_directory()
    return os.path.join(log_dir, filename)

def append_sms_log(filename: str,phone: str,message: str,status: str,tz_offset: str = "+07") -> bool:
    """
    เขียนบรรทัดใหม่แบบ CSV:
    "DD/MM/YYYY,HH:MM:SS+TZ",phone,message,status
    """
    from datetime import datetime
    # เตรียม timestamp ในโซน +07
    now = datetime.now()
    ts = now.strftime(f"%d/%m/%Y,%H:%M:%S{tz_offset}")
    line = f'"{ts}",{phone},{message},{status}'

    # หา path และสร้างโฟลเดอร์ถ้ายังไม่มี
    log_path = get_log_file_path(filename)
    ensure_dir_for_file(log_path)

    try:
        # เขียนแบบ append พร้อมล็อกไฟล์
        import portalocker
        with portalocker.Lock(log_path, 'a', encoding='utf-8-sig') as f:
            f.write(line + "\n")
        return True
    except Exception as e:
        print(f"❌ append_sms_log failed: {e}")
        return False

def log_sms_sent(phone: str,message: str,status: str = "ส่งสำเร็จ",log_file: str = None):
    """บันทึก SMS ที่ส่งออกไป - Enhanced with Network Support"""
    if log_file is None:
        log_file = get_log_file_path("sms_sent_log.csv")
    
    ensure_dir_for_file(log_file)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_new = not os.path.isfile(log_file) or os.path.getsize(log_file) == 0

    try:
        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["Datetime", "Phone", "Message", "Status"])
            writer.writerow([now, phone, message, status])
        
        print(f"📤 SMS sent log saved to: {log_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving SMS sent log: {e}")
        
        # ลองบันทึกใน local backup
        try:
            local_file = os.path.join("./log", "sms_sent_log.csv")
            ensure_dir_for_file(local_file)
            
            with open(local_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not os.path.isfile(local_file) or os.path.getsize(local_file) == 0:
                    writer.writerow(["Datetime", "Phone", "Message", "Status"])
                writer.writerow([now, phone, message, status])
            
            print(f"📤 SMS sent log saved to local backup: {local_file}")
            return True
            
        except Exception as backup_error:
            print(f"❌ Failed to save to local backup: {backup_error}")
            return False

def log_sms_inbox(sender: str, message: str, status: str = "รับเข้า (real-time)", log_file: str = None):
    """บันทึก SMS inbox - ใช้วันที่ปัจจุบันจาก timezone เอเชีย"""
    if log_file is None:
        log_file = get_log_file_path("sms_inbox_log.csv")

    ensure_dir_for_file(log_file)

    # ✅ ใช้เวลาจาก timezone เอเชีย
    tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(tz)
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M:%S")
    timestamp = f"{date_str},{time_str}+07"

    print(f"🔍 DEBUG log_sms_inbox: Using timestamp = {timestamp}")

    if sender:
        # เก็บเบอร์จริงโดยตรง ไม่ผ่าน normalize
        sender = sender.strip()
    else:
        print("❌ Sender is None or empty")
        return False

    try:
        is_new = not os.path.isfile(log_file) or os.path.getsize(log_file) == 0
        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["Received_Time", "Sender", "Message", "Status"])
            writer.writerow([f'"{timestamp}"', sender, f'"{message}"', f'"{status}"'])
        print(f"✅ [Log Saved] SMS from {sender} recorded with current date: {date_str}")
        return True

    except Exception as e:
        print(f"❌ Error saving SMS inbox log: {e}")
        return False

def export_sms_inbox_to_csv(sms_list: list[tuple],csv_file: str = None):
    """ส่งออก sms_list ไปเป็น CSV ใหม่ - Enhanced with Network Support"""
    if csv_file is None:
        csv_file = get_log_file_path("sms_inbox_log.csv")
    
    ensure_dir_for_file(csv_file)
    
    try:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Datetime", "Sender", "Message", "Status"])
            for item in sms_list:
                writer.writerow(item)
        
        print(f"📊 SMS export completed to: {csv_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error exporting SMS: {e}")
        return False

def sync_logs_from_network_to_local():
    """ซิงค์ log จาก network ไป local (สำหรับ backup)"""
    try:
        settings_path = Path('settings.json')
        if not settings_path.exists():
            return False
            
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        network_dir = settings.get('log_dir')
        if not network_dir or not (network_dir.startswith('//') or network_dir.startswith('\\\\')):
            return False  # ไม่ใช่ network path
        
        network_path = Path(network_dir)
        local_path = Path('./log')
        local_path.mkdir(exist_ok=True)
        
        log_files = ["sms_sent_log.csv", "sms_inbox_log.csv"]
        
        for filename in log_files:
            network_file = network_path / filename
            local_file = local_path / filename
            
            if network_file.exists():
                if not local_file.exists() or network_file.stat().st_mtime > local_file.stat().st_mtime:
                    import shutil
                    shutil.copy2(network_file, local_file)
                    print(f"📥 Synced from network: {filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return False

def sync_logs_from_local_to_network():
    """ซิงค์ log จาก local ไป network"""
    try:
        settings_path = Path('settings.json')
        if not settings_path.exists():
            return False
            
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        network_dir = settings.get('log_dir')
        if not network_dir or not (network_dir.startswith('//') or network_dir.startswith('\\\\')):
            return False  # ไม่ใช่ network path
        
        network_path = Path(network_dir)
        local_path = Path('./log')
        
        if not local_path.exists():
            return False
        
        # สร้าง network directory
        network_path.mkdir(parents=True, exist_ok=True)
        
        log_files = ["sms_sent_log.csv", "sms_inbox_log.csv"]
        
        for filename in log_files:
            local_file = local_path / filename
            network_file = network_path / filename
            
            if local_file.exists():
                if not network_file.exists() or local_file.stat().st_mtime > network_file.stat().st_mtime:
                    import shutil
                    shutil.copy2(local_file, network_file)
                    print(f"📤 Synced to network: {filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return False

# ตัวอย่างใช้งาน
if __name__ == "__main__":
    # ทดสอบการใช้งาน
    print("📝 Testing enhanced SMS logging...")
    
    # ทดสอบบันทึก SMS
    log_sms_sent("0812345678", "ทดสอบข้อความ", "ส่งสำเร็จ")
    log_sms_inbox("0897654321", "ข้อความเข้า", "รับเข้า")
    
    # ทดสอบการซิงค์
    print("\n🔄 Testing sync...")
    sync_logs_from_network_to_local()
    sync_logs_from_local_to_network()