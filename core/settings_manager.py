# settings_manager.py
"""
จัดการการตั้งค่าโปรแกรม
"""

import json
import os
from pathlib import Path


class SettingsManager:
    """จัดการการตั้งค่าโปรแกรม"""
    
    def __init__(self, settings_file="settings.json"):
        self.settings_file = settings_file
        self.default_settings = {
            'auto_sms_monitor': True,
            'last_port': '',
            'last_baudrate': '115200',
            'log_dir': '\\\\KITTIPHON\\Simbox-log',
            'window_geometry': {
                'x': 100,
                'y': 100,
                'width': 1050,
                'height': 700
            },
            'auto_sync': True,
            'sync_interval': 300000,  # 5 นาที
            'show_notifications': True,
            'theme': 'default'
        }
    
    def load_settings(self):
        """โหลดการตั้งค่าจากไฟล์
        Returns:
            dict: การตั้งค่าที่โหลด
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # รวมกับค่าเริ่มต้นเพื่อให้แน่ใจว่ามีครบทุกค่า
                merged_settings = self.default_settings.copy()
                merged_settings.update(settings)
                return merged_settings
            else:
                # สร้างไฟล์ settings ใหม่ถ้าไม่มี
                self.save_settings(self.default_settings)
                return self.default_settings.copy()
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.default_settings.copy()
    
    def save_settings(self, settings):
        """บันทึกการตั้งค่าลงไฟล์
        
        Args:
            settings (dict): การตั้งค่าที่ต้องการบันทึก
            
        Returns:
            bool: True ถ้าบันทึกสำเร็จ
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """ดึงค่าการตั้งค่าตาม key
        
        Args:
            key (str): ชื่อ key ของการตั้งค่า
            default: ค่าเริ่มต้นถ้าไม่เจอ key
            
        Returns:
            ค่าการตั้งค่า
        """
        settings = self.load_settings()
        return settings.get(key, default)
    
    def set_setting(self, key, value):
        """ตั้งค่าการตั้งค่าตาม key
        
        Args:
            key (str): ชื่อ key ของการตั้งค่า
            value: ค่าที่ต้องการตั้ง
            
        Returns:
            bool: True ถ้าตั้งค่าสำเร็จ
        """
        try:
            settings = self.load_settings()
            settings[key] = value
            return self.save_settings(settings)
            
        except Exception as e:
            print(f"Error setting {key}: {e}")
            return False
    
    def update_window_geometry(self, x, y, width, height):
        """อัพเดทการตั้งค่าตำแหน่งและขนาดหน้าต่าง
        
        Args:
            x (int): ตำแหน่ง X
            y (int): ตำแหน่ง Y
            width (int): ความกว้าง
            height (int): ความสูง
        """
        geometry = {
            'x': x,
            'y': y,
            'width': width,
            'height': height
        }
        self.set_setting('window_geometry', geometry)
    
    def get_window_geometry(self):
        """ดึงการตั้งค่าตำแหน่งและขนาดหน้าต่าง
        
        Returns:
            dict: ข้อมูล geometry ของหน้าต่าง
        """
        return self.get_setting('window_geometry', self.default_settings['window_geometry'])
    
    def update_last_connection(self, port, baudrate):
        """อัพเดทการตั้งค่าการเชื่อมต่อล่าสุด
        
        Args:
            port (str): พอร์ต Serial
            baudrate (str): Baudrate
        """
        self.set_setting('last_port', port)
        self.set_setting('last_baudrate', baudrate)
    
    def get_last_connection(self):
        """ดึงการตั้งค่าการเชื่อมต่อล่าสุด
        
        Returns:
            tuple: (port, baudrate)
        """
        port = self.get_setting('last_port', '')
        baudrate = self.get_setting('last_baudrate', '115200')
        return port, baudrate
    
    def reset_to_default(self):
        """รีเซ็ตการตั้งค่ากลับเป็นค่าเริ่มต้น
        
        Returns:
            bool: True ถ้ารีเซ็ตสำเร็จ
        """
        return self.save_settings(self.default_settings.copy())
    
    def export_settings(self, export_path):
        """ส่งออกการตั้งค่าเป็นไฟล์
        
        Args:
            export_path (str): path ที่ต้องการส่งออก
            
        Returns:
            bool: True ถ้าส่งออกสำเร็จ
        """
        try:
            settings = self.load_settings()
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
            
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, import_path):
        """นำเข้าการตั้งค่าจากไฟล์
        
        Args:
            import_path (str): path ของไฟล์ที่ต้องการนำเข้า
            
        Returns:
            bool: True ถ้านำเข้าสำเร็จ
        """
        try:
            if not os.path.exists(import_path):
                return False
                
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # ตรวจสอบและรวมกับค่าเริ่มต้น
            merged_settings = self.default_settings.copy()
            merged_settings.update(imported_settings)
            
            return self.save_settings(merged_settings)
            
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
    
    def validate_settings(self, settings):
        """ตรวจสอบความถูกต้องของการตั้งค่า
        
        Args:
            settings (dict): การตั้งค่าที่ต้องการตรวจสอบ
            
        Returns:
            tuple: (is_valid, errors)
        """
        errors = []
        
        # ตรวจสอบ log directory
        log_dir = settings.get('log_dir', '')
        if log_dir:
            try:
                Path(log_dir).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Invalid log directory: {e}")
        
        # ตรวจสอบ sync interval
        sync_interval = settings.get('sync_interval', 0)
        if not isinstance(sync_interval, int) or sync_interval < 60000:  # น้อยสุด 1 นาที
            errors.append("Sync interval must be at least 60000 ms (1 minute)")
        
        # ตรวจสอบ window geometry
        geometry = settings.get('window_geometry', {})
        if not isinstance(geometry, dict):
            errors.append("Window geometry must be a dictionary")
        else:
            required_keys = ['x', 'y', 'width', 'height']
            for key in required_keys:
                if key not in geometry or not isinstance(geometry[key], int):
                    errors.append(f"Window geometry missing or invalid: {key}")
        
        return len(errors) == 0, errors
    
    def backup_settings(self, backup_path=None):
        """สำรองการตั้งค่า
        
        Args:
            backup_path (str): path สำหรับไฟล์สำรอง (optional)
            
        Returns:
            str: path ของไฟล์สำรอง หรือ None ถ้าล้มเหลว
        """
        try:
            if backup_path is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"settings_backup_{timestamp}.json"
            
            return backup_path if self.export_settings(backup_path) else None
            
        except Exception as e:
            print(f"Error backing up settings: {e}")
            return None


class ThemeManager:
    """จัดการธีมและสไตล์"""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.available_themes = {
            'default': 'Default Theme',
            'dark': 'Dark Theme', 
            'light': 'Light Theme',
            'red_corporate': 'Red Corporate Theme'
        }
    
    def get_current_theme(self):
        """ดึงธีมปัจจุบัน
        
        Returns:
            str: ชื่อธีม
        """
        return self.settings_manager.get_setting('theme', 'default')
    
    def set_theme(self, theme_name):
        """ตั้งค่าธีม
        
        Args:
            theme_name (str): ชื่อธีม
            
        Returns:
            bool: True ถ้าตั้งค่าสำเร็จ
        """
        if theme_name in self.available_themes:
            return self.settings_manager.set_setting('theme', theme_name)
        return False
    
    def get_available_themes(self):
        """ดึงรายการธีมที่มี
        
        Returns:
            dict: รายการธีม
        """
        return self.available_themes.copy()
    
    def apply_theme_to_widget(self, widget, theme_name=None):
        """ใช้ธีมกับ widget
        
        Args:
            widget: Widget ที่ต้องการใช้ธีม
            theme_name (str): ชื่อธีม (optional)
        """
        if theme_name is None:
            theme_name = self.get_current_theme()
        
        try:
            if theme_name == 'red_corporate':
                from styles import MainWindowStyles
                widget.setStyleSheet(MainWindowStyles.get_main_window_style())
            elif theme_name == 'dark':
                widget.setStyleSheet("""
                    QWidget {
                        background-color: #2b2b2b;
                        color: #ffffff;
                    }
                    QGroupBox {
                        border: 1px solid #555555;
                        border-radius: 5px;
                        margin-top: 10px;
                        font-weight: bold;
                    }
                """)
            elif theme_name == 'light':
                widget.setStyleSheet("""
                    QWidget {
                        background-color: #ffffff;
                        color: #000000;
                    }
                    QGroupBox {
                        border: 1px solid #cccccc;
                        border-radius: 5px;
                        margin-top: 10px;
                        font-weight: bold;
                    }
                """)
            # default theme ไม่ต้องตั้งค่าอะไร
            
        except Exception as e:
            print(f"Error applying theme: {e}")