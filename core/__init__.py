# core/__init__.py
"""
Core modules สำหรับ SIM Management System
"""

from .utility_functions import (
    list_serial_ports,
    normalize_phone_number,
    format_datetime_for_display,
    validate_phone_number,
    encode_text_to_ucs2,
    decode_ucs2_to_text,
    get_carrier_from_imsi,
    format_signal_strength,
    get_signal_color_by_strength,
    get_timestamp_formatted,
    safe_get_attr
)

from .settings_manager import SettingsManager, ThemeManager
from .constants import *

__all__ = [
    # Utility functions
    'list_serial_ports',
    'normalize_phone_number', 
    'format_datetime_for_display',
    'validate_phone_number',
    'encode_text_to_ucs2',
    'decode_ucs2_to_text',
    'get_carrier_from_imsi',
    'format_signal_strength',
    'get_signal_color_by_strength',
    'get_timestamp_formatted',
    'safe_get_attr',
    
    # Settings management
    'SettingsManager',
    'ThemeManager'
]