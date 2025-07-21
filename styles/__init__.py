# styles/__init__.py
"""
โมดูลสไตล์สำหรับระบบจัดการ SIM
โทนสีแดงทางการสำหรับทุกหน้าของโปรแกรม
"""

from .main_window_styles import MainWindowStyles
from .loading_widget_styles import LoadingWidgetStyles
from .sms_log_dialog_styles import SmsLogDialogStyles
from .sms_realtime_monitor_styles import SmsRealtimeMonitorStyles
from .sim_table_widget_styles import SimTableWidgetStyles

__all__ = [
    'MainWindowStyles',
    'LoadingWidgetStyles', 
    'SmsLogDialogStyles',
    'SmsRealtimeMonitorStyles',
    'SimTableWidgetStyles'
]

# ==================== GLOBAL COLOR SCHEME ====================
class GlobalColorScheme:
    """ชุดสีหลักสำหรับทั้งระบบ - โทนสีแดงทางการ"""
    
    # Primary Colors - สีหลัก
    PRIMARY = '#dc3545'           # แดงหลัก
    PRIMARY_DARK = '#c82333'      # แดงเข้ม
    PRIMARY_DARKER = '#a71e2a'    # แดงเข้มมาก
    PRIMARY_LIGHT = '#e95569'     # แดงอ่อน
    PRIMARY_LIGHTER = '#f5c6cb'   # แดงอ่อนมาก
    
    # Secondary Colors - สีรอง
    SECONDARY = '#6c757d'         # เทา
    SECONDARY_DARK = '#5a6268'    # เทาเข้ม
    SECONDARY_LIGHT = '#adb5bd'   # เทาอ่อน
    
    # Status Colors - สีสถานะ
    SUCCESS = '#198754'           # เขียว
    SUCCESS_LIGHT = '#d1e7dd'     # เขียวอ่อน
    INFO = '#0d6efd'             # น้ำเงิน
    INFO_LIGHT = '#cfe2ff'       # น้ำเงินอ่อน
    WARNING = '#fd7e14'          # ส้ม
    WARNING_LIGHT = '#fff3cd'    # ส้มอ่อน
    DANGER = '#dc3545'           # แดงอันตราย
    DANGER_LIGHT = '#f8d7da'     # แดงอ่อน
    
    # Background Colors - สีพื้นหลัง
    BACKGROUND_MAIN = '#fdf2f2'   # พื้นหลังหลัก
    BACKGROUND_SURFACE = '#fff5f5' # พื้นผิว
    BACKGROUND_CARD = '#fff'      # การ์ด
    
    # Text Colors - สีข้อความ
    TEXT_PRIMARY = '#721c24'      # ข้อความหลัก
    TEXT_SECONDARY = '#6c757d'    # ข้อความรอง
    TEXT_MUTED = '#adb5bd'       # ข้อความจาง
    TEXT_WHITE = '#fff'          # ข้อความขาว
    
    # Border Colors - สีเส้นขอบ
    BORDER_MAIN = '#dc3545'       # เส้นขอบหลัก
    BORDER_LIGHT = '#f5c6cb'      # เส้นขอบอ่อน
    BORDER_SECONDARY = '#dee2e6'  # เส้นขอบรอง
    
    @classmethod
    def get_gradient_primary(cls):
        """ส่งคืน gradient สีแดงหลัก"""
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {cls.PRIMARY}, stop:1 {cls.PRIMARY_DARK})"
    
    @classmethod
    def get_gradient_success(cls):
        """ส่งคืน gradient สีเขียว"""
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {cls.SUCCESS}, stop:1 #157347)"
    
    @classmethod
    def get_gradient_info(cls):
        """ส่งคืน gradient สีน้ำเงิน"""
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {cls.INFO}, stop:1 #0b5ed7)"

# ==================== STYLE UTILITY FUNCTIONS ====================
class StyleUtils:
    """ฟังก์ชันยูทิลิตี้สำหรับสไตล์"""
    
    @staticmethod
    def create_button_style(bg_color, hover_color, pressed_color, text_color='white'):
        """สร้างสไตล์ปุ่มแบบกำหนดเอง"""
        return f"""
            QPushButton {{
                background: {bg_color};
                color: {text_color};
                border: none;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {hover_color};
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            QPushButton:pressed {{
                background: {pressed_color};
                padding-top: 9px;
            }}
            QPushButton:disabled {{
                background: #6c757d;
                color: #adb5bd;
            }}
        """
    
    @staticmethod
    def create_input_style(border_color, focus_color, bg_color='white'):
        """สร้างสไตล์ช่องป้อนข้อมูลแบบกำหนดเอง"""
        return f"""
            QLineEdit, QTextEdit {{
                border: 2px solid {border_color};
                border-radius: 6px;
                padding: 8px;
                background-color: {bg_color};
                font-size: 14px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {focus_color};
                outline: none;
            }}
            QLineEdit:hover, QTextEdit:hover {{
                border-color: {GlobalColorScheme.PRIMARY_DARK};
            }}
        """
    
    @staticmethod
    def create_card_style(bg_color, border_color):
        """สร้างสไตล์การ์ดแบบกำหนดเอง"""
        return f"""
            QWidget {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 10px;
                padding: 15px;
            }}
        """
    
    @staticmethod
    def darken_color(color, factor=0.2):
        """ทำให้สีเข้มขึ้น"""
        color_map = {
            GlobalColorScheme.PRIMARY: GlobalColorScheme.PRIMARY_DARK,
            GlobalColorScheme.SUCCESS: '#157347',
            GlobalColorScheme.INFO: '#0b5ed7',
            GlobalColorScheme.WARNING: '#e8590c'
        }
        return color_map.get(color, color)
    
    @staticmethod
    def lighten_color(color, factor=0.2):
        """ทำให้สีอ่อนลง"""
        color_map = {
            GlobalColorScheme.PRIMARY: GlobalColorScheme.PRIMARY_LIGHT,
            GlobalColorScheme.SUCCESS: '#20c997',
            GlobalColorScheme.INFO: '#6ea8fe',
            GlobalColorScheme.WARNING: '#ffda6a'
        }
        return color_map.get(color, color)

# ==================== THEME MANAGER ====================
class ThemeManager:
    """ตัวจัดการธีมสำหรับทั้งระบบ"""
    
    _current_theme = 'light'
    _themes = {
        'light': {
            'background': GlobalColorScheme.BACKGROUND_MAIN,
            'surface': GlobalColorScheme.BACKGROUND_SURFACE,
            'primary': GlobalColorScheme.PRIMARY,
            'text': GlobalColorScheme.TEXT_PRIMARY
        },
        'dark': {
            'background': '#2c1810',
            'surface': '#3d251a', 
            'primary': '#ff6b6b',
            'text': '#ffcccb'
        }
    }
    
    @classmethod
    def set_theme(cls, theme_name):
        """ตั้งค่าธีม"""
        if theme_name in cls._themes:
            cls._current_theme = theme_name
    
    @classmethod
    def get_current_theme(cls):
        """ได้ธีมปัจจุบัน"""
        return cls._themes[cls._current_theme]
    
    @classmethod
    def get_theme_color(cls, color_key):
        """ได้สีจากธีมปัจจุบัน"""
        theme = cls.get_current_theme()
        return theme.get(color_key, GlobalColorScheme.PRIMARY)

# ==================== RESPONSIVE DESIGN ====================
class ResponsiveDesign:
    """การออกแบบที่ตอบสนอง"""
    
    # ขนาดหน้าจอ
    SCREEN_SMALL = 800
    SCREEN_MEDIUM = 1200
    SCREEN_LARGE = 1600
    
    @classmethod
    def get_font_size(cls, base_size, screen_width):
        """คำนวณขนาดฟอนต์ตามขนาดหน้าจอ"""
        if screen_width < cls.SCREEN_SMALL:
            return base_size - 2
        elif screen_width > cls.SCREEN_LARGE:
            return base_size + 2
        return base_size
    
    @classmethod
    def get_padding(cls, base_padding, screen_width):
        """คำนวณระยะห่างตามขนาดหน้าจอ"""
        if screen_width < cls.SCREEN_SMALL:
            return max(base_padding - 4, 4)
        elif screen_width > cls.SCREEN_LARGE:
            return base_padding + 4
        return base_padding