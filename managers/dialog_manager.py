# dialog_manager.py
"""
จัดการ Dialogs และหน้าต่างต่างๆ
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, QTimer


class DialogManager:
    """จัดการ dialogs และหน้าต่างต่างๆ"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.open_dialogs = []
    
    def show_sms_log_dialog(self, filter_phone=None):
        """เปิดหน้าต่างดูประวัติ SMS
        
        Args:
            filter_phone (str): เบอร์โทรที่ต้องการกรอง (optional)
        """
        try:
            from widgets.sms_log_dialog import SmsLogDialog
            dlg = SmsLogDialog(filter_phone=filter_phone, parent=self.parent)
            
            # เชื่อมต่อ signal สำหรับส่ง SMS
            if hasattr(self.parent, 'prefill_sms_to_send'):
                dlg.send_sms_requested.connect(self.parent.prefill_sms_to_send)
            
            dlg.setModal(False)
            dlg.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
                            Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            dlg.show()
            
            # เก็บ reference
            self.open_dialogs.append(dlg)
            dlg.finished.connect(lambda: self.cleanup_dialog(dlg))
            
        except Exception as e:
            self.show_error_message("SMS Log Error", f"Failed to open SMS log dialog: {e}")
    
    def show_sms_realtime_monitor(self, port, baudrate, serial_thread=None):
        """เปิดหน้าต่าง SMS Real-time Monitor
        
        Args:
            port (str): พอร์ต Serial
            baudrate (int): Baudrate
            serial_thread: Serial thread object (optional)
        """
        try:
            if not port or port == "Device not found":
                QMessageBox.warning(self.parent, "Notice", "Please select a port before opening SMS monitor")
                return None
            
            if not serial_thread:
                QMessageBox.warning(self.parent, "Notice", "No serial connection available")
                return None
            
            # ตรวจสอบว่ามี dialog เปิดอยู่แล้วหรือไม่
            if (hasattr(self.parent, 'sms_monitor_dialog') and 
                self.parent.sms_monitor_dialog and 
                self.parent.sms_monitor_dialog.isVisible()):
                self.parent.sms_monitor_dialog.raise_()
                self.parent.sms_monitor_dialog.activateWindow()
                return self.parent.sms_monitor_dialog
            
            from widgets.sms_realtime_monitor import SmsRealtimeMonitor
            sms_monitor_dialog = SmsRealtimeMonitor(port, baudrate, self.parent, serial_thread=serial_thread)
            
            sms_monitor_dialog.setModal(False)
            sms_monitor_dialog.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | 
                                            Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            
            # เชื่อมต่อ signals
            if hasattr(self.parent, 'on_realtime_sms_received'):
                sms_monitor_dialog.sms_received.connect(self.parent.on_realtime_sms_received)
            if hasattr(self.parent, 'on_sms_log_updated'):
                sms_monitor_dialog.log_updated.connect(self.parent.on_sms_log_updated)
            if hasattr(self.parent, 'on_sms_monitor_closed'):
                sms_monitor_dialog.finished.connect(self.parent.on_sms_monitor_closed)
            
            sms_monitor_dialog.show()
            
            # เก็บ reference
            if hasattr(self.parent, 'sms_monitor_dialog'):
                self.parent.sms_monitor_dialog = sms_monitor_dialog
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[SMS MONITOR] Real-time SMS monitor opened")
            
            return sms_monitor_dialog
            
        except Exception as e:
            self.show_error_message("SMS Monitor Error", f"Failed to open SMS monitor: {e}")
            return None
    
    def show_loading_dialog(self, message="Loading..."):
        """แสดง Loading Dialog
        
        Args:
            message (str): ข้อความที่แสดงใน loading dialog
            
        Returns:
            tuple: (dialog, loading_widget)
        """
        try:
            from widgets.loading_widget import LoadingWidget
            from styles import LoadingWidgetStyles
            
            loading_dialog = QDialog(self.parent)
            loading_dialog.setWindowTitle("📱 ส่ง SMS")
            loading_dialog.setFixedSize(450, 280)
            loading_dialog.setModal(True)
            loading_dialog.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
            loading_dialog.setStyleSheet(LoadingWidgetStyles.get_dialog_style())

            layout = QVBoxLayout()
            loading_widget = LoadingWidget(message)
            
            # เชื่อมต่อ signal
            if hasattr(self.parent, 'on_sms_sending_finished'):
                loading_widget.finished.connect(self.parent.on_sms_sending_finished)
            
            layout.addWidget(loading_widget)
            loading_dialog.setLayout(layout)
            loading_dialog.show()
            loading_widget.start_sending()
            
            # เก็บ reference
            if hasattr(self.parent, 'loading_dialog'):
                self.parent.loading_dialog = loading_dialog
            if hasattr(self.parent, 'loading_widget'):
                self.parent.loading_widget = loading_widget
            
            return loading_dialog, loading_widget
            
        except Exception as e:
            self.show_error_message("Loading Dialog Error", f"Failed to create loading dialog: {e}")
            return None, None
    
    def close_loading_dialog(self):
        """ปิด Loading Dialog"""
        try:
            if hasattr(self.parent, 'loading_dialog') and self.parent.loading_dialog:
                self.parent.loading_dialog.close()
                self.parent.loading_dialog = None
                
            if hasattr(self.parent, 'loading_widget'):
                self.parent.loading_widget = None
                
        except Exception as e:
            print(f"Error closing loading dialog: {e}")
    
    def show_non_blocking_message(self, title, message, icon=QMessageBox.Information):
        """แสดง message box แบบ non-blocking
        
        Args:
            title (str): หัวข้อ
            message (str): ข้อความ
            icon: ไอคอนของ message box
        """
        try:
            msg_box = QMessageBox(self.parent)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setIcon(icon)
            msg_box.setModal(False)
            msg_box.setAttribute(Qt.WA_DeleteOnClose)
            msg_box.show()
            
            # Auto close after 5 seconds
            QTimer.singleShot(5000, msg_box.close)
            
        except Exception as e:
            print(f"Error showing message: {e}")
    
    def show_error_message(self, title, message):
        """แสดง error message
        
        Args:
            title (str): หัวข้อ
            message (str): ข้อความ error
        """
        self.show_non_blocking_message(title, message, QMessageBox.Critical)
    
    def show_info_message(self, title, message):
        """แสดง info message
        
        Args:
            title (str): หัวข้อ
            message (str): ข้อความ info
        """
        self.show_non_blocking_message(title, message, QMessageBox.Information)
    
    def show_warning_message(self, title, message):
        """แสดง warning message
        
        Args:
            title (str): หัวข้อ
            message (str): ข้อความ warning
        """
        self.show_non_blocking_message(title, message, QMessageBox.Warning)
    
    def auto_open_sms_monitor(self, port, baudrate, serial_thread):
        """เปิด SMS Real-time Monitor อัตโนมัติ
        
        Args:
            port (str): พอร์ต Serial
            baudrate (int): Baudrate
            serial_thread: Serial thread object
        """
        try:
            if not getattr(self.parent, 'auto_sms_monitor', True):
                return
                
            if not port or port == "Device not found" or not serial_thread:
                return
            
            if (hasattr(self.parent, 'sms_monitor_dialog') and 
                self.parent.sms_monitor_dialog and 
                self.parent.sms_monitor_dialog.isVisible()):
                return
            
            sms_monitor_dialog = self.show_sms_realtime_monitor(port, baudrate, serial_thread)
            if sms_monitor_dialog:
                QTimer.singleShot(1500, lambda: self._auto_start_monitoring(sms_monitor_dialog))
                
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[AUTO] SMS Real-time Monitor opened automatically")
            
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[AUTO ERROR] Failed to open SMS Monitor: {e}")
    
    def _auto_start_monitoring(self, dialog):
        """เริ่ม monitoring อัตโนมัติ
        
        Args:
            dialog: SMS monitor dialog
        """
        try:
            if dialog and dialog.isVisible():
                if hasattr(dialog, 'start_monitoring'):
                    dialog.start_monitoring()
                    if hasattr(self.parent, 'update_at_result_display'):
                        self.parent.update_at_result_display("[AUTO] SMS Real-time monitoring started automatically")
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[AUTO ERROR] Failed to start monitoring: {e}")
    
    def cleanup_dialog(self, dialog):
        """ลบ dialog ออกจาก list เมื่อปิด
        
        Args:
            dialog: Dialog object ที่ต้องการลบ
        """
        try:
            if dialog in self.open_dialogs:
                self.open_dialogs.remove(dialog)
        except Exception as e:
            print(f"Error cleaning up dialog: {e}")
    
    def close_all_dialogs(self):
        """ปิด dialogs ทั้งหมด"""
        try:
            for dialog in self.open_dialogs[:]:
                if dialog and dialog.isVisible():
                    dialog.close()
            self.open_dialogs.clear()
            
            # ปิด SMS monitor dialog
            if (hasattr(self.parent, 'sms_monitor_dialog') and 
                self.parent.sms_monitor_dialog and 
                self.parent.sms_monitor_dialog.isVisible()):
                self.parent.sms_monitor_dialog.close()
                self.parent.sms_monitor_dialog = None
            
            # ปิด loading dialog
            self.close_loading_dialog()
            
        except Exception as e:
            print(f"Error closing dialogs: {e}")


class SyncManager:
    """จัดการการซิงค์ข้อมูล"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def manual_sync(self):
        """ซิงค์แบบ manual"""
        try:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[MANUAL SYNC] Starting manual sync...")
            
            from services.sms_log import sync_logs_from_network_to_local, sync_logs_from_local_to_network
            
            # ซิงค์ทั้งสองทิศทาง
            network_to_local = sync_logs_from_network_to_local()
            local_to_network = sync_logs_from_local_to_network()
            
            if network_to_local or local_to_network:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[MANUAL SYNC] ✅ Sync completed successfully")
                
                if hasattr(self.parent, 'show_non_blocking_message'):
                    self.parent.show_non_blocking_message(
                        "Sync Completed", 
                        "🔄 SMS logs synchronized successfully!\n\n" +
                        f"Network → Local: {'✅' if network_to_local else '➖'}\n" +
                        f"Local → Network: {'✅' if local_to_network else '➖'}"
                    )
            else:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[MANUAL SYNC] ℹ️ No sync needed - files are up to date")
                
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[MANUAL SYNC ERROR] {e}")
            
            if hasattr(self.parent, 'show_non_blocking_message'):
                self.parent.show_non_blocking_message(
                    "Sync Error", 
                    f"❌ Manual sync failed:\n\n{e}\n\nPlease check network connection and permissions.",
                    QMessageBox.Critical
                )
    
    def auto_sync_on_startup(self):
        """ซิงค์ log files เมื่อเริ่มโปรแกรม"""
        try:
            from services.sms_log import sync_logs_from_network_to_local, sync_logs_from_local_to_network
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[SYNC] Starting auto-sync on startup...")
            
            # ลองซิงค์จาก network มา local ก่อน (ดึงข้อมูลล่าสุด)
            if sync_logs_from_network_to_local():
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SYNC] ✅ Synced from network to local")
            
            # แล้วซิงค์จาก local ไป network (push ข้อมูลใหม่)
            if sync_logs_from_local_to_network():
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SYNC] ✅ Synced from local to network")
                
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SYNC ERROR] Auto-sync failed: {e}")
    
    def setup_periodic_sync(self):
        """ตั้งค่า sync อัตโนมัติทุกๆ 5 นาที"""
        try:
            sync_timer = QTimer(self.parent)
            sync_timer.timeout.connect(self.periodic_sync)
            sync_timer.start(300000)  # 5 นาที = 300,000 ms
            
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display("[SYNC] ⏰ Periodic sync enabled (every 5 minutes)")
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SYNC ERROR] Failed to setup periodic sync: {e}")

    def periodic_sync(self):
        """ซิงค์แบบ periodic"""
        try:
            from services.sms_log import sync_logs_from_local_to_network
            if sync_logs_from_local_to_network():
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display("[SYNC] 🔄 Periodic sync completed")
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[SYNC ERROR] Periodic sync failed: {e}")
    
    def test_network_connection(self):
        """ทดสอบการเชื่อมต่อ network share"""
        try:
            from services.sms_log import get_log_directory
            log_dir = get_log_directory()
            
            if '\\\\' in log_dir or '//' in log_dir:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[NETWORK] Using network share: {log_dir}")
            else:
                if hasattr(self.parent, 'update_at_result_display'):
                    self.parent.update_at_result_display(f"[LOCAL] Using local directory: {log_dir}")
                
        except Exception as e:
            if hasattr(self.parent, 'update_at_result_display'):
                self.parent.update_at_result_display(f"[NETWORK ERROR] {e}")