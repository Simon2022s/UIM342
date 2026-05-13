# ////////////////////////////////////////////////////////////////////////////
# MIT License
#
# Copyright (c) [2022] UIROBOT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Disclaimer: UIROBOT shall not be held responsible for any direct or indirect
# consequences resulting from the misuse of this software, including but not
# limited to damages caused by unauthorized purchases, improper configurations,
# or unintended usage. Users are solely responsible for ensuring the proper and
# safe application of this software in their respective environments.
# ////////////////////////////////////////////////////////////////////////////

"""
Utility functions for data conversion and CRC calculation
"""

from typing import List
from constants import FRAME_HEAD, FRAME_TAIL, FIXED_DATA_FIELD_LENGTH


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'   # Green for sent messages
    BLUE = '\033[94m'    # Blue for received messages
    RED = '\033[91m'     # Red for errors
    YELLOW = '\033[93m'  # Yellow for warnings
    MAGENTA = '\033[95m' # Magenta/Purple for real-time notification messages
    RESET = '\033[0m'    # Reset to default color
    BOLD = '\033[1m'     # Bold text
    
    @staticmethod
    def green(text: str) -> str:
        """Return text in green color"""
        return f"{Colors.GREEN}{text}{Colors.RESET}"
    
    @staticmethod
    def blue(text: str) -> str:
        """Return text in blue color"""
        return f"{Colors.BLUE}{text}{Colors.RESET}"
    
    @staticmethod
    def red(text: str) -> str:
        """Return text in red color"""
        return f"{Colors.RED}{text}{Colors.RESET}"
    
    @staticmethod
    def yellow(text: str) -> str:
        """Return text in yellow color"""
        return f"{Colors.YELLOW}{text}{Colors.RESET}"
    
    @staticmethod
    def purple(text: str) -> str:
        """Return text in purple/magenta color"""
        return f"{Colors.MAGENTA}{text}{Colors.RESET}"

def bytes_to_hex_string(data: bytes) -> str:
    """Convert bytes data to hexadecimal string display"""
    return ' '.join([f'{b:02X}' for b in data])


def hex_string_to_bytes(hex_str: str) -> bytes:
    """Convert hexadecimal string to bytes data"""
    # Remove spaces and separators
    hex_str = hex_str.replace(' ', '').replace('-', '').replace(':', '')
    return bytes.fromhex(hex_str)


def int32_to_bytes(value: int) -> List[int]:
    """
    Convert 32-bit unsigned integer to 4-byte list (little-endian)
    
    Args:
        value: 32-bit unsigned integer (0 to 4294967295)
        
    Returns:
        List of 4 bytes [d0, d1, d2, d3] in little-endian format
        
    Raises:
        ValueError: If value is out of range
    """
    if not (0 <= value <= 0xFFFFFFFF):
        raise ValueError(f"Value must be 0-4294967295, got {value}")
    
    d0 = value & 0xFF
    d1 = (value >> 8) & 0xFF
    d2 = (value >> 16) & 0xFF
    d3 = (value >> 24) & 0xFF
    
    return [d0, d1, d2, d3]


def int32_signed_to_bytes(value: int) -> List[int]:
    """
    Convert 32-bit signed integer to 4-byte list (little-endian)
    
    Args:
        value: 32-bit signed integer (-2147483648 to 2147483647)
        
    Returns:
        List of 4 bytes [d0, d1, d2, d3] in little-endian format
        
    Raises:
        ValueError: If value is out of range
    """
    if not (-2147483648 <= value <= 2147483647):
        raise ValueError(f"Value must be -2147483648 to 2147483647, got {value}")
    
    # Convert to unsigned 32-bit representation
    if value < 0:
        unsigned_value = (1 << 32) + value  # Two's complement
    else:
        unsigned_value = value
    
    return int32_to_bytes(unsigned_value)


def bytes_to_int32(data_bytes: List[int], offset: int = 0) -> int:
    """
    Convert 4 bytes (little-endian) to 32-bit unsigned integer
    
    Args:
        data_bytes: List of bytes
        offset: Starting offset in the list (default: 0)
        
    Returns:
        32-bit unsigned integer (0 to 4294967295)
        
    Raises:
        ValueError: If not enough bytes available
    """
    if len(data_bytes) < offset + 4:
        raise ValueError(f"Need at least {offset + 4} bytes, got {len(data_bytes)}")
    
    d0 = data_bytes[offset]
    d1 = data_bytes[offset + 1]
    d2 = data_bytes[offset + 2]
    d3 = data_bytes[offset + 3]
    
    return d0 + (d1 << 8) + (d2 << 16) + (d3 << 24)


def bytes_to_int32_signed(data_bytes: List[int], offset: int = 0) -> int:
    """
    Convert 4 bytes (little-endian) to 32-bit signed integer
    
    Args:
        data_bytes: List of bytes
        offset: Starting offset in the list (default: 0)
        
    Returns:
        32-bit signed integer (-2147483648 to 2147483647)
        
    Raises:
        ValueError: If not enough bytes available
    """
    unsigned_value = bytes_to_int32(data_bytes, offset)
    
    # Convert from unsigned to signed (two's complement)
    if unsigned_value >= 0x80000000:  # If MSB is set (negative number)
        return unsigned_value - (1 << 32)
    else:
        return unsigned_value


def bytes_to_int24(data_bytes: List[int], offset: int = 0) -> int:
    """
    Convert 3 bytes (little-endian) to 24-bit unsigned integer
    
    Args:
        data_bytes: List of bytes
        offset: Starting offset in the list (default: 0)
        
    Returns:
        24-bit unsigned integer (0 to 16777215)
        
    Raises:
        ValueError: If not enough bytes available
    """
    if len(data_bytes) < offset + 3:
        raise ValueError(f"Need at least {offset + 3} bytes, got {len(data_bytes)}")
    
    d0 = data_bytes[offset]
    d1 = data_bytes[offset + 1]
    d2 = data_bytes[offset + 2]
    
    return d0 + (d1 << 8) + (d2 << 16)


def rtu_crc16(data: bytes) -> bytes:
    """
    Calculate RTU CRC16 checksum
    
    Args:
        data: Input data bytes
        
    Returns:
        2-byte CRC checksum (little-endian: [CRC_LOW, CRC_HIGH])
    """
    crc = 0xFFFF
    
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    
    # Return as little-endian bytes
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    return bytes([crc_low, crc_high])


def build_command_frame(station_id: int, control_word: int, date_len: int, data_bytes: List[int]) -> bytes:
    """
    Build command frame with structure: AA ID CW DL d0 d1 d2 d3 d4 d5 d6 d7 d8 R0 R1 CC
    
    Args:
        station_id: Station ID (0-255)
        control_word: Control word (0-255)
        date_len: Data length (0-9)
        data_bytes: Data bytes list (length should match date_len)
        
    Returns:
        Complete 16-byte command frame
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Validate parameters
    if not (0 <= station_id <= 255):
        raise ValueError(f"Station ID must be 0-255, got {station_id}")
    if not (0 <= control_word <= 255):
        raise ValueError(f"Control word must be 0-255, got {control_word}")
    if not (0 <= date_len <= FIXED_DATA_FIELD_LENGTH):
        raise ValueError(f"Data length must be 0-{FIXED_DATA_FIELD_LENGTH}, got {date_len}")
    if len(data_bytes) != date_len:
        raise ValueError(f"Data bytes length ({len(data_bytes)}) doesn't match date_len ({date_len})")
    
    # Build frame without CRC first
    frame = bytearray()
    frame.append(FRAME_HEAD)  # AA
    frame.append(station_id)  # ID
    frame.append(control_word)  # CW
    frame.append(date_len)  # DL
    
    # Add data bytes (d0~d8), pad with 0x00 if needed
    for i in range(FIXED_DATA_FIELD_LENGTH):
        if i < len(data_bytes):
            frame.append(data_bytes[i])
        else:
            frame.append(0x00)  # Padding
    
    # Calculate CRC for ID + CW + DL + d0~d8 (12 bytes)
    crc_data = frame[1:13]  # Skip frame header (AA)
    crc_bytes = rtu_crc16(bytes(crc_data))
    
    # Add CRC (R0 R1)
    frame.extend(crc_bytes)
    
    # Add frame tail
    frame.append(FRAME_TAIL)  # CC
    
    return bytes(frame)