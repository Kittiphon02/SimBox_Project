from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QComboBox, QGroupBox, QSizePolicy, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QTextEdit, QFileDialog,
    QDateEdit, QCheckBox, QFrame, QSpacerItem, QShortcut, QFileDialog
)
from PyQt5.QtCore import Qt, QEvent, QDate, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QKeySequence, QBrush
import sys, os, csv, time, re
from datetime import datetime, timedelta
from styles import SmsLogDialogStyles
import json
from pathlib import Path
import portalocker
from core.utility_functions import normalize_phone_number
from services.sms_log import list_logs
import sip

# --- helper สำหรับตรวจว่าเป็น Fail หรือไม่ ---
FAIL_KEYWORDS = [
    "ล้มเหลว", "ไม่สำเร็จ", "ส่งไม่สำเร็จ", "ผิดพลาด", "ขัดข้อง",
    "fail", "failed", "error", "timeout", "time out", "not sent",
    "denied", "reject", "rejected", "cancel", "cancelled", "no route", "no service",
    "no sim", "pin required", "no signal", "no network", "connection"
]
def _is_fail_row(row: dict) -> bool:
    try:
        if int(row.get("is_failed", 0) or 0) == 1:
            return True
    except Exception:
        pass
    st = (row.get("status") or "").lower()
    return any(k in st for k in FAIL_KEYWORDS)


def get_log_directory_from_settings():
    """ดึง log directory จาก settings.json"""
    try:
        from services.sms_log import get_log_directory
        return get_log_directory()
    except Exception as e:
        print(f"Error getting log directory: {e}")
        return "./log"

_cfg_path = Path(__file__).parent / "settings.json"
try:
    LOG_DIR = Path(get_log_directory_from_settings())
except:
    LOG_DIR = Path(__file__).parent / "log"

class SmsLogDialog(QDialog):
    """หน้าต่างประวัติ SMS ที่เน้นตารางเป็นหลัก (แบบง่าย) - โทนสีแดงทางการ"""
    send_sms_requested = pyqtSignal(str, str)
    last_export_dir = None

    def __init__(self, filter_phone=None, parent=None):
        super().__init__(parent)
        
        # ==================== 1. INITIALIZATION ====================
        self.filter_phone = filter_phone
        self.all_data = []
        
        # ตั้งค่าหน้าต่าง
        self.setWindowTitle("📱 SMS History Manager | ประวัติข้อความ")
        self.resize(1000, 700)
        
        # สร้าง main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        # สร้าง UI และเชื่อมต่อ signals
        self.setup_simplified_ui()
        self.setup_connections()
        self.apply_styles()  # ใช้สไตล์ใหม่
        
        # โหลดข้อมูลเริ่มต้น
        QTimer.singleShot(100, self.load_log)
        
        # เชื่อมต่อ double click event
        self.table.cellDoubleClicked.connect(self.handle_row_double_clicked)

        self._poll = QTimer(self)
        self._poll.setInterval(2000)
        self._poll.timeout.connect(self.load_log)
        self._poll.start()

        self._init_csv_watch()
    
    def _init_csv_watch(self):
        try:
            from services.sms_log_store import READ_FROM_CSV, get_csv_file_path
        except Exception:
            return
        if not READ_FROM_CSV:
            return
        import os
        self._csv_path = get_csv_file_path()
        self._csv_mtime = os.path.getmtime(self._csv_path) if os.path.exists(self._csv_path) else None
        self._csv_timer = QTimer(self)
        self._csv_timer.setInterval(3000)  # 3 วิ
        def _tick():
            if not os.path.exists(self._csv_path): return
            m = os.path.getmtime(self._csv_path)
            if self._csv_mtime is None:
                self._csv_mtime = m; return
            if m != self._csv_mtime:
                self._csv_mtime = m
                self.load_log()
        self._csv_timer.timeout.connect(_tick)
        self._csv_timer.start()

    # ==================== 2. UI SETUP ====================
    def setup_simplified_ui(self):
        """ตั้งค่า UI แบบง่าย เหลือแค่การเลือกรายการล่าสุดหรือเก่ากว่า - Enhanced version"""
        # ==================== SEARCH SECTION (ส่วนบนสุด) ====================
        search_section = self.create_search_section()
        self.main_layout.addWidget(search_section)
        
        # ==================== CONTROL SECTION ====================
        control_section = self.create_simple_control_section()
        self.main_layout.addWidget(control_section)
        
        # ==================== TABLE SECTION ====================
        table_section = self.create_maximized_table_section()
        self.main_layout.addWidget(table_section, stretch=20)
        
        # ==================== FOOTER SECTION ====================
        footer = self.create_footer_section()
        self.main_layout.addWidget(footer)
        
        # ⭐ ตั้งค่า search shortcuts
        self.setup_search_shortcuts()

    def create_search_section(self):
        """สร้าง section สำหรับค้นหาเบอร์/ข้อความ - ปุ่มอยู่แถวเดียวกับช่องกรอก"""
        search_widget = QWidget()
        search_widget.setMinimumHeight(80)  # ลดความสูงลง
        search_widget.setMaximumHeight(90)
        
        layout = QHBoxLayout(search_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 15)

        # Search label
        search_label = QLabel("🔍 ค้นหา:")
        search_label.setFixedWidth(80)
        search_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #721c24;
                padding: 5px;
            }
        """)
        layout.addWidget(search_label)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ค้นหาจากเบอร์โทรศัพท์หรือข้อความ...")
        self.search_input.setMinimumHeight(40)
        self.search_input.setMaximumHeight(45)
        self.search_input.textChanged.connect(self.apply_search_filter)
        layout.addWidget(self.search_input)

        # Search button
        self.search_button = QPushButton("🔍 Search")
        self.search_button.setFixedWidth(100)
        self.search_button.setMinimumHeight(40)
        self.search_button.setMaximumHeight(45)
        self.search_button.clicked.connect(self.apply_search_filter)
        layout.addWidget(self.search_button)

        # Clear button
        self.clear_search_button = QPushButton("✖ Clear")
        self.clear_search_button.setFixedWidth(80)
        self.clear_search_button.setMinimumHeight(40)
        self.clear_search_button.setMaximumHeight(45)
        self.clear_search_button.clicked.connect(self.clear_search)
        layout.addWidget(self.clear_search_button)
        
        # จัดเก็บ reference สำหรับ styling
        self.search_widget = search_widget
        self.search_label = search_label

        return search_widget

    def apply_search_filter(self):
        """กรองตารางตามข้อความในช่องค้นหา - Enhanced phone number search"""
        query = self.search_input.text().strip().lower()
        visible_count = 0
        
        # ถ้าไม่มีคำค้นหา แสดงทั้งหมด
        if not query:
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
                visible_count += 1
            self.update_status_label(visible_count)
            return
        
        # ตรวจสอบว่าเป็นการค้นหาเบอร์โทรหรือไม่
        is_phone_search = self._is_phone_number_query(query)
        
        if is_phone_search:
            # ปรับเบอร์ค้นหาให้เป็นรูปแบบต่างๆ
            normalized_phones = self._generate_phone_variations(query)
            print(f"🔍 Phone search variations: {normalized_phones}")
        
        for row in range(self.table.rowCount()):
            # ดึงข้อมูลจากแต่ละคอลัมน์
            phone_item = self.table.item(row, 2)
            msg_item = self.table.item(row, 3)
            
            if phone_item and msg_item:
                phone = phone_item.text().lower()
                msg = msg_item.text().lower()
                
                show = False
                
                if is_phone_search:
                    # ค้นหาเบอร์โทรแบบ flexible
                    show = self._match_phone_numbers(phone, normalized_phones)
                else:
                    # ค้นหาข้อความปกติ
                    show = (query in phone) or (query in msg)
                
                self.table.setRowHidden(row, not show)
                
                if show:
                    visible_count += 1
            else:
                # ถ้าไม่มีข้อมูลให้ซ่อนแถว
                self.table.setRowHidden(row, True)
        
        # อัพเดทสถิติ
        self.update_status_label(visible_count)
        
        # แสดงข้อความค้นหา
        if query:
            search_type = "เบอร์โทร" if is_phone_search else "ข้อความ"
            print(f"🔍 Search for {search_type} '{query}': Found {visible_count} results")

    def _is_phone_number_query(self, query):
        """ตรวจสอบว่าคำค้นหาเป็นเบอร์โทรหรือไม่ - Enhanced Version"""
        if not query:
            return False
        
        # ลบอักขระพิเศษออก
        clean_query = ''.join(filter(str.isdigit, query))
        
        # กรณีที่ชัดเจนว่าเป็นเบอร์โทร
        obvious_phone_patterns = [
            query.startswith('+66'),
            query.startswith('66') and len(clean_query) >= 11,
            query.startswith('0') and len(clean_query) >= 9,
            len(clean_query) == 9 or len(clean_query) == 10,
            len(clean_query) == 11 and clean_query.startswith('66'),
            len(clean_query) == 12 and clean_query.startswith('66')
        ]
        
        if any(obvious_phone_patterns):
            print(f"🔍 Obvious phone pattern detected for: '{query}'")
            return True
        
        # ตรวจสอบเงื่อนไข:
        # 1. มีตัวเลขอย่างน้อย 3 ตัว
        # 2. สัดส่วนตัวเลขต่อตัวอักษรทั้งหมดมากกว่า 70%
        if len(clean_query) >= 3:
            digit_ratio = len(clean_query) / len(query) if len(query) > 0 else 0
            
            if digit_ratio >= 0.7:
                print(f"🔍 High digit ratio detected for: '{query}' ({digit_ratio:.2f})")
                return True
        
        # ตรวจสอบรูปแบบเบอร์โทรที่มีขีด/วรรค
        phone_pattern_regex = r'^[\d\s\-\+\(\)]{7,}$'
        import re
        if re.match(phone_pattern_regex, query) and len(clean_query) >= 7:
            print(f"🔍 Phone pattern regex match for: '{query}'")
            return True
        
        return False

    def _generate_phone_variations(self, query):
        """สร้างเบอร์โทรในรูปแบบต่างๆ สำหรับการค้นหา - Enhanced Version
        
        Args:
            query (str): เบอร์ที่ต้องการค้นหา
            
        Returns:
            list: รายการเบอร์ในรูปแบบต่างๆ
        """
        variations = set()
        
        # ลบอักขระพิเศษทั้งหมด
        clean_digits = ''.join(filter(str.isdigit, query))
        
        if not clean_digits:
            return [query]  # ถ้าไม่มีตัวเลขเลย ใช้ query เดิม
        
        print(f"📱 DEBUG: Processing phone query '{query}' -> digits '{clean_digits}'")
        
        # === กรณีพิเศษ: เบอร์ 10 หลักที่ขึ้นต้นด้วย 0 ===
        if clean_digits.startswith('0') and len(clean_digits) == 10:
            # 0653988461 -> สร้างทุกรูปแบบ
            phone_without_zero = clean_digits[1:]  # 653988461
            
            variations.add(clean_digits)  # 0653988461
            variations.add(phone_without_zero)  # 653988461
            variations.add(f'+66{phone_without_zero}')  # +66653988461
            variations.add(f'66{phone_without_zero}')  # 66653988461
            
            # เพิ่มรูปแบบที่มีขีด/วรรค
            variations.add(f'0{phone_without_zero[:2]}-{phone_without_zero[2:5]}-{phone_without_zero[5:]}')  # 065-398-8461
            variations.add(f'0{phone_without_zero[:2]} {phone_without_zero[2:5]} {phone_without_zero[5:]}')  # 065 398 8461
            
            print(f"📱 Generated variations for 10-digit: {variations}")
        
        # === กรณี 1: ถ้าขึ้นต้นด้วย +66 ===
        elif query.startswith('+66'):
            # +66653988461 -> 0653988461, 653988461, +66653988461
            if len(clean_digits) >= 11 and clean_digits.startswith('66'):
                national_number = '0' + clean_digits[2:]  # 0653988461
                phone_only = clean_digits[2:]  # 653988461
                
                variations.add(national_number)
                variations.add(phone_only)
                variations.add(f'+66{phone_only}')
                variations.add(f'66{phone_only}')
                variations.add(query)  # เก็บ original ด้วย
        
        # === กรณี 2: ถ้าขึ้นต้นด้วย 66 (ไม่มี +) ===
        elif clean_digits.startswith('66') and len(clean_digits) >= 11:
            # 66653988461 -> 0653988461, 653988461, +66653988461
            phone_only = clean_digits[2:]  # 653988461
            national_number = '0' + phone_only  # 0653988461
            
            variations.add(national_number)
            variations.add(phone_only)
            variations.add(f'+{clean_digits}')  # +66653988461
            variations.add(f'+66{phone_only}')
            variations.add(clean_digits)  # 66653988461
        
        # === กรณี 3: เลข 9 หลัก (ไม่มี 0 ข้างหน้า) ===
        elif len(clean_digits) == 9 and not clean_digits.startswith('0'):
            # 653988461 -> 0653988461, +66653988461, 66653988461
            variations.add(f'0{clean_digits}')  # 0653988461
            variations.add(clean_digits)  # 653988461
            variations.add(f'+66{clean_digits}')  # +66653988461
            variations.add(f'66{clean_digits}')  # 66653988461
        
        # === กรณี 4: เลขบางส่วน (สำหรับค้นหาบางส่วน) ===
        elif len(clean_digits) >= 3:
            variations.add(clean_digits)
            variations.add(query.lower())  # เก็บ query เดิม
            
            # ถ้าขึ้นต้นด้วย 0 และมี 4+ หลัก
            if clean_digits.startswith('0') and len(clean_digits) >= 4:
                without_zero = clean_digits[1:]
                variations.add(without_zero)
                variations.add(f'+66{without_zero}')
                variations.add(f'66{without_zero}')
            
            # ถ้าไม่ขึ้นต้นด้วย 0 และมี 3+ หลัก
            elif not clean_digits.startswith('0') and len(clean_digits) >= 3:
                variations.add(f'0{clean_digits}')
                variations.add(f'+66{clean_digits}')
                variations.add(f'66{clean_digits}')
        
        # === เพิ่มรูปแบบพิเศษ ===
        # เพิ่ม query เดิมด้วย (สำหรับกรณีพิเศษ)
        variations.add(query.lower())
        variations.add(query.upper())
        variations.add(clean_digits)
        
        # เพิ่มรูปแบบที่มีขีด/วรรค (ถ้ามีอยู่ใน query เดิม)
        if '-' in query or ' ' in query:
            variations.add(query)
            variations.add(query.replace('-', '').replace(' ', ''))
        
        # เพิ่มรูปแบบ normalized
        try:
            from core.utility_functions import normalize_phone_number
            normalized = normalize_phone_number(query)
            if normalized:
                variations.add(normalized)
                # สร้างรูปแบบอื่นจาก normalized
                if normalized.startswith('0') and len(normalized) == 10:
                    without_zero = normalized[1:]
                    variations.add(without_zero)
                    variations.add(f'+66{without_zero}')
                    variations.add(f'66{without_zero}')
        except Exception as e:
            print(f"Warning: normalize_phone_number error: {e}")
        
        result = list(variations)
        print(f"📱 Final phone variations for '{query}': {result}")
        return result

    def _match_phone_numbers(self, phone_in_table, search_variations):
        """ตรวจสอบว่าเบอร์ในตารางตรงกับรูปแบบค้นหาหรือไม่ - Enhanced Version
        
        Args:
            phone_in_table (str): เบอร์ในตารางที่ต้องการเช็ค
            search_variations (list): รายการเบอร์ค้นหาในรูปแบบต่างๆ
            
        Returns:
            bool: True ถ้าตรงกัน
        """
        if not phone_in_table or not search_variations:
            return False
        
        # ทำให้เป็น lowercase และเตรียมข้อมูล
        phone_lower = phone_in_table.lower().strip()
        phone_clean = phone_in_table.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').strip()
        
        print(f"🔍 Matching '{phone_in_table}' against {len(search_variations)} variations")
        
        # ตรวจสอบการตรงกันแบบเต็ม
        for variation in search_variations:
            variation_str = str(variation).lower().strip()
            variation_clean = variation_str.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
            
            # 1. ตรงกันทุกตัวอักษร (exact match)
            if phone_lower == variation_str or phone_clean.lower() == variation_clean:
                print(f"✅ Exact match: '{phone_in_table}' == '{variation}'")
                return True
            
            # 2. ตรงกันแบบ contains (สำหรับการค้นหาบางส่วน)
            if len(variation_clean) >= 3:
                if variation_clean in phone_clean.lower() or phone_clean.lower() in variation_clean:
                    print(f"✅ Contains match: '{phone_in_table}' contains '{variation}'")
                    return True
        
        # 3. ตรวจสอบแบบ normalize ทั้งสองฝั่ง
        phone_digits = ''.join(filter(str.isdigit, phone_in_table))
        
        for variation in search_variations:
            variation_digits = ''.join(filter(str.isdigit, str(variation)))
            
            if variation_digits and len(variation_digits) >= 3:
                # ตรงกันแบบ exact digits
                if phone_digits == variation_digits:
                    print(f"✅ Digits exact match: '{phone_digits}' == '{variation_digits}'")
                    return True
                
                # ตรงกันแบบ contains digits (สำหรับค้นหาบางส่วน)
                if len(variation_digits) >= 7:  # เฉพาะเบอร์ยาวๆ
                    if variation_digits in phone_digits or phone_digits in variation_digits:
                        print(f"✅ Digits contains match: '{phone_digits}' ~ '{variation_digits}'")
                        return True
        
        # 4. ตรวจสอบแบบ fuzzy match สำหรับรูปแบบพิเศษ
        try:
            from core.utility_functions import normalize_phone_number
            
            normalized_table = normalize_phone_number(phone_in_table)
            
            for variation in search_variations:
                normalized_variation = normalize_phone_number(str(variation))
                
                if normalized_table and normalized_variation:
                    if normalized_table == normalized_variation:
                        print(f"✅ Normalized match: '{normalized_table}' == '{normalized_variation}'")
                        return True
                    
                    # ตรวจสอบแบบบางส่วน
                    if len(normalized_variation) >= 7:
                        if normalized_variation in normalized_table or normalized_table in normalized_variation:
                            print(f"✅ Normalized contains: '{normalized_table}' ~ '{normalized_variation}'")
                            return True
        except Exception as e:
            print(f"Warning: normalize check error: {e}")
        
        return False

    def clear_search(self):
        """ล้างการค้นหาและแสดงข้อมูลทั้งหมด - Enhanced version"""
        self.search_input.clear()
        
        # แสดงแถวทั้งหมด
        visible_count = 0
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)
            
            # นับเฉพาะแถวที่มีข้อมูลจริง (ไม่ใช่ "ไม่มีข้อมูล")
            first_item = self.table.item(row, 0)
            if first_item and not ("ไม่มี" in first_item.text() or "🔍" in first_item.text()):
                visible_count += 1
        
        # อัพเดทสถิติ
        self.update_status_label(visible_count)
        
        print("🗑️ Search cleared - showing all data")

    def get_search_stats(self):
        """ดึงสถิติการค้นหา"""
        query = self.search_input.text().strip()
        total_rows = self.table.rowCount()
        visible_rows = 0
        hidden_rows = 0
        
        for row in range(total_rows):
            if self.table.isRowHidden(row):
                hidden_rows += 1
            else:
                visible_rows += 1
        
        return {
            'query': query,
            'total': total_rows,
            'visible': visible_rows,
            'hidden': hidden_rows,
            'is_phone_search': self._is_phone_number_query(query) if query else False
        }

    def highlight_search_results(self, query):
        """ไฮไลท์ผลการค้นหาในตาราง (สำหรับอนาคต)"""
        # สำหรับการพัฒนาในอนาคต - ไฮไลท์คำที่ค้นหา
        pass

    def setup_search_shortcuts(self):
        """ตั้งค่า keyboard shortcuts สำหรับการค้นหา"""
        
        # Ctrl+F สำหรับ focus ที่ search box
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(lambda: self.search_input.setFocus())
        
        # Escape สำหรับ clear search
        clear_shortcut = QShortcut(QKeySequence("Escape"), self)
        clear_shortcut.activated.connect(self.clear_search)
        
        # F3 สำหรับค้นหาต่อ (ถ้ามี)
        next_shortcut = QShortcut(QKeySequence("F3"), self)
        next_shortcut.activated.connect(self.apply_search_filter)

    def create_simple_control_section(self):
        """สร้างส่วนควบคุมแบบง่าย - เก็บ SMS Fail option ไว้"""
        control_widget = QWidget()
        control_widget.setObjectName("control_container")   # ← กรอบใหญ่

        hlayout = QHBoxLayout(control_widget)
        hlayout.setSpacing(15)
        hlayout.setContentsMargins(15, 10, 15, 10)

        # ---------- บล็อก "ประเภท" ----------
        self.category_container = QWidget()
        self.category_container.setObjectName("category_block")   # ← บล็อกย่อย
        cat_layout = QHBoxLayout(self.category_container)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(8)

        label_history = QLabel("📂 ประเภท:")
        cat_layout.addWidget(label_history)

        self.combo = QComboBox()
        self.combo.addItems([
            "📤 SMS Send",
            "📥 SMS Inbox",
            "❌ SMS Fail"
        ])
        self.combo.setFixedWidth(150)
        self.combo.setFixedHeight(32)
        self.combo.currentIndexChanged.connect(self.load_log)
        cat_layout.addWidget(self.combo)

        hlayout.addWidget(self.category_container)

        # ---------- บล็อก "เรียงลำดับ" ----------
        self.order_container = QWidget()
        self.order_container.setObjectName("sort_block")    # ← บล็อกย่อย
        order_layout = QHBoxLayout(self.order_container)
        order_layout.setContentsMargins(0, 0, 0, 0)
        order_layout.setSpacing(8)

        sort_label = QLabel("🔄 เรียงลำดับ:")
        order_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "รายการล่าสุด (ใหม่)",
            "รายการเก่ากว่า (เก่า)"
        ])
        self.sort_combo.setFixedWidth(200)
        self.sort_combo.setFixedHeight(32)
        self.sort_combo.currentIndexChanged.connect(self.apply_sort_filter)
        order_layout.addWidget(self.sort_combo)

        hlayout.addWidget(self.order_container)

        hlayout.addStretch()

        # เก็บอ้างอิงสำหรับใช้ใน apply_styles()
        self.control_widget = control_widget
        self.label_history = label_history
        self.sort_label = sort_label

        return control_widget

    def create_maximized_table_section(self):
        """สร้าง table section ที่ใหญ่ที่สุด - ปรับขนาดคอลัมน์"""
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['📅 DATE', '🕐 TIME', '📱 PHONE', '💬 MESSAGE'])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # วันที่
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # เวลา
        
        # แก้ไขให้คอลัมน์เบอร์โทรกว้างพอแสดงเบอร์ 10 หลัก
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 130)  # เพิ่มความกว้างเป็น 130px
        
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # ข้อความ (ขยายเต็ม)
        
        self.table.setMinimumHeight(500)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.cellDoubleClicked.connect(self.handle_row_double_clicked)

        return self.table

    def create_footer_section(self):
        """สร้าง footer section - Enhanced version"""
        footer_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setContentsMargins(5, 5, 5, 5)
        
        # Status label
        self.status_label = QLabel("📊 รายการทั้งหมด: 0")
        btn_layout.addWidget(self.status_label)
        
        btn_layout.addStretch()
        
        # --- ปุ่ม Delete ---
        self.btn_delete = self.create_button("🗑 Delete", 120)
        self.btn_delete.setToolTip("ลบรายการที่เลือก หรือทั้งแท็บ (Send/Inbox/Fail)")
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        btn_layout.addWidget(self.btn_delete)

        # ปุ่มอื่นๆ
        btn_refresh = self.create_button("🔄 Refresh", 120)
        btn_refresh.clicked.connect(self.load_log)
        btn_layout.addWidget(btn_refresh)

        btn_export = self.create_button("📊 Export All", 120)
        btn_export.clicked.connect(self.export_to_excel)
        btn_export.setToolTip("Export ข้อมูลทั้งหมด")
        btn_layout.addWidget(btn_export)
        
        btn_close = self.create_button("❌ Close", 120)
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        footer_widget.setLayout(btn_layout)
        footer_widget.setMaximumHeight(60)
        
        # จัดเก็บ reference สำหรับ styling/ใช้งานภายหลัง
        self.footer_widget = footer_widget
        self.btn_delete = self.btn_delete
        self.btn_refresh = btn_refresh
        self.btn_export = btn_export
        self.btn_close = btn_close
        
        return footer_widget

    def create_button(self, text, width=None):
        """สร้างปุ่มสไตล์เดียวกัน"""
        button = QPushButton(text)
        if width:
            button.setFixedWidth(width)
        button.setFixedHeight(40)
        return button

    def apply_styles(self):
        """ใช้สไตล์ใหม่โทนสีแดงทางการ - Enhanced version"""
        # Dialog main style
        self.setStyleSheet(SmsLogDialogStyles.get_dialog_style())
        
        # Control section
        self.control_widget.setStyleSheet(SmsLogDialogStyles.get_control_section_style())
        self.label_history.setStyleSheet(SmsLogDialogStyles.get_control_label_style())
        self.sort_label.setStyleSheet(SmsLogDialogStyles.get_control_label_style())
        
        # ComboBoxes
        self.combo.setStyleSheet(SmsLogDialogStyles.get_combo_box_style())
        self.sort_combo.setStyleSheet(SmsLogDialogStyles.get_combo_box_style())
        
        # Table styles
        self.table.setStyleSheet(SmsLogDialogStyles.get_table_style())
        self.table.horizontalHeader().setStyleSheet(SmsLogDialogStyles.get_table_header_style())
        
        # Status label
        self.status_label.setStyleSheet(SmsLogDialogStyles.get_status_label_style())
        
        # Footer
        self.footer_widget.setStyleSheet(SmsLogDialogStyles.get_footer_style())
        
        # Buttons
        self.btn_delete.setStyleSheet(SmsLogDialogStyles.get_delete_button_style())
        self.btn_refresh.setStyleSheet(SmsLogDialogStyles.get_info_button_style())
        self.btn_export.setStyleSheet(SmsLogDialogStyles.get_success_button_style())
        self.btn_close.setStyleSheet(SmsLogDialogStyles.get_danger_button_style())

    def setup_connections(self):
        """เชื่อมต่อ signals แบบง่าย"""
        # เชื่อมต่อ ComboBox เรียงลำดับกับฟังก์ชันเรียงลำดับ
        self.sort_combo.currentIndexChanged.connect(self.apply_sort_filter)

    # ==================== 3. UTILITY FUNCTIONS ====================
    def darken_color(self, color, factor=0.2):
        """ทำให้สีเข้มขึ้น"""
        return SmsLogDialogStyles.darken_color(color, factor)

    def normalize_phone(self, phone):
        """ปรับรูปแบบเบอร์โทร"""
        phone = phone.replace('-', '').replace(' ', '')
        if phone.startswith('+66'):
            phone = phone[3:]
        elif phone.startswith('66'):
            phone = phone[2:]
        return phone.lstrip('0')

    def parse_date_from_string(self, date_str):
        """แปลงข้อความวันที่เป็น datetime object - แก้ไขปีให้ถูกต้อง"""
        try:
            if ',' in date_str:
                date_part, time_part = date_str.split(',')
                y, m, d = date_part.split('/')
                year = int(y)
                
                # แก้ไขการคำนวณปี
                if year < 100:
                    # ถ้าเป็น YY format
                    if year >= 50:  # 50-99 = 1950-1999
                        year += 1900
                    else:  # 00-49 = 2000-2049
                        year += 2000
                
                return datetime.strptime(f"{year:04d}-{m}-{d} {time_part}", "%Y-%m-%d %H:%M:%S")
            else:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"[❌ Date parse failed] {date_str} | {e}")
            return None

    def update_status_label(self, custom_count=None):
        """อัพเดทข้อความสถานะ"""
        try:
            if custom_count is not None:
                # ใช้จำนวนที่กำหนด (สำหรับการค้นหา)
                total_items = custom_count
            else:
                # นับจำนวนแถวที่แสดงอยู่
                total_items = 0
                for row in range(self.table.rowCount()):
                    if not self.table.isRowHidden(row):
                        total_items += 1
                
                # ตรวจสอบว่าเป็นข้อความ "ไม่มีข้อมูล" หรือไม่
                if total_items == 1:
                    first_item = self.table.item(0, 0)
                    if first_item and ("ไม่มี" in first_item.text() or "🔍" in first_item.text()):
                        total_items = 0
            
            # อัพเดทข้อความ
            search_query = self.search_input.text().strip()
            if search_query:
                self.status_label.setText(f"📊 ผลการค้นหา '{search_query}': {total_items} รายการ")
            else:
                self.status_label.setText(f"📊 รายการทั้งหมด: {total_items}")
                
        except Exception as e:
            print(f"Error updating status label: {e}")
            self.status_label.setText("📊 รายการทั้งหมด: 0")
            
    # ==================== 4. DATA LOADING ====================
    def clear_table(self):
        """ล้างข้อมูลตาราง + เคลียร์ buffer/ตัวนับ"""
        try:
            self.table.setRowCount(0)
        except Exception:
            pass
        self.all_data = []
        if hasattr(self, "total_label") and self.total_label is not None:
            self.total_label.setText("รายการทั้งหมด: 0")

    def _render_rows(self, rows, direction):
        self.table.setRowCount(len(rows))
        self.all_data = []

        for i, r in enumerate(rows):
            raw_dt = r.get('dt')
            if hasattr(raw_dt, 'strftime'):
                dt_obj = raw_dt
                date = dt_obj.strftime("%d/%m/%Y")
                time_str = dt_obj.strftime("%H:%M:%S")
            else:
                if direction == 'sent':
                    date, time_str, dt_obj = self.parse_sent_datetime(str(raw_dt or ""))
                else:
                    date, time_str, dt_obj = self.parse_inbox_datetime(str(raw_dt or ""))

            phone = r.get("phone") or ""
            msg   = r.get("message") or ""

            # ✅ สร้าง items แยกตัวแปรให้ถูกต้อง
            it_date  = QTableWidgetItem(date)
            it_time  = QTableWidgetItem(time_str)
            it_phone = QTableWidgetItem(phone)
            it_msg   = QTableWidgetItem(msg)

            # ✅ ทำรายการที่เป็น Fail ให้เป็นสีแดง
            try:
                is_fail = _is_fail_row(r)   # ถ้ามี helper ตามที่เพิ่มไว้
            except NameError:
                is_fail = int(r.get("is_failed", 0) or 0) == 1

            if is_fail:
                red_fg   = QBrush(QColor(220, 53, 69))
                light_bg = QBrush(QColor(255, 235, 238))
                for it in (it_date, it_time, it_phone, it_msg):
                    it.setForeground(red_fg)
                    it.setBackground(light_bg)

            # ใส่ลงตาราง
            self.table.setItem(i, 0, it_date)
            self.table.setItem(i, 1, it_time)
            self.table.setItem(i, 2, it_phone)
            self.table.setItem(i, 3, it_msg)

            # ✅ อย่าลืมคอมม่าหลัง "message": msg
            self.all_data.append({
                "date": date,
                "time": time_str,
                "phone": phone,
                "message": msg,
                "datetime": dt_obj,
                "status": r.get("status") or "",
                "is_failed": int(r.get("is_failed", 0) or 0),
            })

        if hasattr(self, "total_label") and self.total_label is not None:
            self.total_label.setText(f"รายการทั้งหมด: {len(rows)}")

    def _inbox_has_data(self) -> bool:
        """คืน True ถ้าในฐานข้อมูลมีรายการ SMS inbox อย่างน้อย 1 แถว"""
        try:
            from services.sms_log import list_logs
            return bool(list_logs(direction="inbox", limit=1))
        except Exception:
            return False
    
    def load_log(self):
        # ประเภทจากคอมโบ (0:send, 1:inbox, 2:fail)
        idx = self.combo.currentIndex()
        cat = {0: "send", 1: "inbox", 2: "fail"}.get(idx, "inbox")

        # ดึง order จากคอมโบเรียง (รองรับชื่อทั้ง sort_combo / order_combo)
        order = "DESC"
        try:
            combo = getattr(self, "sort_combo", None) or getattr(self, "order_combo", None)
            if combo:
                txt = (combo.currentText() or "").strip().upper()
                order = "ASC" if ("เก่า" in txt or txt == "ASC") else "DESC"
        except Exception:
            pass

        # ดึงข้อมูลตามทิศทาง
        direction = "inbox" if cat == "inbox" else "sent"
        try:
            rows = list_logs(direction=direction, limit=5000, order=order) or []
        except Exception as e:
            print(f"DB error: {e}")
            self.show_error_message(e)
            return

        self.all_data = []
        for r in rows:
            raw_dt = r.get("dt")

            # --- แปลงวันเวลาให้เป็นฟอร์แมตเดียวกับหน้า Send ---
            if hasattr(raw_dt, "strftime"):
                dt_obj = raw_dt
                date = dt_obj.strftime("%d/%m/%Y")
                time_str = dt_obj.strftime("%H:%M:%S")
            else:
                s = str(raw_dt or "")
                if direction == "inbox":
                    # ใช้ parser inbox (รองรับ 'YYYY-MM-DD HH:MM:SS' และรูปแบบ GSM)
                    date, time_str, dt_obj = self.parse_inbox_datetime(s)
                else:
                    date, time_str, dt_obj = self.parse_sent_datetime(s)

            # ธง fail
            try:
                is_failed = 1 if _is_fail_row(r) else 0
            except NameError:
                # fallback ถ้ายังไม่มี helper
                is_failed = int(r.get("is_failed", 0) or 0)

            # เก็บเรคอร์ด
            rec = {
                "row_id": r.get("id"), 
                "date": date,
                "time": time_str,
                "phone": r.get("phone") or "",
                "message": r.get("message") or "",
                "datetime": dt_obj,             # ใช้สำหรับ sort/filter
                "status": r.get("status") or "",
                "is_failed": is_failed,
            }

            if cat == "fail":
                if rec["is_failed"] == 1:
                    self.all_data.append(rec)
            else:
                # send / inbox
                self.all_data.append(rec)

        # --- กฎพิเศษ: ถ้า Inbox มีข้อมูล แต่ Send/Fail ไม่มี → หน้า Send/Fail ว่างเปล่า ---
        if cat in ("send", "fail") and not self.all_data and self._inbox_has_data():
            self.clear_table()           # ว่างจริง ไม่แสดงแถว "ไม่มีข้อมูล"
            self.update_status_label(0)
            return

        # Inbox ไม่มีข้อมูล → ให้โชว์หน้าว่างแบบข้อความ
        if cat == "inbox" and not self.all_data:
            self.display_filtered_data([])    # จะขึ้น "ยังไม่มีประวัติ SMS เข้า"
            self.update_status_label(0)
            return

        # ใช้การเรียงลำดับ/ฟิลเตอร์/วาดตารางตามเดิม
        self.apply_sort_filter()

    def _is_failed_sms(self, status):
        """ตรวจสอบว่า SMS ส่งไม่สำเร็จหรือไม่"""
        if not status:
            return False
        
        status_lower = status.lower()
        
        # คำที่บ่งบอกว่าส่งไม่สำเร็จ
        failed_keywords = [
            'ไม่สำเร็จ', 'ล้มเหลว', 'fail', 'error', 'failed',
            'ไม่มี sim', 'no sim', 'sim not ready', 'pin required',
            'no signal', 'no network', 'timeout', 'connection'
        ]
        
        return any(keyword in status_lower for keyword in failed_keywords)

    def show_error_message(self, message):
        """แสดงข้อความ error"""
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem("❌ เกิดข้อผิดพลาด"))
        self.table.setItem(0, 1, QTableWidgetItem(""))
        self.table.setItem(0, 2, QTableWidgetItem(""))
        self.table.setItem(0, 3, QTableWidgetItem(str(message)))
        for col in range(4):
            it = self.table.item(0, col)
            if it:
                it.setTextAlignment(Qt.AlignCenter)
                it.setForeground(QColor(231, 76, 60))
        self.update_status_label()

    def parse_sent_datetime(self, dt_str):
        """แยกฟังก์ชัน parse วันที่สำหรับ sent - รูปแบบ YYYY-MM-DD HH:MM:SS"""
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            # ✅ แปลงเป็น DD/MM/YYYY
            date = dt.strftime("%d/%m/%Y")
            time = dt.strftime("%H:%M:%S")
            return date, time, dt
        except:
            return dt_str, "", None

    def parse_inbox_datetime(self, dt_str):
        """แปลงวันที่/เวลา SMS Inbox ให้ได้รูปแบบเดียวกับ SMS Send (DD/MM/YYYY, HH:MM:SS).

        รองรับทั้ง:
        - 'YYYY-MM-DD HH:MM:SS'  (ที่มาจากฐานข้อมูล)
        - 'DD/MM/YY,HH:MM:SS+zz' (บางโมเด็มรายงานมาแบบนี้)
        """
        s = (dt_str or "").strip()

        # 1) ลองฟอร์แมตแบบ DB ก่อน: YYYY-MM-DD HH:MM:SS
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S"), dt
        except Exception:
            pass

        # 2) ลองฟอร์แมตแบบ GSM: DD/MM/YY,HH:MM:SS+zz
        try:
            if "," not in s:
                return s, "", None

            dpart, tpart = s.split(",", 1)
            time_str = tpart.split("+", 1)[0].strip()

            parts = dpart.split("/")
            if len(parts) != 3:
                return s, "", None

            dd, mm, yy = int(parts[0]), int(parts[1]), int(parts[2])

            # ปี 2 หลัก -> 4 หลัก
            if parts[2].isdigit() and len(parts[2]) == 2:
                cur_yy = datetime.now().year % 100
                yyyy = 2000 + yy if yy <= cur_yy else 1900 + yy
            else:
                yyyy = yy

            dt = datetime.strptime(f"{yyyy:04d}-{mm:02d}-{dd:02d} {time_str}", "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S"), dt
        except Exception:
            return s, "", None


    # ==================== 5. DATA FILTERING & SORTING ====================
    def apply_sort_filter(self):
        """ใช้ฟิลเตอร์การเรียงลำดับ"""
        try:
            if not self.all_data:
                print("No data to sort")
                return
                
            print(f"Sorting data, count: {len(self.all_data)}, sort index: {self.sort_combo.currentIndex()}")
            
            # กรองข้อมูล
            filtered_data = self.all_data.copy()
            idx = self.combo.currentIndex()
            
            # ถ้าเป็น SMS Fail ให้เอาเฉพาะเรคอร์ดที่ติดธง is_failed = 1
            if idx == 2:
                filtered_data = [d for d in filtered_data if int(d.get('is_failed', 0) or 0) == 1]

            # เรียงลำดับตามที่เลือก
            if self.sort_combo.currentIndex() == 0:  # รายการล่าสุด (ใหม่ → เก่า)
                filtered_data.sort(key=lambda x: x['datetime'] if x['datetime'] else datetime.min, reverse=True)
                print("Sorted: latest first")
            else:  # รายการเก่ากว่า (เก่า → ใหม่)
                filtered_data.sort(key=lambda x: x['datetime'] if x['datetime'] else datetime.min, reverse=False)
                print("Sorted: oldest first")
            
            self.display_filtered_data(filtered_data)
            self.update_status_label()
            
        except Exception as e:
            print(f"Error applying sort filter: {e}")
            import traceback
            traceback.print_exc()

    # ==================== 6. TABLE DISPLAY ====================
    def display_filtered_data(self, data):
        """แสดงข้อมูลที่กรองแล้วในตาราง - Updated สำหรับ SMS Fail"""
        self.table.setRowCount(0)
        
        if not data:
            self.table.setRowCount(1)
            
            # เลือกข้อความที่เหมาะสมตามประเภท
            idx = self.combo.currentIndex()
            if idx == 2:  # SMS Fail
                no_data_msg = "ยังไม่มี SMS ที่ส่งไม่สำเร็จ"
                icon = "✅"
            elif idx == 1:  # SMS Inbox
                no_data_msg = "ยังไม่มีประวัติ SMS เข้า"
                icon = "📥"
            else:  # SMS Send
                no_data_msg = "ยังไม่มีประวัติ SMS ส่งออก"
                icon = "📤"
            
            self.table.setItem(0, 0, QTableWidgetItem(f"{icon} ไม่มีข้อมูล"))
            self.table.setItem(0, 1, QTableWidgetItem(""))
            self.table.setItem(0, 2, QTableWidgetItem(""))
            self.table.setItem(0, 3, QTableWidgetItem(no_data_msg))
            
            # จัดให้ข้อความอยู่กลาง
            for col in range(4):
                item = self.table.item(0, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # ใช้สีต่างกันตามประเภท
                    if idx == 2:  # SMS Fail
                        item.setForeground(QColor(46, 204, 113))  # เขียว - ดีที่ไม่มี error
                    else:
                        item.setForeground(QColor(127, 140, 141))  # เทา - ปกติ
            return
            
        for row_idx, item in enumerate(data):
            self.table.insertRow(row_idx)
            
            # วันที่
            date_item = QTableWidgetItem(item['date'])
            date_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, date_item)
            
            # เวลา
            time_item = QTableWidgetItem(item['time'])
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, time_item)
            
            # เบอร์โทร
            phone_display = item.get('phone') or "Unknown"
            phone_item = QTableWidgetItem(phone_display)
            phone_item.setTextAlignment(Qt.AlignCenter)
            phone_item.setToolTip(phone_display)
            self.table.setItem(row_idx, 2, phone_item)
            
            # ข้อความ
            message_text = item['message']
            
            message_item = QTableWidgetItem(message_text)
            message_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            # ใช้สีต่างกันสำหรับ SMS Fail
            if self.combo.currentIndex() == 2:
                message_item.setForeground(QColor(231, 76, 60))  # แดง - error
                phone_item.setForeground(QColor(231, 76, 60))
            
            self.table.setItem(row_idx, 3, message_item)

            # ฝัง row_id ลงใน cell (สำหรับลบ)
            row_id = item.get("row_id")
            if row_id is not None:
                for col in range(4):
                    cell_item = self.table.item(row_idx, col)
                    if cell_item:
                        cell_item.setData(Qt.UserRole, int(row_id))
            
            # เพิ่มสีสันให้แถว
            if row_idx % 2 == 0:
                # ตั้งค่า background color สำหรับแถวที่เป็นเลขคู่
                bg_color = QColor(248, 249, 250)  # ปกติ
                if self.combo.currentIndex() == 2:  # SMS Fail
                    bg_color = QColor(253, 237, 238)  # แดงอ่อน
                    
                for col in range(4):
                    cell_item = self.table.item(row_idx, col)
                    if cell_item:
                        cell_item.setBackground(bg_color)

    # ==================== 7. EVENT HANDLERS ====================
    def handle_row_double_clicked(self, row, col):
        """จัดการเมื่อมีการ double click บนแถว"""
        phone_item = self.table.item(row, 2)
        msg_item = self.table.item(row, 3)
        if phone_item and msg_item:
            phone = phone_item.text()
            message = msg_item.text()
            self.send_sms_requested.emit(phone, message)
        self.accept()

    def on_row_double_clicked(self, row, col):
        """จัดการเมื่อมีการ double click บนแถว (อีกวิธี)"""
        # ดึงค่าเบอร์กับข้อความจากตาราง
        phone = self.table.item(row, 2).text()
        message = self.table.item(row, 3).text()
        # ส่งสัญญาณกลับไปหน้า main
        self.send_sms_requested.emit(phone, message)
        # ปิด dialog
        self.accept()
    
    def on_delete_clicked(self):
        """
        ลบประวัติ SMS:
        - ถ้าเลือกหลายแถว → ลบเฉพาะแถวที่เลือก
        - ถ้าไม่ได้เลือก → ถามว่าจะลบทั้งแท็บนี้ไหม (Send/Inbox/Fail)
        """
        try:
            from services.sms_log import delete_selected, delete_all, vacuum_db
        except Exception as e:
            QMessageBox.warning(self, "Delete Error", f"ไม่สามารถเรียกใช้บริการลบได้: {e}")
            return

        # แท็บปัจจุบัน
        idx = self.combo.currentIndex() if hasattr(self, "combo") else 0
        view = {0: "send", 1: "inbox", 2: "fail"}.get(idx, "send")
        direction = "inbox" if view == "inbox" else "sent"

        # ดึง id ของแถวที่เลือก
        sel_rows = sorted({mi.row() for mi in self.table.selectionModel().selectedRows()})
        chosen_ids = []
        for r in sel_rows:
            it = self.table.item(r, 0)
            if it:
                rid = it.data(Qt.UserRole)
                if rid is not None:
                    chosen_ids.append(int(rid))

        # ไม่มีการเลือก → ถามว่าจะลบทั้งหมดในแท็บนี้ไหม
        if not chosen_ids:
            # Fail = ลบเฉพาะ fail ในตาราง sent
            only_failed = (view == "fail")
            label_map = {"send": "ประวัติ SMS ส่งออกทั้งหมด",
                        "inbox": "ประวัติ SMS เข้า",
                        "fail": "ประวัติ SMS ที่ส่งไม่สำเร็จ"}
            msg = f"ต้องการลบ{label_map.get(view, 'ข้อมูลในหน้านี้')} ทั้งหมดหรือไม่?"
            if QMessageBox.question(self, "Confirm Delete", msg,
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            try:
                delete_all(direction=direction, only_failed=only_failed)
                vacuum_db()
            except Exception as e:
                QMessageBox.warning(self, "Delete Error", f"ลบไม่สำเร็จ: {e}")
                return
            self.load_log()
            return

        # มีการเลือก → ยืนยันลบเฉพาะรายการที่เลือก
        if QMessageBox.question(
            self,
            "Confirm Delete",
            f"ต้องการลบ {len(chosen_ids)} รายการที่เลือกหรือไม่?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) != QMessageBox.Yes:
            return

        try:
            delete_selected(direction, chosen_ids)
            vacuum_db()
        except Exception as e:
            QMessageBox.warning(self, "Delete Error", f"ลบไม่สำเร็จ: {e}")
            return

        self.load_log()


    # ==================== 8. EXPORT FUNCTIONS ====================
    def export_to_excel(self):
        """Export ข้อมูลที่แสดงอยู่ไปยัง Excel - เก็บ SMS Fail ไว้"""
        try:
            import pandas as pd
        except ImportError:
            QMessageBox.warning(
                self, 
                "📊 Export Error", 
                "❌ ต้องติดตั้ง pandas ก่อน\n\nรันคำสั่ง: pip install pandas"
            )
            return
        
        row_count = self.table.rowCount()
        if row_count == 0 or (row_count == 1 and not self.table.item(0, 0)):
            QMessageBox.information(
                self, 
                "📊 Export", 
                "⚠️ กรุณาเลือกข้อมูลที่จะ Export ก่อน"
            )
            return
        
        data = []
        headers = ['วันที่', 'เวลา', 'เบอร์โทร', 'ข้อความ']
        
        for row in range(row_count):
            # ข้ามแถวที่ถูกซ่อน (จากการค้นหา)
            if self.table.isRowHidden(row):
                continue
                
            row_data = []
            empty_row = True
            for col in range(4):
                item = self.table.item(row, col)
                txt = item.text() if item else ''
                if txt and "ไม่มี" not in txt and "🔍" not in txt and "❌" not in txt and "✅" not in txt:
                    empty_row = False
                row_data.append(txt)
            if not empty_row:
                data.append(row_data)
        
        if not data:
            QMessageBox.information(
                self, 
                "📊 Export", 
                "⚠️ ไม่มีข้อมูลให้ Export"
            )
            return
        
        df = pd.DataFrame(data, columns=headers)
        
        # เลือกโฟลเดอร์ default
        if SmsLogDialog.last_export_dir and os.path.exists(SmsLogDialog.last_export_dir):
            initial_dir = SmsLogDialog.last_export_dir
        elif LOG_DIR.exists():
            initial_dir = str(LOG_DIR)
        else:
            initial_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        
        # สร้างชื่อไฟล์ตามประเภท
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        idx = self.combo.currentIndex()
        
        # ⭐ เก็บ SMS Fail case ไว้
        if idx == 2:
            sms_type = "failed"
            type_name = "Failed SMS"
        elif idx == 1:
            sms_type = "inbox"
            type_name = "SMS Inbox"
        else:
            sms_type = "sent"
            type_name = "SMS Sent"
            
        filename = f"sms_{sms_type}_log_{timestamp}.xlsx"
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"📊 Export {type_name}",
            os.path.join(initial_dir, filename),
            "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not path:
            return
        
        SmsLogDialog.last_export_dir = os.path.dirname(path)
        
        try:
            if path.endswith('.csv'):
                df.to_csv(path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(path, index=False)
                
            QMessageBox.information(
                self, 
                "✅ Export สำเร็จ", 
                f"📊 Export {type_name} เรียบร้อยแล้ว!\n\n"
                f"📁 ไฟล์: {os.path.basename(path)}\n"
                f"📂 ตำแหน่ง: {os.path.dirname(path)}\n"
                f"📋 จำนวนรายการ: {len(data)} รายการ"
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "❌ Export Error", 
                f"💥 Export {type_name} ไม่สำเร็จ!\n\n"
                f"ข้อผิดพลาด: {str(e)}\n\n"
                f"กรุณาตรวจสอบ:\n"
                f"• ไฟล์ไม่ได้เปิดอยู่ในโปรแกรมอื่น\n"
                f"• มีสิทธิ์เขียนไฟล์ในโฟลเดอร์นั้น\n"
                f"• พื้นที่ดิสก์เพียงพอ"
            )

    # ==================== 9. WINDOW EVENT HANDLERS ====================
    def closeEvent(self, event):
        """จัดการเมื่อปิดหน้าต่าง SMS Log"""
        event.accept()
        self.deleteLater()


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SmsLogDialog()
    dialog.show()
    sys.exit(app.exec_())