import sys
from PyQt5.QtWidgets import QApplication
from windows.sim_info_window import SimInfoWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimInfoWindow()
    window.show()
    sys.exit(app.exec_())