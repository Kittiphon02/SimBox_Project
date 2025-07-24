# core/constants.py
"""
ค่าคงที่สำหรับโปรแกรม SIM Management System
"""

# Application Info
APP_NAME = "SIM Management System"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "โปรแกรมจัดการซิมการ์ดและส่ง SMS"
APP_AUTHOR = "SIM Management Team"

# Default Settings
DEFAULT_BAUDRATE = "115200"
DEFAULT_TIMEOUT = 5
DEFAULT_WINDOW_WIDTH = 1050
DEFAULT_WINDOW_HEIGHT = 700

# SMS Settings
SMS_MAX_LENGTH = 160
SMS_UCS2_MAX_LENGTH = 70
SMS_ENCODING_UCS2 = "UCS2"
SMS_ENCODING_GSM7 = "GSM7"

# Signal Strength Thresholds (dBm)
SIGNAL_EXCELLENT = -70
SIGNAL_GOOD = -85
SIGNAL_FAIR = -100
SIGNAL_POOR = -110

# Signal Colors
SIGNAL_COLORS = {
    'excellent': '#27ae60',
    'good': '#2ecc71',
    'fair': '#f39c12',
    'poor': '#e74c3c',
    'no_signal': '#95a5a6'
}

# Carrier Codes (Thailand)
CARRIER_CODES = {
    "52001": "AIS",
    "52005": "DTAC", 
    "52003": "TRUE",
    "52000": "CAT",
    "52015": "TOT",
    "52018": "dtac",
    "52023": "AIS",
    "52047": "NT"
}

# AT Commands
DEFAULT_AT_COMMANDS = [
    "AT", "ATI", "AT+CNUM", "AT+CIMI", "AT+CCID", "AT+CSQ",
    "AT+CMGF=1", "AT+CPIN?", "AT+CGSN", "AT+CMGL=\"STO SENT\"",
    "AT+CMGW=\"0653988461\"", "AT+CMSS=3", "AT+CMGL=\"REC READ\"",
    "AT+CMGL=\"STO UNSENT\"", "AT+CMGL=\"REC UNREAD\"", "AT+CMGL=\"ALL\"",
    "AT+NETOPEN", "AT+CNMI=2,2,0,0,0", "AT+RUN", "AT+STOP", "AT+CLEAR"
]

# Special AT Commands
SPECIAL_COMMANDS = {
    "AT+RUN": "start_sms_monitoring",
    "AT+STOP": "stop_sms_monitoring", 
    "AT+CLEAR": "clear_sms_monitoring"
}

# File Names
SETTINGS_FILE = "settings.json"
AT_HISTORY_FILE = "at_command_history.txt"
SMS_SENT_LOG_FILE = "sms_sent_log.csv"
SMS_INBOX_LOG_FILE = "sms_inbox_log.csv"
APP_LOG_FILE = "app_debug.log"

# Directory Names
LOGS_DIR = "logs"
DATA_DIR = "data"
CONFIG_DIR = "config"
STYLES_DIR = "styles"

# Themes
AVAILABLE_THEMES = {
    'default': 'Default Theme',
    'dark': 'Dark Theme', 
    'light': 'Light Theme',
    'red_corporate': 'Red Corporate Theme'
}

# Sync Settings
SYNC_INTERVAL_DEFAULT = 300000  # 5 นาที
SYNC_TIMEOUT = 30  # 30 วินาที

# Recovery Settings
RECOVERY_TIMEOUT = 10000  # 10 วินาที
MAX_RECOVERY_ATTEMPTS = 3

# UI Constants
BUTTON_WIDTH_SMALL = 100
BUTTON_WIDTH_MEDIUM = 120
BUTTON_WIDTH_LARGE = 150
BUTTON_HEIGHT_DEFAULT = 40

# Port Settings
SUPPORTED_BAUDRATES = ['9600', '19200', '38400', '57600', '115200']
DEFAULT_PORT_TIMEOUT = 3

# SMS Status
SMS_STATUS = {
    'sent': 'ส่งสำเร็จ',
    'failed': 'ล้มเหลว',
    'pending': 'รอส่ง',
    'received': 'รับเข้า',
    'read': 'อ่านแล้ว',
    'unread': 'ยังไม่อ่าน'
}

# Log Levels
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

# Network Settings
NETWORK_SHARE_TIMEOUT = 5  # วินาที
NETWORK_RETRY_COUNT = 3

# Unicode Signal Bars
SIGNAL_BARS = {
    'no_signal': '▁▁▁▁',
    'poor': '▁▁▁▁',
    'fair': '▁▃▁▁', 
    'good': '▁▃▅▇',
    'excellent': '▁▃▅█'
}

# Error Messages
ERROR_MESSAGES = {
    'no_port': 'กรุณาเลือกพอร์ต Serial',
    'no_connection': 'ไม่สามารถเชื่อมต่อได้',
    'no_sim': 'ไม่พบซิมการ์ด',
    'sim_not_ready': 'ซิมการ์ดไม่พร้อม',
    'pin_required': 'ต้องใส่รหัส PIN',
    'puk_required': 'ต้องใส่รหัส PUK',
    'network_error': 'เกิดข้อผิดพลาดในการเชื่อมต่อเครือข่าย',
    'sms_failed': 'ส่ง SMS ไม่สำเร็จ',
    'invalid_phone': 'เบอร์โทรศัพท์ไม่ถูกต้อง',
    'empty_message': 'กรุณาใส่ข้อความ'
}

# Success Messages
SUCCESS_MESSAGES = {
    'sms_sent': 'ส่ง SMS สำเร็จ',
    'sim_ready': 'ซิมการ์ดพร้อมใช้งาน',
    'connection_ok': 'เชื่อมต่อสำเร็จ',
    'recovery_success': 'กู้คืนซิมการ์ดสำเร็จ',
    'sync_complete': 'ซิงค์ข้อมูลสำเร็จ'
}

# Window Flags
WINDOW_FLAGS_MAIN = "Window | WindowMinimizeButtonHint | WindowMaximizeButtonHint | WindowCloseButtonHint"
WINDOW_FLAGS_DIALOG = "Dialog | CustomizeWindowHint | WindowTitleHint"