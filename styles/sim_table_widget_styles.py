class SimTableWidgetStyles:
    """สไตล์สำหรับ SIM Table Widget - โทนสีแดงทางการ"""
    
    # ==================== MAIN TABLE STYLES ====================
    @staticmethod
    def get_table_style():
        """Table Style รองรับ Unicode bars"""
        return """
            QTableWidget {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                border-radius: 8px;
                background: #fff5f5;
                gridline-color: #f5c6cb;
                selection-background-color: #f8d7da;
                selection-color: #721c24;
                alternate-background-color: #fff;
                border: 2px solid #dc3545;
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
    
    @staticmethod
    def get_table_header_style():
        """Table Header Style - หัวตารางโทนแดงเข้ม"""
        return """
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                border: 1px solid #b02a37;
                color: white;
                text-align: center;
            }
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
            QHeaderView::section:pressed {
                background: #a71e2a;
            }
        """

    # ==================== SIGNAL STRENGTH STYLES ====================
    @staticmethod
    def get_signal_container_style():
        """Signal Container Style - คอนเทนเนอร์สัญญาณ"""
        return """
            QWidget {
                background-color: transparent;
                border: none;
                padding: 2px;
            }
        """
    
    @staticmethod
    def get_signal_bars_excellent_style():
        """Signal Bars Excellent Style - แถบสัญญาณดีเยี่ยม"""
        return """
            QLabel {
                color: #198754;
                font-weight: bold;
                font-size: 12px;
                background-color: #d1e7dd;
                border-radius: 3px;
                padding: 2px 4px;
            }
        """
    
    @staticmethod
    def get_signal_bars_good_style():
        """Signal Bars Good Style - แถบสัญญาณดี"""
        return """
            QLabel {
                color: #20c997;
                font-weight: bold;
                font-size: 12px;
                background-color: #c3f7df;
                border-radius: 3px;
                padding: 2px 4px;
            }
        """
    
    @staticmethod
    def get_signal_bars_fair_style():
        """Signal Bars Fair Style - แถบสัญญาณพอใช้"""
        return """
            QLabel {
                color: #fd7e14;
                font-weight: bold;
                font-size: 12px;
                background-color: #fff3cd;
                border-radius: 3px;
                padding: 2px 4px;
            }
        """
    
    @staticmethod
    def get_signal_bars_poor_style():
        """Signal Bars Poor Style - แถบสัญญาณอ่อน"""
        return """
            QLabel {
                color: #dc3545;
                font-weight: bold;
                font-size: 12px;
                background-color: #f8d7da;
                border-radius: 3px;
                padding: 2px 4px;
            }
        """
    
    @staticmethod
    def get_signal_bars_no_signal_style():
        """Signal Bars No Signal Style - ไม่มีสัญญาณ"""
        return """
            QLabel {
                color: #6c757d;
                font-weight: bold;
                font-size: 12px;
                background-color: #f8f9fa;
                border-radius: 3px;
                padding: 2px 4px;
            }
        """
    
    @staticmethod
    def get_signal_text_style():
        """Signal Text Style - ข้อความสัญญาณ"""
        return """
            QLabel {
                font-size: 11px;
                font-weight: 500;
                margin-left: 5px;
            }
        """

    # ==================== CELL DATA STYLES ====================
    @staticmethod
    def get_phone_cell_style():
        """Phone Cell Style - เซลล์เบอร์โทร"""
        return """
            QTableWidgetItem {
                font-weight: bold;
                color: #721c24;
                text-align: center;
            }
        """
    
    @staticmethod
    def get_imsi_cell_style():
        """IMSI Cell Style - เซลล์ IMSI"""
        return """
            QTableWidgetItem {
                font-family: 'Courier New', monospace;
                color: #495057;
                text-align: center;
                font-size: 13px;
            }
        """
    
    @staticmethod
    def get_iccid_cell_style():
        """ICCID Cell Style - เซลล์ ICCID"""
        return """
            QTableWidgetItem {
                font-family: 'Courier New', monospace;
                color: #495057;
                text-align: center;
                font-size: 13px;
            }
        """
    
    @staticmethod
    def get_carrier_cell_style():
        """Carrier Cell Style - เซลล์ผู้ให้บริการ"""
        return """
            QTableWidgetItem {
                font-weight: 600;
                text-align: center;
            }
        """

    # ==================== CARRIER SPECIFIC STYLES ====================
    @staticmethod
    def get_ais_carrier_style():
        """AIS Carrier Style - สไตล์ AIS"""
        return """
            QTableWidgetItem {
                color: #28a745;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
            }
        """
    
    @staticmethod
    def get_dtac_carrier_style():
        """DTAC Carrier Style - สไตล์ DTAC"""
        return """
            QTableWidgetItem {
                color: #007bff;
                background-color: #cce5ff;
                border: 1px solid #99d0ff;
            }
        """
    
    @staticmethod
    def get_true_carrier_style():
        """TRUE Carrier Style - สไตล์ TRUE"""
        return """
            QTableWidgetItem {
                color: #dc3545;
                background-color: #f8d7da;
                border: 1px solid #f1aeb5;
            }
        """
    
    @staticmethod
    def get_unknown_carrier_style():
        """Unknown Carrier Style - สไตล์ผู้ให้บริการไม่ทราบ"""
        return """
            QTableWidgetItem {
                color: #6c757d;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
            }
        """

    # ==================== ROW STATE STYLES ====================
    @staticmethod
    def get_row_normal_style():
        """Row Normal Style - แถวปกติ"""
        return """
            QTableWidget::item {
                background-color: #fff;
                border-bottom: 1px solid #f5c6cb;
            }
        """
    
    @staticmethod
    def get_row_alternate_style():
        """Row Alternate Style - แถวสลับสี"""
        return """
            QTableWidget::item {
                background-color: #fff5f5;
                border-bottom: 1px solid #f5c6cb;
            }
        """
    
    @staticmethod
    def get_row_selected_style():
        """Row Selected Style - แถวที่เลือก"""
        return """
            QTableWidget::item:selected {
                background-color: #f8d7da;
                color: #721c24;
                font-weight: bold;
                border: 2px solid #dc3545;
            }
        """
    
    @staticmethod
    def get_row_hover_style():
        """Row Hover Style - แถวเมื่อ hover"""
        return """
            QTableWidget::item:hover {
                background-color: #f1b0b7;
                color: #721c24;
                font-weight: 500;
                border-bottom: 2px solid #dc3545;
            }
        """

    # ==================== BUTTON STYLES ====================
    @staticmethod
    def get_action_button_style():
        """Action Button Style - ปุ่มดำเนินการในตาราง"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                margin: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
                box-shadow: 0 2px 4px rgba(220, 53, 69, 0.3);
            }
            QPushButton:pressed {
                background: #a71e2a;
            }
            QPushButton:disabled {
                background: #6c757d;
                color: #adb5bd;
            }
        """
    
    @staticmethod
    def get_history_button_style():
        """History Button Style - ปุ่มประวัติ"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d6efd, stop:1 #0b5ed7);
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                margin: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0b5ed7, stop:1 #0a58ca);
                box-shadow: 0 2px 4px rgba(13, 110, 253, 0.3);
            }
            QPushButton:pressed {
                background: #0a58ca;
            }
        """
    
    @staticmethod
    def get_send_button_style():
        """Send Button Style - ปุ่มส่ง SMS"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #198754, stop:1 #157347);
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                margin: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #157347, stop:1 #146c43);
                box-shadow: 0 2px 4px rgba(25, 135, 84, 0.3);
            }
            QPushButton:pressed {
                background: #146c43;
            }
        """

    # ==================== CONTEXT MENU STYLES ====================
    @staticmethod
    def get_context_menu_style():
        """Context Menu Style - เมนูคลิกขวา"""
        return """
            QMenu {
                background-color: #fff;
                border: 2px solid #dc3545;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 15px;
                color: #212529;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #f8d7da;
                color: #721c24;
                font-weight: bold;
            }
            QMenu::item:pressed {
                background-color: #f5c6cb;
            }
            QMenu::separator {
                height: 1px;
                background-color: #f5c6cb;
                margin: 5px 10px;
            }
        """

    # ==================== TOOLTIP STYLES ====================
    @staticmethod
    def get_tooltip_style():
        """Tooltip Style - คำแนะนำเครื่องมือ"""
        return """
            QToolTip {
                background-color: #212529;
                color: white;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
                opacity: 220;
            }
        """

    # ==================== SCROLLBAR STYLES ====================
    @staticmethod
    def get_vertical_scrollbar_style():
        """Vertical Scrollbar Style - แถบเลื่อนแนวตั้ง"""
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
    
    @staticmethod
    def get_horizontal_scrollbar_style():
        """Horizontal Scrollbar Style - แถบเลื่อนแนวนอน"""
        return """
            QScrollBar:horizontal {
                background-color: #fff5f5;
                height: 12px;
                border-radius: 6px;
                border: 1px solid #f5c6cb;
            }
            QScrollBar::handle:horizontal {
                background-color: #dc3545;
                border-radius: 5px;
                min-width: 20px;
                margin: 1px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #c82333;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #a71e2a;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }
        """

    # ==================== UTILITY METHODS ====================
    @staticmethod
    def get_signal_strength_colors():
        """สีสำหรับระดับสัญญาณ"""
        return {
            'excellent': '#27ae60',  # เขียวสด
            'good': '#2ecc71',       # เขียว
            'fair': '#f39c12',       # เหลือง/ส้ม
            'poor': '#e74c3c',       # แดง
            'no_signal': '#95a5a6',  # เทา
            'error': '#c0392b'       # แดงเข้ม
        }
    
    @staticmethod
    def get_carrier_colors():
        """ส่งคืนสีสำหรับผู้ให้บริการ"""
        return {
            'AIS': '#28a745',
            'DTAC': '#007bff',
            'TRUE': '#dc3545',
            'Unknown': '#6c757d'
        }
    
    @staticmethod
    def get_signal_icons():
        """ส่งคืนไอคอนสำหรับระดับสัญญาณ"""
        return {
            'excellent': '▁▃▅█',
            'good': '▁▃▅▇',
            'fair': '▁▃▁▁',
            'poor': '▁▁▁▁',
            'no_signal': '    ',
            'error': '❌'
        }
    
    @staticmethod
    def get_signal_descriptions():
        """คำอธิบายระดับสัญญาณพร้อม Unicode bars"""
        return {
            'excellent': '▁▃▅█ Excellent',
            'good': '▁▃▅▇ Good',
            'fair': '▁▃▁▁ Fair',
            'poor': '▁▁▁▁ Poor',
            'no_signal': '▁▁▁▁ No Signal',
            'error': '▁▁▁▁ Error'
        }

    @staticmethod
    def get_signal_bars_style():
        """สไตล์สำหรับ Unicode Signal Bars"""
        return """
            QLabel {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
            }
        """