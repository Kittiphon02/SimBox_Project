# main_window_styles.py - โค้ดเต็มที่แก้ไขแล้ว

from PyQt5.QtCore import QTimer, QPropertyAnimation, QRect, QEasingCurve, Qt
from PyQt5.QtWidgets import QGraphicsOpacityEffect

class MainWindowStyles:
    """สไตล์สำหรับหน้าต่างหลัก - โทนสีแดงทางการ"""
    
    # ==================== MAIN WINDOW & HEADER ====================
    @staticmethod
    def get_main_window_style():
        """Main Window Background Style"""
        return "QMainWindow {background-color: #fdf2f2;}"
    
    @staticmethod
    def get_header_style():
        """Header Style - หัวข้อหลักโทนสีแดงทางการ"""
        return """
            font-size: 28px;
            font-weight: 700;
            color: #8b1e1e;
            letter-spacing: 1px;
            padding-bottom: 12px;
            text-shadow: 1px 1px 2px rgba(139, 30, 30, 0.3);
        """

    # ==================== GROUP BOX STYLES ====================
    @staticmethod
    def get_modem_group_style():
        """Modem Group Style - กลุ่มการตั้งค่าโมเด็มโทนแดง"""
        return """
            QGroupBox {
                font-size: 17px;
                font-weight: 600;
                color: #722f37;
                border: 2px solid #dc3545;
                border-radius: 12px;
                margin-top: 12px;
                padding: 16px;
                background-color: #fff5f5;
                box-shadow: 0 2px 4px rgba(220, 53, 69, 0.1);
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 16px;
                color: #a91e2c;
                font-weight: bold;
            }
        """
    
    @staticmethod
    def get_at_group_style():
        """AT Command Group Style - กลุ่มควบคุมคำสั่ง AT โทนแดง"""
        return """
            QGroupBox {
                font-size: 17px;
                font-weight: 600;
                color: #722f37;
                border: 2px solid #b91d47;
                border-radius: 12px;
                margin-top: 12px;
                padding: 16px;
                background-color: #fff5f5;
                box-shadow: 0 2px 4px rgba(185, 29, 71, 0.1);
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 16px;
                color: #a91e2c;
                font-weight: bold;
            }
        """

    # ==================== INPUT FIELD STYLES ====================
    @staticmethod
    def get_at_combo_style():
        """AT ComboBox Style - โทนแดงทางการ"""
        return """
            QComboBox {
                font-size: 14px;
                border-radius: 6px;
                border: 2px solid #dc3545;
                padding: 6px 10px;
                background-color: #fff;
                color: #495057;
            }
            QComboBox:hover {
                border: 2px solid #c82333;
                background-color: #fff5f5;
            }
            QComboBox:focus {
                border: 2px solid #a71e2a;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #dc3545;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: 2px solid white;
                border-top: none;
                border-left: none;
                width: 6px;
                height: 6px;
                margin: 4px;
            }
        """
    
    @staticmethod
    def get_input_cmd_style():
        """Input Command Style - โทนแดงสำหรับช่องคำสั่ง"""
        return """
            QTextEdit {
                font-size: 16px;
                border-radius: 6px;
                border: 2px solid #dc3545;
                padding: 8px;
                background-color: #fff;
                color: #212529;
            }
            QTextEdit:focus {
                border: 2px solid #a71e2a;
                background-color: #fff5f5;
                outline: none;
            }
        """
    
    @staticmethod
    def get_sms_input_style():
        """SMS Input Style - โทนแดงสำหรับช่องข้อความ"""
        return """
            QTextEdit {
                font-size: 14px;
                border-radius: 6px;
                border: 2px solid #dc3545;
                padding: 8px;
                background-color: #fff;
                color: #212529;
            }
            QTextEdit:focus {
                border: 2px solid #a71e2a;
                background-color: #fff5f5;
                outline: none;
            }
            QTextEdit:hover {
                border: 2px solid #c82333;
            }
        """
    
    @staticmethod
    def get_phone_input_style():
        """Phone Input Style - โทนแดงสำหรับช่องเบอร์โทร"""
        return """
            QLineEdit {
                font-size: 14px;
                padding: 8px 12px;
                border-radius: 6px;
                border: 2px solid #dc3545;
                background-color: #fff;
                color: #212529;
            }
            QLineEdit:focus {
                border: 2px solid #a71e2a;
                background-color: #fff5f5;
                outline: none;
            }
            QLineEdit:hover {
                border: 2px solid #c82333;
            }
        """

    # ==================== DISPLAY AREA STYLES ====================
    @staticmethod
    def get_command_display_style():
        """Command Display Style - แสดงคำสั่งที่ส่ง"""
        return """
            QTextEdit {
                font-size: 14px;
                font-family: 'Courier New', monospace;
                border-radius: 6px;
                border: 2px solid #dc3545;
                padding: 8px;
                background-color: #fff;
                color: #6c757d;
            }
            QTextEdit:focus {
                border: 2px solid #a71e2a;
                outline: none;
            }
        """
    
    @staticmethod
    def get_result_display_style():
        """Result Display Style - แสดงผลลัพธ์คำสั่ง"""
        return """
            QTextEdit {
                font-size: 14px;
                font-family: 'Courier New', monospace;
                border-radius: 6px;
                border: 2px solid #dc3545;
                padding: 8px;
                background-color: #fff;
                color: #d63384;
            }
            QTextEdit:focus {
                border: 2px solid #a71e2a;
                outline: none;
            }
        """

    # ==================== BUTTON STYLES ====================
    @staticmethod
    def get_send_at_button_style():
        """Send AT Button Style - ปุ่มส่งคำสั่ง AT โทนแดงหลัก"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                font-weight: 600;
                border-radius: 7px;
                padding: 8px 0;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
                border: 1px solid #a71e2a;
            }
            QPushButton:pressed {
                background: #a71e2a;
                padding-top: 9px;
            }
        """
    
    @staticmethod
    def get_send_sms_button_style():
        """Send SMS Button Style - ปุ่มส่ง SMS โทนแดง-เขียว"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #198754, stop:1 #157347);
                color: white;
                font-weight: 600;
                border-radius: 7px;
                padding: 8px 0;
                font-size: 14px;
                border: 1px solid #146c43;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #157347, stop:1 #146c43);
                border: 1px solid #146c43;
            }
            QPushButton:pressed {
                background: #146c43;
                padding-top: 9px;
            }
        """
    
    @staticmethod
    def get_show_sms_button_style():
        """Show SMS Button Style - ปุ่มแสดง SMS โทนม่วง-แดง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6f42c1, stop:1 #5a359a);
                color: white;
                font-weight: 600;
                border-radius: 7px;
                padding: 8px 0;
                font-size: 14px;
                border: 1px solid #59359a;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a359a, stop:1 #4c2d83);
                border: 1px solid #5a359a;
            }
            QPushButton:pressed {
                background: #4c2d83;
                padding-top: 9px;
            }
        """

    # ==================== CONTROL BUTTON STYLES ====================
    @staticmethod
    def get_refresh_button_style():
        """Refresh Button Style - ปุ่มรีเฟรชโทนแดงเข้ม"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: white;
                font-weight: 600;
                border-radius: 7px;
                padding: 10px 0;
                border: 1px solid #a93226;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c0392b, stop:1 #a93226);
                box-shadow: 0 2px 4px rgba(231, 76, 60, 0.3);
            }
            QPushButton:pressed {
                background: #a93226;
            }
        """
    
    @staticmethod
    def get_smslog_button_style():
        """SMS Log Button Style - ปุ่ม SMS Log โทนน้ำเงิน-แดง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d6efd, stop:1 #0b5ed7);
                color: white;
                font-weight: 600;
                border-radius: 7px;
                padding: 10px 0;
                border: 1px solid #0a58ca;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0b5ed7, stop:1 #0a58ca);
                border: 1px solid #0a58ca;
            }
            QPushButton:pressed {
                background: #0a58ca;
            }
        """

    @staticmethod
    def get_realtime_monitor_style():
        """SMS Monitor Button Style - ปุ่ม Monitor โทนเขียวเข้ม"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #198754, stop:1 #157347);
                color: white;
                font-weight: 600;
                border-radius: 7px;
                padding: 10px 0;
                border: 1px solid #146c43;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #157347, stop:1 #146c43);
                border: 1px solid #146c43;
            }
            QPushButton:pressed {
                background: #146c43;
            }
        """

    # ==================== DELETE & CLEAR BUTTON STYLES ====================
    @staticmethod
    def get_delete_button_style():
        """Delete Button Style - ปุ่มลบโทนแดงสด"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #bb2d3b);
                color: white;
                font-weight: 600;
                border-radius: 5px;
                padding: 8px 0;
                font-size: 13px;
                border: 1px solid #b02a37;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #bb2d3b, stop:1 #b02a37);
                box-shadow: 0 2px 4px rgba(220, 53, 69, 0.4);
            }
            QPushButton:pressed {
                background: #b02a37;
                padding-top: 9px;
            }
        """
    
    @staticmethod
    def get_help_button_style():
        """Help Button Style - ปุ่มช่วยเหลือโทนเทา"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #808080, stop:1 #808080);
                color: white;
                font-weight: 600;
                border-radius: 5px;
                padding: 8px 0;
                font-size: 13px;
                border: 1px solid #808080;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #999999, stop:1 #999999);
                box-shadow: 0 2px 4px rgba(220, 53, 69, 0.4);
            }
            QPushButton:pressed {
                background: #808080;
                padding-top: 9px;
            }
        """
    
    @staticmethod
    def get_clear_sms_button_style():
        """Clear SMS Button Style - ปุ่มล้าง SMS โทนแดงเข้ม"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #bb2d3b);
                color: white;
                font-weight: 600;
                border-radius: 7px;
                padding: 8px 0;
                font-size: 14px;
                border: 1px solid #b02a37;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #bb2d3b, stop:1 #b02a37);
                box-shadow: 0 2px 4px rgba(220, 53, 69, 0.4);
            }
            QPushButton:pressed {
                background: #b02a37;
                padding-top: 9px;
            }
        """
    
    @staticmethod
    def get_clear_response_button_style():
        """Clear Response Button Style - ปุ่มล้างผลลัพธ์"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #bb2d3b);
                color: white;
                border-radius: 4px;
                padding: 6px;
                border: 1px solid #b02a37;
                font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #bb2d3b, stop:1 #b02a37);
            }
            QPushButton:pressed {
                background: #b02a37;
            }
        """

    # ==================== TABLE & DATA DISPLAY STYLES ====================
    @staticmethod
    def get_table_style():
        """Table Style - รองรับ Unicode Signal Bars"""
        return """
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                border: 1px solid #b02a37;
                color: white;
            }
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
            QTableWidget {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 15px;
                border-radius: 10px;
                background: #fff5f5;
                gridline-color: #f5c6cb;
                selection-background-color: #f8d7da;
                selection-color: #721c24;
                alternate-background-color: #fff;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f5c6cb;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QTableWidget::item:selected {
                background-color: #f8d7da;
                color: #721c24;
                font-weight: bold;
            }
            QTableWidget::item:hover {
                background-color: #f1b0b7;
                color: #721c24;
            }
        """
    
    # ==================== TOGGLE BUTTON STYLES ====================
    @staticmethod
    def get_toggle_button_style():
        """Toggle Button Style - ปุ่มสลับโทนแดง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c757d, stop:1 #5a6268);
                color: white;
                font-weight: 500;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                border: 1px solid #545b62;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6268, stop:1 #545b62);
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
            }
        """

    @staticmethod
    def get_message_box_style():
        """Message Box Style - กล่องข้อความข้างปุ่ม Sync (ใช้โทนสีแดงให้เข้ากับธีม)"""
        return """
            QLineEdit {
                font-size: 14px;
                padding: 8px 12px;
                border-radius: 6px;
                border: 2px solid #dc3545;
                background-color: #fff;
                color: #212529;
                font-family: Arial, sans-serif;
            }
            QLineEdit:focus {
                border: 2px solid #a71e2a;
                background-color: #fff5f5;
                outline: none;
            }
            QLineEdit:hover {
                border: 2px solid #c82333;
                background-color: #f8fbff;
            }
            QLineEdit::placeholder {
                color: #95a5a6;
                font-style: italic;
            }
            QLineEdit:disabled {
                background-color: #ecf0f1;
                color: #7f8c8d;
                border: 2px solid #bdc3c7;
            }
        """
    
    # เพิ่มลงในไฟล์ main_window_styles.py

    @staticmethod
    def get_sms_inbox_counter_style():
        """SMS Inbox Counter Style - แสดงจำนวน SMS ใน inbox"""
        return """
            QLabel {
                font-size: 14px;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 6px;
                border: 2px solid #dc3545;
                background-color: #fff5f5;
                color: #721c24;
                text-align: center;
            }
            QLabel:hover {
                background-color: #f8d7da;
                border: 2px solid #c82333;
            }
        """

    @staticmethod
    def get_sms_inbox_counter_zero_style():
        """SMS Inbox Counter Style - เมื่อไม่มี SMS"""
        return """
            QLabel {
                font-size: 14px;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 6px;
                border: 2px solid #6c757d;
                background-color: #f8f9fa;
                color: #495057;
                text-align: center;
            }
        """

    @staticmethod
    def get_sms_inbox_counter_high_style():
        """SMS Inbox Counter Style - เมื่อมี SMS เยอะ (>10)"""
        return """
            QLabel {
                font-size: 14px;
                font-weight: 700;
                padding: 8px 12px;
                border-radius: 6px;
                border: 2px solid #dc3545;
                background-color: #f8d7da;
                color: #721c24;
                text-align: center;
            }
            QLabel:hover {
                background-color: #f5c6cb;
                border: 2px solid #c82333;
            }
        """
    
    @staticmethod
    def get_sms_inbox_badge_style():
        """SMS Inbox Badge Style - แบบปุ่มฟ้า"""
        return """
            QLabel {
                background-color: #3498db;
                color: white;
                border: 2px solid #2980b9;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 8px;
            }
            QLabel:hover {
                background-color: #2980b9;
            }
        """

    @staticmethod
    def get_sms_count_badge_style():
        """SMS Count Badge Style - แบดจ์แดงกลม"""
        return """
            QLabel {
                background-color: #e74c3c;
                color: white;
                border: 2px solid white;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
        """

    @staticmethod
    def get_sms_count_badge_high_style():
        """SMS Count Badge Style - เมื่อมีจำนวนเยอะ"""
        return """
            QLabel {
                background-color: #c0392b;
                color: white;
                border: 2px solid white;
                border-radius: 14px;
                font-size: 11px;
                font-weight: bold;
                text-align: center;
            }
        """

    @staticmethod
    def get_sms_inbox_badge_inactive_style():
        """SMS Inbox Badge Style - เมื่อไม่มี SMS"""
        return """
            QLabel {
                background-color: #95a5a6;
                color: white;
                border: 2px solid #7f8c8d;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 8px;
            }
        """

