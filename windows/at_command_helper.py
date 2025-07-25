# at_command_helper.py
"""
AT Command Helper Dialog - แสดงคำอธิบายคำสั่ง AT ยอดนิยม
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QWidget, QFrame, QTextEdit, QTabWidget,
    QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon


class ATCommandHelperDialog(QDialog):
    """Dialog แสดงคำแนะนำการใช้คำสั่ง AT"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """สร้าง UI components"""
        self.setWindowTitle("📋 AT Command Helper")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Header
        self.create_header(layout)
        
        # Main content with tabs
        self.create_tabs(layout)
        
        # Footer with buttons
        self.create_footer(layout)
    
    def create_header(self, layout):
        """สร้างส่วนหัว"""
        header_frame = QFrame()
        header_layout = QHBoxLayout()
        
        # Icon
        icon_label = QLabel("📋")
        icon_label.setFont(QFont("Arial", 24))
        header_layout.addWidget(icon_label)
        
        # Title and description
        title_layout = QVBoxLayout()
        title_label = QLabel("AT Command Helper")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        
        desc_label = QLabel("คู่มือการใช้คำสั่ง AT สำหรับโมเด็ม GSM/3G/4G")
        desc_label.setFont(QFont("Arial", 11))
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(desc_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        header_frame.setLayout(header_layout)
        layout.addWidget(header_frame)
        
        # Store references for styling
        self.header_frame = header_frame
        self.title_label = title_label
        self.desc_label = desc_label
    
    def create_tabs(self, layout):
        """สร้าง tabs แยกหมวดหมู่คำสั่ง"""
        self.tab_widget = QTabWidget()
        
        # Tab 1: Basic Commands
        self.create_basic_tab()
        
        # Tab 2: SMS Commands
        self.create_sms_tab()
        
        # Tab 3: Network Commands
        self.create_network_tab()
        
        # Tab 4: Special Commands
        self.create_special_tab()
        
        layout.addWidget(self.tab_widget)
    
    def create_basic_tab(self):
        """Tab คำสั่งพื้นฐาน"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        # Basic commands data
        basic_commands = [
            {
                "command": "AT",
                "description": "ทดสอบการเชื่อมต่อกับโมเด็ม",
                "example": "AT",
                "response": "OK",
                "usage": "ใช้เพื่อตรวจสอบว่าโมเด็มตอบสนองหรือไม่"
            },
            {
                "command": "ATI",
                "description": "แสดงข้อมูลโมเด็ม",
                "example": "ATI",
                "response": "Manufacturer: SIMCOM INCORPORATED\nModel: SIMCOM_SIM7600G-H",
                "usage": "ดูข้อมูลผู้ผลิตและรุ่นโมเด็ม"
            },
            {
                "command": "AT+CGMI",
                "description": "ดูชื่อผู้ผลิตโมเด็ม",
                "example": "AT+CGMI",
                "response": "SIMCOM INCORPORATED",
                "usage": "แสดงชื่อบริษัทผู้ผลิตโมเด็ม"
            },
            {
                "command": "AT+CGMM",
                "description": "ดูรุ่นโมเด็ม",
                "example": "AT+CGMM",
                "response": "SIMCOM_SIM7600G-H",
                "usage": "แสดงรุ่นและแบบของโมเด็ม"
            },
            {
                "command": "AT+CGMR",
                "description": "ดูเวอร์ชันเฟิร์มแวร์",
                "example": "AT+CGMR",
                "response": "SIM7600M22_V1.1.0",
                "usage": "แสดงเวอร์ชันของเฟิร์มแวร์โมเด็ม"
            },
            {
                "command": "AT+CGSN",
                "description": "ดูหมายเลข IMEI",
                "example": "AT+CGSN",
                "response": "860384063639006",
                "usage": "แสดงหมายเลข IMEI ของโมเด็ม"
            }
        ]
        
        for cmd_info in basic_commands:
            group = self.create_command_group(cmd_info)
            layout.addWidget(group)
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        self.tab_widget.addTab(tab, "🔧 คำสั่งพื้นฐาน")
    
    def create_sms_tab(self):
        """Tab คำสั่ง SMS"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        sms_commands = [
            {
                "command": "AT+CMGF=1",
                "description": "เปิดโหมด SMS แบบ Text",
                "example": "AT+CMGF=1",
                "response": "OK",
                "usage": "ตั้งค่าให้ SMS ทำงานในโหมดข้อความธรรมดา"
            },
            {
                "command": "AT+CMGS",
                "description": "ส่งข้อความ SMS",
                "example": 'AT+CMGS="0812345678"',
                "response": "> (รอข้อความ)\nสวัสดี\nCtrl+Z",
                "usage": "ส่ง SMS ไปยังเบอร์ที่ระบุ"
            },
            {
                "command": "AT+CMGL",
                "description": "อ่าน SMS ทั้งหมด",
                "example": 'AT+CMGL="ALL"',
                "response": "+CMGL: 1,\"REC READ\",\"+66812345678\"...",
                "usage": "แสดง SMS ที่เก็บในซิมการ์ด"
            },
            {
                "command": "AT+CMGR",
                "description": "อ่าน SMS ตำแหน่งที่ระบุ",
                "example": "AT+CMGR=1",
                "response": "+CMGR: \"REC READ\",\"+66812345678\"...",
                "usage": "อ่าน SMS ในตำแหน่งที่กำหนด"
            },
            {
                "command": "AT+CMGD",
                "description": "ลบ SMS",
                "example": "AT+CMGD=1,4",
                "response": "OK",
                "usage": "ลบ SMS (1=ตำแหน่ง, 4=ลบทั้งหมด)"
            },
            {
                "command": "AT+CSCS",
                "description": "ตั้งค่าการเข้ารหัสข้อความ",
                "example": 'AT+CSCS="UCS2"',
                "response": "OK",
                "usage": "ใช้สำหรับภาษาไทยและภาษาอื่นๆ"
            }
        ]
        
        for cmd_info in sms_commands:
            group = self.create_command_group(cmd_info)
            layout.addWidget(group)
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        self.tab_widget.addTab(tab, "📱 คำสั่ง SMS")
    
    def create_network_tab(self):
        """Tab คำสั่งเครือข่าย"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        network_commands = [
            {
                "command": "AT+CSQ",
                "description": "ตรวจสอบระดับสัญญาณ",
                "example": "AT+CSQ",
                "response": "+CSQ: 20,99",
                "usage": "แสดงความแรงสัญญาณ (0-31, 99=ไม่ทราบ)"
            },
            {
                "command": "AT+CPIN?",
                "description": "ตรวจสอบสถานะ SIM PIN",
                "example": "AT+CPIN?",
                "response": "+CPIN: READY",
                "usage": "ตรวจสอบว่า SIM พร้อมใช้งานหรือต้องใส่ PIN"
            },
            {
                "command": "AT+CNUM",
                "description": "ดูเบอร์โทรศัพท์ SIM",
                "example": "AT+CNUM",
                "response": '+CNUM: "","0812345678",129',
                "usage": "แสดงเบอร์โทรของ SIM ที่ใส่อยู่"
            },
            {
                "command": "AT+CIMI",
                "description": "ดูหมายเลข IMSI",
                "example": "AT+CIMI",
                "response": "520050231128663",
                "usage": "แสดงหมายเลข IMSI ของ SIM"
            },
            {
                "command": "AT+CCID",
                "description": "ดูหมายเลข ICCID",
                "example": "AT+CCID",
                "response": "89660525024875100552",
                "usage": "แสดงหมายเลข ICCID ของ SIM"
            },
            {
                "command": "AT+CREG?",
                "description": "สถานะการลงทะเบียนเครือข่าย",
                "example": "AT+CREG?",
                "response": "+CREG: 0,1",
                "usage": "ตรวจสอบการเชื่อมต่อกับเครือข่าย"
            },
            {
                "command": "AT+COPS?",
                "description": "ดูผู้ให้บริการเครือข่าย",
                "example": "AT+COPS?",
                "response": '+COPS: 0,0,"dtac"',
                "usage": "แสดงชื่อผู้ให้บริการที่เชื่อมต่ออยู่"
            }
        ]
        
        for cmd_info in network_commands:
            group = self.create_command_group(cmd_info)
            layout.addWidget(group)
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        self.tab_widget.addTab(tab, "📡 คำสั่งเครือข่าย")
    
    def create_special_tab(self):
        """Tab คำสั่งพิเศษ"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        
        special_commands = [
            {
                "command": "AT+RUN",
                "description": "เริ่ม SMS Real-time Monitor",
                "example": "AT+RUN",
                "response": "[AT+RUN] SMS Real-time monitoring started",
                "usage": "คำสั่งพิเศษของโปรแกรมนี้ - เปิด SMS Monitor"
            },
            {
                "command": "AT+STOP",
                "description": "หยุด SMS Real-time Monitor",
                "example": "AT+STOP",
                "response": "[AT+STOP] SMS Real-time monitoring stopped",
                "usage": "คำสั่งพิเศษของโปรแกรมนี้ - หยุด SMS Monitor"
            },
            {
                "command": "AT+CLEAR",
                "description": "เคลียร์ SMS Monitor Display",
                "example": "AT+CLEAR",
                "response": "[AT+CLEAR] SMS Real-time monitoring cleared",
                "usage": "คำสั่งพิเศษของโปรแกรมนี้ - ล้างหน้าจอ Monitor"
            },
            {
                "command": "AT+CFUN=0",
                "description": "ปิดการทำงานโมเด็ม",
                "example": "AT+CFUN=0",
                "response": "OK",
                "usage": "ปิดฟังก์ชันการส่งสัญญาณของโมเด็ม"
            },
            {
                "command": "AT+CFUN=1",
                "description": "เปิดการทำงานโมเด็ม",
                "example": "AT+CFUN=1",
                "response": "OK",
                "usage": "เปิดฟังก์ชันการส่งสัญญาณของโมเด็ม"
            },
            {
                "command": "ATZ",
                "description": "รีเซ็ตโมเด็ม",
                "example": "ATZ",
                "response": "OK",
                "usage": "รีเซ็ตโมเด็มกลับสู่สถานะเริ่มต้น"
            }
        ]
        
        for cmd_info in special_commands:
            group = self.create_command_group(cmd_info)
            layout.addWidget(group)
        
        # Add usage tips
        tips_group = self.create_tips_section()
        layout.addWidget(tips_group)
        
        layout.addStretch()
        content.setLayout(layout)
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        
        self.tab_widget.addTab(tab, "⚡ คำสั่งพิเศษ")
    
    def create_command_group(self, cmd_info):
        """สร้าง group สำหรับแต่ละคำสั่ง"""
        group = QGroupBox(f"🔹 {cmd_info['command']}")
        layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel(f"📝 {cmd_info['description']}")
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(desc_label)
        
        # Usage
        usage_label = QLabel(f"💡 {cmd_info['usage']}")
        usage_label.setWordWrap(True)
        usage_label.setFont(QFont("Arial", 10))
        layout.addWidget(usage_label)
        
        # Example and Response
        example_layout = QHBoxLayout()
        
        # Example
        example_frame = QFrame()
        example_frame.setFrameStyle(QFrame.Box)
        example_layout_inner = QVBoxLayout()
        
        example_header = QLabel("📤 ตัวอย่างคำสั่ง:")
        example_header.setFont(QFont("Arial", 9, QFont.Bold))
        example_layout_inner.addWidget(example_header)
        
        example_text = QLabel(cmd_info['example'])
        example_text.setFont(QFont("Courier New", 10))
        example_text.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        example_layout_inner.addWidget(example_text)
        
        example_frame.setLayout(example_layout_inner)
        example_layout.addWidget(example_frame)
        
        # Response
        response_frame = QFrame()
        response_frame.setFrameStyle(QFrame.Box)
        response_layout_inner = QVBoxLayout()
        
        response_header = QLabel("📥 ผลลัพธ์:")
        response_header.setFont(QFont("Arial", 9, QFont.Bold))
        response_layout_inner.addWidget(response_header)
        
        response_text = QLabel(cmd_info['response'])
        response_text.setFont(QFont("Courier New", 10))
        response_text.setStyleSheet("background-color: #e8f5e8; padding: 5px; border-radius: 3px;")
        response_text.setWordWrap(True)
        response_layout_inner.addWidget(response_text)
        
        response_frame.setLayout(response_layout_inner)
        example_layout.addWidget(response_frame)
        
        layout.addLayout(example_layout)
        
        group.setLayout(layout)
        return group
    
    def create_tips_section(self):
        """สร้างส่วนเคล็ดลับการใช้งาน"""
        tips_group = QGroupBox("💡 เคล็ดลับการใช้งาน")
        layout = QVBoxLayout()
        
        tips_text = QTextEdit()
        tips_text.setReadOnly(True)
        tips_text.setMaximumHeight(150)
        
        tips_content = """
            🔸 การใช้งานโปรแกรม SIM Management System:

            • ใส่คำสั่ง AT ในช่อง "AT Command" แล้วกด "Send AT"
            • ดูผลลัพธ์ทางด้านขวาในช่อง "Response"
            • ใช้คำสั่ง AT+RUN เพื่อเปิด SMS Monitor อัตโนมัติ
            • ใช้คำสั่ง AT+STOP เพื่อหยุด SMS Monitor
            • หากโมเด็มไม่ตอบสนอง ลองใช้ ATZ หรือ AT+CFUN=0 แล้ว AT+CFUN=1

            🔸 การแก้ปัญหาเบื้องต้น:

            • ถ้าไม่มีสัญญาณ: ตรวจสอบเสาอากาศและ SIM Card
            • ถ้า SMS ส่งไม่ได้: ตรวจสอบเครดิตและการตั้งค่า Service Center
            • ถ้าโมเด็มค้าง: ใช้คำสั่ง ATZ หรือ SIM Recovery
                    """
        
        tips_text.setText(tips_content.strip())
        layout.addWidget(tips_text)
        
        tips_group.setLayout(layout)
        return tips_group
    
    def create_footer(self, layout):
        """สร้างส่วนท้ายด้วยปุ่ม"""
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        # Close Button
        close_btn = QPushButton("✖️ Close")
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addLayout(footer_layout)
        
        self.close_btn = close_btn
    
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
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QTextEdit {
                border: 1px solid #dc3545;
                border-radius: 4px;
                background-color: white;
                color: #212529;
                font-family: 'Arial', sans-serif;
                font-size: 11px;
            }
            
            QFrame {
                border-radius: 4px;
                margin: 2px;
            }
        """)
        
        # Header specific styles
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #fff5f5;
                border: 2px solid #f5c6cb;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        
        self.title_label.setStyleSheet("""
            QLabel {
                color: #721c24;
                font-weight: bold;
            }
        """)
        
        self.desc_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-style: italic;
            }
        """)


# Integration code for sim_info_window.py
"""
เพิ่มโค้ดนี้ใน sim_info_window.py:

1. เพิ่ม import ที่ด้านบน:
from at_command_helper import ATCommandHelperDialog

2. เพิ่มในฟังก์ชัน setup_connections():
self.btn_help.clicked.connect(self.show_at_command_helper)

3. เพิ่มฟังก์ชันใหม่:
def show_at_command_helper(self):
    '''แสดงหน้าต่าง AT Command Helper'''
    try:
        helper_dialog = ATCommandHelperDialog(self)
        helper_dialog.exec_()
    except Exception as e:
        QMessageBox.warning(self, "Error", f"Cannot open AT Command Helper: {e}")
"""