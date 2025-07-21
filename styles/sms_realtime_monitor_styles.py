class SmsRealtimeMonitorStyles:
    """สไตล์สำหรับ SMS Real-time Monitor - โทนสีแดงทางการ"""
    
    # ==================== MAIN DIALOG STYLES ====================
    @staticmethod
    def get_dialog_style():
        """Dialog Main Style - หน้าต่างหลักโทนแดง"""
        return """
            QDialog {
                background-color: #fdf2f2;
                border: 2px solid #dc3545;
                border-radius: 10px;
            }
        """
    
    @staticmethod
    def get_header_style():
        """Header Style - หัวข้อหลักโทนแดงเข้ม"""
        return """
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #721c24;
                padding: 10px;
                background-color: #fff5f5;
                border-radius: 5px;
                margin-bottom: 10px;
                border: 1px solid #f5c6cb;
            }
        """
    
    @staticmethod
    def get_connection_info_style():
        """Connection Info Style - ข้อมูลการเชื่อมต่อ"""
        return """
            QLabel {
                font-size: 12px;
                color: #6c757d;
                padding: 5px;
                background-color: #f8f9fa;
                border-radius: 3px;
            }
        """

    # ==================== GROUP BOX STYLES ====================
    @staticmethod
    def get_control_group_style():
        """Control Group Style - กลุ่มควบคุมโทนแดง"""
        return """
            QGroupBox {
                font-size: 16px;
                font-weight: 600;
                color: #721c24;
                border: 2px solid #dc3545;
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
                background-color: #fff5f5;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #a91e2c;
                font-weight: bold;
            }
        """
    
    @staticmethod
    def get_monitor_group_style():
        """Monitor Group Style - กลุ่มแสดงผลโทนแดง"""
        return """
            QGroupBox {
                font-size: 16px;
                font-weight: 600;
                color: #721c24;
                border: 2px solid #b91d47;
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
                background-color: #fff5f5;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #a91e2c;
                font-weight: bold;
            }
        """

    # ==================== BUTTON STYLES ====================
    @staticmethod
    def get_start_button_style():
        """Start Button Style - ปุ่มเริ่มโทนเขียว"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #198754, stop:1 #157347);
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #146c43;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #157347, stop:1 #146c43);
                box-shadow: 0 2px 4px rgba(25, 135, 84, 0.3);
            }
            QPushButton:pressed {
                background: #146c43;
                padding-top: 9px;
            }
            QPushButton:disabled {
                background: #6c757d;
                color: #adb5bd;
                border-color: #545b62;
            }
        """
    
    @staticmethod
    def get_stop_button_style():
        """Stop Button Style - ปุ่มหยุดโทนแดง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #b02a37;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
                box-shadow: 0 2px 4px rgba(220, 53, 69, 0.3);
            }
            QPushButton:pressed {
                background: #a71e2a;
                padding-top: 9px;
            }
            QPushButton:disabled {
                background: #6c757d;
                color: #adb5bd;
                border-color: #545b62;
            }
        """
    
    @staticmethod
    def get_clear_button_style():
        """Clear Button Style - ปุ่มล้างโทนส้ม"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fd7e14, stop:1 #e8590c);
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #d63384;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8590c, stop:1 #dc5200);
                box-shadow: 0 2px 4px rgba(253, 126, 20, 0.3);
            }
            QPushButton:pressed {
                background: #dc5200;
                padding-top: 9px;
            }
        """

    # ==================== STATUS LABEL STYLES ====================
    @staticmethod
    def get_status_ready_style():
        """Status Ready Style - สถานะพร้อมโทนน้ำเงิน"""
        return """
            QLabel {
                color: #0d6efd;
                font-weight: bold;
                padding: 5px;
                background-color: #cfe2ff;
                border-radius: 5px;
                border: 1px solid #9ec5fe;
            }
        """
    
    @staticmethod
    def get_status_active_style():
        """Status Active Style - สถานะทำงานโทนเขียว"""
        return """
            QLabel {
                color: #198754;
                font-weight: bold;
                padding: 5px;
                background-color: #d1e7dd;
                border-radius: 5px;
                border: 1px solid #a3cfbb;
            }
        """
    
    @staticmethod
    def get_status_stopped_style():
        """Status Stopped Style - สถานะหยุดโทนแดง"""
        return """
            QLabel {
                color: #dc3545;
                font-weight: bold;
                padding: 5px;
                background-color: #f8d7da;
                border-radius: 5px;
                border: 1px solid #f1aeb5;
            }
        """
    
    @staticmethod
    def get_status_error_style():
        """Status Error Style - สถานะผิดพลาดโทนแดงเข้ม"""
        return """
            QLabel {
                color: #721c24;
                font-weight: bold;
                padding: 5px;
                background-color: #f8d7da;
                border-radius: 5px;
                border: 2px solid #dc3545;
            }
        """

    # ==================== MONITOR DISPLAY STYLES ====================
    @staticmethod
    def get_monitor_display_style():
        """Monitor Display Style - หน้าจอแสดงผลโทนแดง"""
        return """
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                border-radius: 5px;
                border: 2px solid #dc3545;
                padding: 8px;
                background-color: #fff;
                color: #212529;
                selection-background-color: #f8d7da;
                selection-color: #721c24;
            }
            QTextEdit:focus {
                border-color: #a71e2a;
                outline: none;
            }
        """
    
    @staticmethod
    def get_monitor_placeholder_style():
        """Monitor Placeholder Style - ข้อความตัวอย่าง"""
        return """
            QTextEdit {
                color: #6c757d;
                font-style: italic;
            }
        """

    # ==================== STATS SECTION STYLES ====================
    @staticmethod
    def get_stats_received_style():
        """Stats Received Style - สถิติข้อความรับ"""
        return """
            QLabel {
                background-color: #0d6efd;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #0b5ed7;
            }
        """
    
    @staticmethod
    def get_stats_saved_style():
        """Stats Saved Style - สถิติบันทึกแล้ว"""
        return """
            QLabel {
                background-color: #198754;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #157347;
            }
        """
    
    @staticmethod
    def get_stats_errors_style():
        """Stats Errors Style - สถิติข้อผิดพลาด"""
        return """
            QLabel {
                background-color: #dc3545;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #c82333;
            }
        """

    # ==================== LOG MESSAGE STYLES ====================
    @staticmethod
    def get_log_timestamp_style():
        """Log Timestamp Style - สไตล์เวลาในล็อก"""
        return """
            color: #6c757d;
            font-weight: normal;
            font-size: 11px;
        """
    
    @staticmethod
    def get_log_system_style():
        """Log System Style - ข้อความระบบในล็อก"""
        return """
            color: #0d6efd;
            font-weight: bold;
        """
    
    @staticmethod
    def get_log_sms_style():
        """Log SMS Style - ข้อความ SMS ในล็อก"""
        return """
            color: #198754;
            font-weight: bold;
        """
    
    @staticmethod
    def get_log_error_style():
        """Log Error Style - ข้อผิดพลาดในล็อก"""
        return """
            color: #dc3545;
            font-weight: bold;
        """
    
    @staticmethod
    def get_log_warning_style():
        """Log Warning Style - คำเตือนในล็อก"""
        return """
            color: #fd7e14;
            font-weight: bold;
        """

    # ==================== CONNECTION STATUS STYLES ====================
    @staticmethod
    def get_connection_connected_style():
        """Connection Connected Style - สถานะเชื่อมต่อแล้ว"""
        return """
            QLabel {
                color: #198754;
                font-weight: bold;
                background-color: #d1e7dd;
                padding: 5px 10px;
                border-radius: 15px;
                border: 1px solid #a3cfbb;
            }
        """
    
    @staticmethod
    def get_connection_disconnected_style():
        """Connection Disconnected Style - สถานะไม่ได้เชื่อมต่อ"""
        return """
            QLabel {
                color: #dc3545;
                font-weight: bold;
                background-color: #f8d7da;
                padding: 5px 10px;
                border-radius: 15px;
                border: 1px solid #f1aeb5;
            }
        """
    
    @staticmethod
    def get_connection_connecting_style():
        """Connection Connecting Style - สถานะกำลังเชื่อมต่อ"""
        return """
            QLabel {
                color: #fd7e14;
                font-weight: bold;
                background-color: #fff3cd;
                padding: 5px 10px;
                border-radius: 15px;
                border: 1px solid #ffecb5;
            }
        """

    # ==================== TOOLBAR STYLES ====================
    @staticmethod
    def get_toolbar_style():
        """Toolbar Style - แถบเครื่องมือโทนแดง"""
        return """
            QWidget {
                background-color: #fff5f5;
                border: 1px solid #f5c6cb;
                border-radius: 5px;
                padding: 5px;
            }
        """
    
    @staticmethod
    def get_toolbar_separator_style():
        """Toolbar Separator Style - เส้นแบ่งในแถบเครื่องมือ"""
        return """
            QFrame {
                background-color: #dc3545;
                width: 2px;
                margin: 5px;
            }
        """

    # ==================== PROGRESS INDICATOR STYLES ====================
    @staticmethod
    def get_progress_indicator_style():
        """Progress Indicator Style - ตัวบ่งชี้ความคืบหน้า"""
        return """
            QProgressBar {
                border: 2px solid #dc3545;
                border-radius: 8px;
                background-color: #f8d7da;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
                color: #721c24;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc3545, stop:0.5 #e95569, stop:1 #c82333);
                border-radius: 6px;
                margin: 1px;
            }
        """

    # ==================== NOTIFICATION STYLES ====================
    @staticmethod
    def get_notification_info_style():
        """Notification Info Style - แจ้งเตือนข้อมูล"""
        return """
            QLabel {
                background-color: #cfe2ff;
                color: #084298;
                border: 1px solid #9ec5fe;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: 500;
            }
        """
    
    @staticmethod
    def get_notification_success_style():
        """Notification Success Style - แจ้งเตือนสำเร็จ"""
        return """
            QLabel {
                background-color: #d1e7dd;
                color: #0a3622;
                border: 1px solid #a3cfbb;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: 500;
            }
        """
    
    @staticmethod
    def get_notification_warning_style():
        """Notification Warning Style - แจ้งเตือนคำเตือน"""
        return """
            QLabel {
                background-color: #fff3cd;
                color: #664d03;
                border: 1px solid #ffecb5;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: 500;
            }
        """
    
    @staticmethod
    def get_notification_error_style():
        """Notification Error Style - แจ้งเตือนข้อผิดพลาด"""
        return """
            QLabel {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f1aeb5;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: 500;
            }
        """

    # ==================== SCROLLBAR STYLES ====================
    @staticmethod
    def get_scrollbar_style():
        """Scrollbar Style - แถบเลื่อนโทนแดง"""
        return """
            QScrollBar:vertical {
                background-color: #fff5f5;
                width: 12px;
                border-radius: 6px;
                border: 1px solid #f5c6cb;
            }
            QScrollBar::handle:vertical {
                background-color: #dc3545;
                border-radius: 5px;
                min-height: 20px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #c82333;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #a71e2a;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """

    # ==================== ANIMATION CLASSES ====================
    @staticmethod
    def get_fade_in_animation():
        """Fade In Animation - แอนิเมชันค่อยๆ ปรากฏ"""
        return """
            QWidget {
                animation-duration: 300ms;
                animation-timing-function: ease-in-out;
            }
        """
    
    @staticmethod
    def get_pulse_animation():
        """Pulse Animation - แอนิเมชันเต้น"""
        return """
            QLabel {
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
        """

    # ==================== UTILITY METHODS ====================
    @staticmethod
    def get_status_colors():
        """ส่งคืนสีสำหรับสถานะต่างๆ"""
        return {
            'ready': '#0d6efd',
            'active': '#198754',
            'stopped': '#dc3545',
            'error': '#721c24',
            'warning': '#fd7e14',
            'info': '#17a2b8'
        }
    
    @staticmethod
    def get_message_type_colors():
        """ส่งคืนสีสำหรับประเภทข้อความต่างๆ"""
        return {
            'system': '#0d6efd',
            'sms': '#198754',
            'error': '#dc3545',
            'warning': '#fd7e14',
            'info': '#17a2b8',
            'debug': '#6c757d'
        }
    
    @staticmethod
    def get_priority_styles():
        """ส่งคืนสไตล์สำหรับลำดับความสำคัญ"""
        return {
            'high': """
                border: 2px solid #dc3545;
                background-color: #f8d7da;
                font-weight: bold;
            """,
            'medium': """
                border: 2px solid #fd7e14;
                background-color: #fff3cd;
                font-weight: 500;
            """,
            'low': """
                border: 2px solid #6c757d;
                background-color: #f8f9fa;
                font-weight: normal;
            """
        }
    
    @staticmethod
    def get_theme_variants():
        """ส่งคืนตัวแปรธีมสี"""
        return {
            'light': {
                'background': '#fdf2f2',
                'surface': '#fff5f5',
                'primary': '#dc3545',
                'text': '#721c24'
            },
            'dark': {
                'background': '#2c1810',
                'surface': '#3d251a',
                'primary': '#ff6b6b',
                'text': '#ffcccb'
            }
        }