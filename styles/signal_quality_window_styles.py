# styles/signal_quality_window_styles.py

def get_stylesheet() -> str:
    return """
    QDialog {
        background-color: #fdf2f2;
        border: 2px solid #dc3545;
        border-radius: 10px;
    }
    QGroupBox {
        font-size: 13px;
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
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #c82333, stop:1 #a71e2a);
        border: 1px solid #a71e2a;
    }
    QPushButton:pressed { background: #dc3545; }
    QPushButton:disabled { background-color: #6c757d; color: #adb5bd; }

    QTabWidget::pane {
        border: 2px solid #dc3545;
        border-radius: 8px;
        background-color: #fff5f5;
    }
    QTabBar::tab {
        background-color: #f8d7da;
        color: #721c24;
        padding: 6px 12px;
        margin-right: 2px;
        border: 1px solid #f5c6cb;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected { background-color: #dc3545; color: white; font-weight: bold; }
    QTabBar::tab:hover:!selected { background-color: #f1b0b7; }

    QTableWidget {
        border: 1px solid #dc3545;
        border-radius: 4px;
        background-color: white;
        gridline-color: #f5c6cb;
        font-size: 10px;
        selection-background-color: #f8d7da;
    }
    QTableWidget::item { padding: 4px 6px; border-bottom: 1px solid #f5c6cb; min-height: 20px; }
    QTableWidget::item:selected { background-color: #f8d7da; color: #721c24; }

    QHeaderView::section {
        background-color: #dc3545;
        color: white;
        padding: 6px 8px;
        border: 1px solid #c82333;
        font-size: 10px;
        font-weight: bold;
        min-height: 25px;
    }

    QTextEdit {
        border: 1px solid #dc3545;
        border-radius: 4px;
        background-color: white;
        color: #212529;
        padding: 5px;
    }

    QComboBox, QSpinBox {
        border: 1px solid #dc3545;
        border-radius: 4px;
        padding: 2px 5px;
        background-color: white;
        min-width: 80px;
    }

    QSlider::groove:horizontal {
        border: 1px solid #dc3545;
        height: 6px;
        background: #f8d7da;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #dc3545;
        border: 1px solid #c82333;
        width: 16px; height: 16px; border-radius: 8px; margin: -5px 0;
    }
    QSlider::sub-page:horizontal { background: #dc3545; border-radius: 3px; }

    QCheckBox { color: #721c24; font-weight: 500; }
    QCheckBox::indicator {
        width: 16px; height: 16px; border: 1px solid #dc3545;
        border-radius: 2px; background-color: white;
    }
    QCheckBox::indicator:checked { background-color: #dc3545; image: none; }

    QSplitter::handle { background-color: #dc3545; width: 3px; height: 3px; }
    QScrollArea { border: none; background-color: transparent; }
    """
