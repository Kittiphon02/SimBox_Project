class SmsLogDialogStyles:
    """สไตล์สำหรับ SMS Log Dialog - โทนสีแดงทางการ"""
    
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
    def get_dialog_title_style():
        """Dialog Title Style - หัวข้อหน้าต่างโทนแดงเข้ม"""
        return """
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #8b1e1e;
                padding: 10px;
                text-align: center;
            }
        """

    # ==================== CONTROL SECTION STYLES ====================
    @staticmethod
    def get_control_section_style():
        """Control Section Style - ส่วนควบคุมโทนแดงอ่อน"""
        return """
            QWidget {
                background-color: #fff5f5;
                border: 2px solid #dc3545;
                border-radius: 8px;
                padding: 10px;
            }
        """
    
    @staticmethod
    def get_control_label_style():
        """Control Label Style - ป้ายควบคุมโทนแดงเข้ม"""
        return """
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #721c24;
            }
        """
    
    @staticmethod
    def get_combo_box_style():
        """ComboBox Style - กล่องเลือกโทนแดงทางการ"""
        return """
            QComboBox {
                font-size: 14px;
                padding: 6px 10px;
                border: 2px solid #dc3545;
                border-radius: 6px;
                background-color: white;
                color: #495057;
            }
            QComboBox:hover {
                border-color: #c82333;
                background-color: #fff5f5;
            }
            QComboBox:focus {
                border-color: #a71e2a;
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
            QComboBox QAbstractItemView {
                border: 2px solid #dc3545;
                background-color: white;
                selection-background-color: #f8d7da;
                selection-color: #721c24;
            }
        """

    # ==================== TABLE STYLES ====================
    @staticmethod
    def get_table_style():
        """Table Style - ตารางโทนแดงทางการ"""
        return """
            QTableWidget {
                gridline-color: #f5c6cb;
                background-color: white;
                alternate-background-color: #fff5f5;
                border: 2px solid #dc3545;
                border-radius: 8px;
                selection-background-color: #f8d7da;
                selection-color: #721c24;
                font-size: 15px;
                font-weight: 500;
            }
            QTableWidget::item {
                padding: 15px 10px;
                border-bottom: 1px solid #f5c6cb;
                border-right: 1px solid #f5c6cb;
            }
            QTableWidget::item:selected {
                background-color: #f8d7da;
                color: #721c24;
                font-weight: bold;
            }
            QTableWidget::item:hover {
                background-color: #f1b0b7;
                color: #721c24;
                font-weight: 600;
            }
        """
    
    @staticmethod
    def get_table_header_style():
        """Table Header Style - หัวตารางโทนแดงเข้ม"""
        return """
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                padding: 15px 10px;
                border: none;
                font-weight: bold;
                font-size: 16px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
        """

    # ==================== BUTTON STYLES ====================
    @staticmethod
    def get_primary_button_style():
        """Primary Button Style - ปุ่มหลักโทนแดง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
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
    def get_success_button_style():
        """Success Button Style - ปุ่มสำเร็จโทนเขียว"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #198754, stop:1 #157347);
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
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
    def get_info_button_style():
        """Info Button Style - ปุ่มข้อมูลโทนน้ำเงิน"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d6efd, stop:1 #0b5ed7);
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0b5ed7, stop:1 #0a58ca);
                border: 1px solid #0a58ca;
            }
            QPushButton:pressed {
                background: #0a58ca;
                padding-top: 9px;
            }
        """
    
    @staticmethod
    def get_danger_button_style():
        """Danger Button Style - ปุ่มอันตรายโทนแดงเข้ม"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #bb2d3b);
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
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

    # ==================== STATUS LABEL STYLES ====================
    @staticmethod
    def get_status_label_style():
        """Status Label Style - ป้ายสถานะโทนแดง"""
        return """
            QLabel {
                font-weight: bold;
                color: #721c24;
                font-size: 14px;
                padding: 8px 15px;
                background-color: #fff5f5;
                border-radius: 20px;
                border: 2px solid #dc3545;
            }
        """
    
    @staticmethod
    def get_info_label_style():
        """Info Label Style - ป้ายข้อมูลโทนแดงอ่อน"""
        return """
            QLabel {
                font-size: 12px;
                color: #6c757d;
                padding: 5px;
                background-color: #f8f9fa;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }
        """

    # ==================== FILTER SECTION STYLES ====================
    @staticmethod
    def get_filter_section_style():
        """Filter Section Style - ส่วนกรองข้อมูลโทนแดง"""
        return """
            QGroupBox {
                font-size: 16px;
                font-weight: 600;
                color: #721c24;
                border: 2px solid #dc3545;
                border-radius: 10px;
                margin-top: 10px;
                padding: 10px;
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
    def get_date_edit_style():
        """Date Edit Style - ช่องเลือกวันที่โทนแดง"""
        return """
            QDateEdit {
                font-size: 14px;
                padding: 6px 10px;
                border: 2px solid #dc3545;
                border-radius: 6px;
                background-color: white;
                color: #495057;
            }
            QDateEdit:hover {
                border-color: #c82333;
                background-color: #fff5f5;
            }
            QDateEdit:focus {
                border-color: #a71e2a;
                outline: none;
            }
            QDateEdit::drop-down {
                border: none;
                background-color: #dc3545;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                width: 20px;
            }
        """
    
    @staticmethod
    def get_checkbox_style():
        """Checkbox Style - ช่องเลือกโทนแดง"""
        return """
            QCheckBox {
                font-size: 14px;
                color: #721c24;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #dc3545;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #c82333;
                background-color: #fff5f5;
            }
            QCheckBox::indicator:checked {
                background-color: #dc3545;
                border-color: #a71e2a;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #c82333;
            }
        """

    # ==================== SEARCH SECTION STYLES ====================
    @staticmethod
    def get_search_input_style():
        """Search Input Style - ช่องค้นหาโทนแดง"""
        return """
            QLineEdit {
                font-size: 14px;
                padding: 8px 12px;
                border: 2px solid #dc3545;
                border-radius: 6px;
                background-color: white;
                color: #495057;
            }
            QLineEdit:hover {
                border-color: #c82333;
                background-color: #fff5f5;
            }
            QLineEdit:focus {
                border-color: #a71e2a;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #adb5bd;
            }
        """
    
    # สไตล์ช่องสำหรับ Search Phone Number&Message และปุ่ม Search
    @staticmethod
    def get_search_button_style():
        """Search Button Style – ปุ่มค้นหาโทนแดง"""
        return """
            QPushButton {
                font-size: 14px;
                padding: 6px 12px;
                border: 2px solid #dc3545;
                border-radius: 6px;
                background-color: white;
                color: #dc3545;
            }
            QPushButton:hover {
                background-color: #fff5f5;
                border-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #e53e3e;
                padding-top: 7px;
            }
        """


    @staticmethod
    def get_search_button_style():
        """Search Button Style - ปุ่มค้นหาโทนแดง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c757d, stop:1 #5a6268);
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6268, stop:1 #545b62);
            }
            QPushButton:pressed {
                background: #545b62;
            }
        """

    # ==================== FOOTER STYLES ====================
    @staticmethod
    def get_footer_style():
        """Footer Style - ส่วนท้ายโทนแดงอ่อน"""
        return """
            QWidget {
                background-color: #fff5f5;
                border-top: 2px solid #f5c6cb;
                padding: 10px;
            }
        """
    
    @staticmethod
    def get_pagination_style():
        """Pagination Style - ส่วนแบ่งหน้าโทนแดง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                color: #dc3545;
                border: 1px solid #dc3545;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                margin: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
            }
            QPushButton:pressed {
                background: #a71e2a;
                color: white;
            }
            QPushButton:disabled {
                background: #f8f9fa;
                color: #adb5bd;
                border-color: #dee2e6;
            }
        """

    # ==================== UTILITY METHODS ====================
    @staticmethod
    def darken_color(color, factor=0.2):
        """ทำให้สีเข้มขึ้น"""
        color_map = {
            "#dc3545": "#c82333",
            "#198754": "#157347", 
            "#0d6efd": "#0b5ed7",
            "#6f42c1": "#5a359a",
            "#f39c12": "#e67e22"
        }
        return color_map.get(color, color)
    
    @staticmethod
    def get_color_scheme():
        """ส่งคืนชุดสีหลักของ Dialog"""
        return {
            'primary': '#dc3545',
            'primary_dark': '#c82333',
            'primary_darker': '#a71e2a',
            'secondary': '#6c757d',
            'success': '#198754',
            'info': '#0d6efd',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'light': '#f8f9fa',
            'dark': '#212529',
            'background': '#fdf2f2',
            'surface': '#fff5f5',
            'border': '#f5c6cb',
            'text_primary': '#721c24',
            'text_secondary': '#6c757d'
        }