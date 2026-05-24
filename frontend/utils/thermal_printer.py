"""
ESC/POS Thermal Printer Support — raw command generation for receipt printers.
Supports 58mm and 80mm thermal printers with auto-cut, cash drawer, and barcode printing.

Architecture:
  ThermalPrinterService
    ├── ESC/POS Command Builder (generates byte sequences)
    ├── Windows/COM port writer (raw USB/serial)
    ├── Network printer writer (TCP socket)
    └── QPrinter fallback (generic driver)
"""

import socket
from typing import Optional, Dict, Any
from enum import Enum

from utils.company_config import get_cached_config


class PrinterWidth(Enum):
    MM_58 = 384  # 58mm paper ~384 dots
    MM_80 = 576  # 80mm paper ~576 dots


class PrintDensity(Enum):
    NORMAL = 0
    DOUBLE_WIDTH = 1
    DOUBLE_HEIGHT = 16
    DOUBLE_BOTH = 17


class ThermalPrinter:
    """
    ESC/POS thermal printer abstraction.
    Generates raw byte commands and sends to the physical device.
    """

    # ESC/POS byte constants
    ESC = b'\x1b'
    GS = b'\x1d'
    LF = b'\x0a'
    CR = b'\x0d'

    def __init__(self, width: PrinterWidth = PrinterWidth.MM_58):
        self._width = width
        self._buffer: bytearray = bytearray()
        self._connection = None
        self._timeout = 5.0

    # ── Initialization ──

    def init(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'@')
        return self

    def reset(self) -> 'ThermalPrinter':
        self._buffer = bytearray()
        return self

    # ── Alignment ──

    def align_left(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'a' + b'\x00')
        return self

    def align_center(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'a' + b'\x01')
        return self

    def align_right(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'a' + b'\x02')
        return self

    # ── Text Style ──

    def bold_on(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'E' + b'\x01')
        return self

    def bold_off(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'E' + b'\x00')
        return self

    def underline_on(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'-' + b'\x01')
        return self

    def underline_off(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'-' + b'\x00')
        return self

    def set_size(self, width: int = 1, height: int = 1) -> 'ThermalPrinter':
        n = ((height - 1) << 4) | (width - 1)
        self._buffer.extend(self.GS + b'!' + bytes([n]))
        return self

    def set_font_b(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'M' + b'\x01')
        return self

    def set_font_a(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'M' + b'\x00')
        return self

    # ── Content ──

    def text(self, s: str) -> 'ThermalPrinter':
        self._buffer.extend(s.encode('cp437', errors='replace'))
        return self

    def text_line(self, s: str = '') -> 'ThermalPrinter':
        return self.text(s).newline()

    def newline(self, count: int = 1) -> 'ThermalPrinter':
        self._buffer.extend(self.LF * count)
        return self

    def feed(self, lines: int = 1) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'd' + bytes([lines]))
        return self

    def reverse_feed(self, lines: int = 1) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'e' + bytes([lines]))
        return self

    def separator(self, char: str = '-', length: Optional[int] = None) -> 'ThermalPrinter':
        max_len = length if length is not None else (self._width.value // 12)
        return self.text_line(char * max_len)

    # ── Barcode ──

    def barcode_ean13(self, code: str) -> 'ThermalPrinter':
        if len(code) == 12 and code.isdigit():
            total = sum(int(d) * (3 if i % 2 == 1 else 1) for i, d in enumerate(code))
            check = (10 - (total % 10)) % 10
            code = f"{code}{check}"
        code_bytes = code.encode('ascii')
        height = 50
        width = 2
        self._buffer.extend(self.GS + b'H' + b'\x02')
        self._buffer.extend(self.GS + b'h' + bytes([height]))
        self._buffer.extend(self.GS + b'w' + bytes([width]))
        self._buffer.extend(self.GS + b'k' + bytes([67, len(code_bytes)]))
        self._buffer.extend(code_bytes)
        return self.newline()

    def barcode_code128(self, code: str) -> 'ThermalPrinter':
        code_bytes = code.encode('ascii')
        height = 50
        width = 2
        self._buffer.extend(self.GS + b'H' + b'\x02')
        self._buffer.extend(self.GS + b'h' + bytes([height]))
        self._buffer.extend(self.GS + b'w' + bytes([width]))
        self._buffer.extend(self.GS + b'k' + bytes([73, len(code_bytes)]))
        self._buffer.extend(code_bytes)
        return self.newline()

    # ── QR Code ──

    def qr_code(self, data: str, module_size: int = 4) -> 'ThermalPrinter':
        data_bytes = data.encode('cp437', errors='replace')
        total_len = len(data_bytes) + 3
        pl = total_len % 256
        ph = total_len // 256
        self._buffer.extend(self.GS + b'(k' + bytes([pl, ph, 49, 80, 48]))
        self._buffer.extend(self.GS + b'(k' + bytes([3, 0, 49, 69, module_size]))
        self._buffer.extend(self.GS + b'(k' + bytes([3, 0, 49, 67, 1]))
        store_pl = (len(data_bytes) + 3) % 256
        store_ph = (len(data_bytes) + 3) // 256
        self._buffer.extend(self.GS + b'(k' + bytes([store_pl, store_ph, 49, 80, 48]))
        self._buffer.extend(data_bytes)
        self._buffer.extend(self.GS + b'(k' + bytes([3, 0, 49, 81, 48]))
        return self.newline()

    # ── Hardware ──

    def cut(self, partial: bool = False) -> 'ThermalPrinter':
        m = b'\x01' if partial else b'\x00'
        self._buffer.extend(self.GS + b'V' + m)
        return self

    def open_drawer(self) -> 'ThermalPrinter':
        self._buffer.extend(b'\x1b\x70\x00\x19\xfa')
        return self

    def beep(self) -> 'ThermalPrinter':
        self._buffer.extend(b'\x1b\x42\x01\x01')
        return self

    def status(self) -> 'ThermalPrinter':
        self._buffer.extend(self.ESC + b'v' + b'\x00')
        return self

    # ── Receipt Builders ──

    def build_receipt(self, receipt_data: Dict[str, Any]) -> bytes:
        config = get_cached_config()
        cfg = config.to_dict() if config else {}
        self.init().align_center()
        name = receipt_data.get("company_name", cfg.get("name", "Pharmacy ERP"))
        self.set_size(2, 2).text_line(name).set_size(1, 1)
        addr = receipt_data.get("address", cfg.get("address", ""))
        if addr:
            self.text_line(addr)
        phone = receipt_data.get("phone", cfg.get("phone", ""))
        if phone:
            self.text_line(f"Tel: {phone}")
        self.separator()

        self.text_line(f"Receipt: {receipt_data.get('receipt_number', 'N/A')}")
        self.text_line(f"Date: {receipt_data.get('date', '')}")
        self.text_line(f"Cashier: {receipt_data.get('cashier', 'N/A')}")
        self.separator()

        self.align_left()
        for item in receipt_data.get("items", []):
            name = item.get("product_name", "Item")
            qty = item.get("quantity", 0)
            total = item.get("total", 0)
            if len(name) > 22:
                name = name[:20] + ".."
            self.text_line(f"{name:<22} {qty:>3}  {total:>7.2f}")

        self.separator()
        self.align_right()
        self.text_line(f"Subtotal: {receipt_data.get('subtotal', 0):>8.2f}")
        self.text_line(f"Total:    {receipt_data.get('total_amount', 0):>8.2f}")
        self.text_line(f"Paid:     {receipt_data.get('paid_amount', 0):>8.2f}")
        self.text_line(f"Change:   {receipt_data.get('change', 0):>8.2f}")

        self.align_center().newline()
        self.text_line(receipt_data.get("footer", "Thank you!"))
        qr = receipt_data.get("qr_data", "")
        if qr:
            self.qr_code(qr)
        self.newline(3).cut()
        return bytes(self._buffer)

    # ── Printing ──

    def print_to_file(self, filepath: str) -> bool:
        try:
            with open(filepath, 'wb') as f:
                f.write(bytes(self._buffer))
            return True
        except Exception:
            return False

    def print_to_windows_printer(self, printer_name: str) -> bool:
        try:
            import win32print
            h_printer = win32print.OpenPrinter(printer_name)
            try:
                win32print.StartDocPrinter(h_printer, 1, ("Receipt", None, "RAW"))
                win32print.StartPagePrinter(h_printer)
                win32print.WritePrinter(h_printer, bytes(self._buffer))
                win32print.EndPagePrinter(h_printer)
                win32print.EndDocPrinter(h_printer)
            finally:
                win32print.ClosePrinter(h_printer)
            return True
        except Exception:
            return self._fallback_qprinter()

    def print_to_network(self, host: str, port: int = 9100) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((host, port))
            sock.send(bytes(self._buffer))
            sock.close()
            return True
        except Exception:
            return False

    def print_to_com(self, port: str = 'COM1', baudrate: int = 9600) -> bool:
        try:
            import serial
            ser = serial.Serial(port, baudrate=baudrate, timeout=self._timeout)
            ser.write(bytes(self._buffer))
            ser.close()
            return True
        except Exception:
            return False

    def _fallback_qprinter(self) -> bool:
        try:
            from PySide6.QtPrintSupport import QPrinter
            from PySide6.QtGui import QTextDocument
            printer = QPrinter(QPrinter.HighResolution)
            doc = QTextDocument()
            text = bytes(self._buffer).decode('cp437', errors='replace')
            doc.setPlainText(text)
            doc.print_(printer)
            return True
        except Exception:
            return False

    def get_buffer_size(self) -> int:
        return len(self._buffer)

    def print_raw(self) -> bool:
        try:
            import win32print
            printer_name = win32print.GetDefaultPrinter()
            return self.print_to_windows_printer(printer_name)
        except Exception:
            return self._fallback_qprinter()
