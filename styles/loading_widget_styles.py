class LoadingWidgetStyles:
    """สไตล์สำหรับ Loading Widget - โทนสีแดงทางการ"""
    
    # ==================== PROGRESS BAR STYLES ====================
    @staticmethod
    def get_progress_bar_style():
        """Progress Bar Style - แถบโหลดโทนแดงทางการ"""
        return """
            QProgressBar {
                border: 2px solid #dc3545;
                border-radius: 12px;
                background-color: #f8d7da;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                color: #721c24;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc3545, stop:0.5 #e95569, stop:1 #c82333);
                border-radius: 10px;
                margin: 1px;
            }
        """
    
    @staticmethod
    def get_progress_bar_success_style():
        """Progress Bar Success Style - แถบโหลดเมื่อสำเร็จ"""
        return """
            QProgressBar {
                border: 2px solid #198754;
                border-radius: 12px;
                background-color: #d1e7dd;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                color: #0a3622;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #198754, stop:0.5 #20c997, stop:1 #157347);
                border-radius: 10px;
                margin: 1px;
            }
        """
    
    @staticmethod
    def get_progress_bar_error_style():
        """Progress Bar Error Style - แถบโหลดเมื่อเกิดข้อผิดพลาด"""
        return """
            QProgressBar {
                border: 2px solid #dc3545;
                border-radius: 12px;
                background-color: #f8d7da;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                color: #721c24;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc3545, stop:0.5 #e74c3c, stop:1 #c0392b);
                border-radius: 10px;
                margin: 1px;
            }
        """

    # ==================== LABEL STYLES ====================
    @staticmethod
    def get_title_label_style():
        """Title Label Style - ป้ายชื่อหลักโทนแดง"""
        return """
            QLabel {
                color: #721c24;
                font-size: 15px;
                font-weight: bold;
                margin-left: 10px;
            }
        """
    
    @staticmethod
    def get_subtitle_label_style():
        """Subtitle Label Style - ป้ายชื่อรองโทนแดงอ่อน"""
        return """
            QLabel {
                color: #a2536a;
                font-size: 10px;
                margin-bottom: 10px;
            }
        """
    
    @staticmethod
    def get_percentage_label_style():
        """Percentage Label Style - ป้ายเปอร์เซ็นต์โทนแดงเข้ม"""
        return """
            QLabel {
                color: #8b1e1e;
                font-size: 12px;
                font-weight: bold;
                margin: 5px;
            }
        """
    
    @staticmethod
    def get_error_label_style():
        """Error Label Style - ป้ายข้อผิดพลาดโทนแดงสด"""
        return """
            QLabel {
                color: #dc3545;
                font-size: 12px;
                font-weight: bold;
            }
        """

    # ==================== STATUS FRAME STYLES ====================
    @staticmethod
    def get_status_frame_style():
        """Status Frame Style - กรอบสถานะโทนแดงอ่อน"""
        return """
            QFrame {
                background-color: #fff5f5;
                border: 1px solid #f5c6cb;
                border-radius: 8px;
                padding: 10px;
            }
        """
    
    @staticmethod
    def get_status_label_style():
        """Status Label Style - ป้ายสถานะโทนแดงกลาง"""
        return """
            QLabel {
                color: #721c24;
                font-size: 11px;
                font-weight: bold;
                margin-left: 8px;
            }
        """

    # ==================== ICON STYLES ====================
    @staticmethod
    def get_header_icon_style():
        """Header Icon Style - ไอคอนหัวข้อ"""
        return """
            QLabel {
                font-size: 24px;
            }
        """
    
    @staticmethod
    def get_status_icon_style():
        """Status Icon Style - ไอคอนสถานะ"""
        return """
            QLabel {
                font-size: 16px;
            }
        """

    # ==================== CONTAINER STYLES ====================
    @staticmethod
    def get_main_container_style():
        """Main Container Style - คอนเทนเนอร์หลักโทนแดงอ่อน"""
        return """
            QWidget {
                background-color: #fff5f5;
                border-radius: 10px;
                border: 1px solid #f5c6cb;
            }
        """
    
    @staticmethod
    def get_dialog_style():
        """Dialog Style - สไตล์หน้าต่าง Dialog โทนแดง"""
        return """
            QDialog {
                background-color: #fff5f5;
                border: 2px solid #dc3545;
                border-radius: 12px;
            }
        """

    # ==================== ANIMATION STATES ====================
    @staticmethod
    def get_loading_animation_style():
        """Loading Animation Style - สไตล์ขณะโหลด"""
        return """
            QLabel {
                color: #dc3545;
                font-weight: bold;
            }
        """
    
    @staticmethod
    def get_success_animation_style():
        """Success Animation Style - สไตล์เมื่อสำเร็จ"""
        return """
            QLabel {
                color: #198754;
                font-weight: bold;
            }
        """
    
    @staticmethod
    def get_error_animation_style():
        """Error Animation Style - สไตล์เมื่อเกิดข้อผิดพลาด"""
        return """
            QLabel {
                color: #dc3545;
                font-weight: bold;
            }
        """

    # ==================== UTILITY METHODS ====================
    @staticmethod
    def get_step_colors():
        """ส่งคืนสีสำหรับแต่ละขั้นตอน"""
        return {
            'default': '#6c757d',
            'active': '#dc3545',
            'success': '#198754',
            'error': '#dc3545',
            'warning': '#ffc107'
        }
    
    @staticmethod
    def get_icon_mapping():
        """ส่งคืนไอคอนสำหรับแต่ละสถานะ"""
        return {
            'default': '🔵',
            'loading': '🟡',
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }