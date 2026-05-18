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
Serial protocol handling and frame processing
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from constants import (
    FRAME_HEAD, FRAME_TAIL, FRAME_LENGTH,
    FIXED_DATA_FIELD_LENGTH, EXPECTED_FRAME_LENGTH
)
import constants
from utils import rtu_crc16, bytes_to_hex_string, Colors
from parsers import parse_control_word


class SerialProtocol(asyncio.Protocol):
    """Serial communication protocol handler"""
    
    def __init__(self, expected_data: bytes) -> None:
        self.transport: Optional[asyncio.Transport] = None
        self.expected_data: bytes = expected_data
        self.received_data: bytearray = bytearray()
        self.response_queue: asyncio.Queue = asyncio.Queue()
        self.active_message_queue: asyncio.Queue = asyncio.Queue()  # For real-time notifications
        self.connection_lost_event: asyncio.Event = asyncio.Event()
    
    def connection_made(self, transport: asyncio.Transport) -> None:
        """Called when connection is established"""
        self.transport = transport
        print(f"OK Serial connection established")
    
    def data_received(self, data: bytes) -> None:
        """
        Called when data is received from the serial port.
        
        This method handles incoming data by:
        1. Accumulating received bytes into the buffer
        2. Extracting complete frames from the buffer (handles packet sticking)
        3. Routing each frame to either the response queue or active message queue
           based on whether it's a command response or a real-time notification
        
        Frame Routing Logic:
        - Real-time notifications: Messages sent by the device without a command request.
          These are identified by the control word's real-time notification flag.
          They are routed to active_message_queue for asynchronous processing.
        - Command responses: Responses to commands we sent. These are routed to
          response_queue to be matched with the corresponding command request.
        
        Args:
            data: Raw bytes received from the serial port (may be partial or multiple frames)
        """
        # Accumulate received data into buffer (handles partial frames)
        self.received_data.extend(data)
        
        # Extract complete frames from buffer (handles packet sticking - multiple frames in one packet)
        complete_frames = extract_complete_frames(self.received_data)
        
        # Process each complete frame
        for frame in complete_frames:
            # Determine if this frame is a response to our command or an active message
            try:
                # Parse the frame to extract control word information
                parsed = parse_response_frame(frame)
                control_word_info = parsed.get('control_word_info', {})
                
                # Real-time notifications are active messages (not responses to commands)
                # These are sent by the device autonomously (e.g., motion completion notifications)
                if control_word_info.get('is_real_time_notification', False):
                    # This is a real-time notification message - route to active message queue
                    # These will be processed by the handle_active_messages() background task
                    self.active_message_queue.put_nowait(frame)
                else:
                    # This is a response to a command we sent - route to response queue
                    # These will be matched with the corresponding SDK function call
                    self.response_queue.put_nowait(frame)
            except Exception as e:
                # If parsing fails, treat as response (safer default)
                # This ensures we don't lose frames even if parsing has issues
                print(f"WARNING Warning: Failed to parse frame for routing: {e}")
                self.response_queue.put_nowait(frame)
    
    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Called when connection is lost"""
        print(f"FAIL Serial connection lost: {exc}")
        self.connection_lost_event.set()


def extract_complete_frames(buffer: bytearray) -> List[bytes]:
    """
    Extract complete frames from buffer (handle packet sticking).
    
    This function handles the common serial communication issue where multiple frames
    may arrive in a single packet, or a frame may be split across multiple packets.
    
    Frame format: AA ID CW DL d0 d1 d2 d3 d4 d5 d6 d7 d8 R0 R1 CC (16 bytes)
    - Frame starts with 0xAA (FRAME_HEAD)
    - Frame ends with 0xCC (FRAME_TAIL)
    - Fixed length: 16 bytes (FRAME_LENGTH)
    
    Algorithm:
    1. Scan buffer byte-by-byte looking for frame header (0xAA)
    2. When header found, check if we have enough bytes for a complete frame
    3. Verify frame tail (0xCC) is at the expected position
    4. Extract complete frame and continue searching for more frames
    5. Remove processed frames from buffer, leaving incomplete data for next call
    
    This handles:
    - Packet sticking: Multiple frames in one packet (e.g., "AA...CCAA...CC")
    - Partial frames: Incomplete frame at end of buffer (e.g., "AA...")
    - Invalid data: Bytes that don't match frame format are skipped
    
    Args:
        buffer: Received data buffer (may contain multiple frames or incomplete frames).
               This buffer is modified in-place - processed frames are removed.
        
    Returns:
        List of complete frame bytes. Remaining incomplete data stays in buffer
        for processing when more data arrives.
    """
    complete_frames = []
    
    # Scan buffer byte-by-byte to find all complete frames
    i = 0
    while i < len(buffer):
        # Look for frame header (0xAA) - start of a potential frame
        if buffer[i] == FRAME_HEAD:
            # Check if we have enough bytes for a complete frame
            # Need at least FRAME_LENGTH bytes starting from position i
            if i + FRAME_LENGTH <= len(buffer):
                # Verify frame tail (0xCC) is at the expected position
                # This confirms we have a complete, valid frame
                if buffer[i + FRAME_LENGTH - 1] == FRAME_TAIL:
                    # Extract complete frame as immutable bytes
                    frame = bytes(buffer[i:i + FRAME_LENGTH])
                    complete_frames.append(frame)
                    # Move past this frame to continue searching
                    i += FRAME_LENGTH
                else:
                    # Frame tail doesn't match - this wasn't a valid frame header
                    # Skip this byte and continue searching (might be data byte that happens to be 0xAA)
                    i += 1
            else:
                # Not enough bytes for a complete frame - wait for more data
                # The incomplete frame data remains in buffer for next call
                break
        else:
            # Not a frame header - skip this byte and continue searching
            i += 1
    
    # Remove processed frames from buffer to prevent reprocessing
    # This leaves any incomplete frame data at the end for next data_received() call
    if complete_frames:
        total_processed = len(complete_frames) * FRAME_LENGTH
        del buffer[:total_processed]
    
    return complete_frames


def parse_response_frame(frame_data: bytes) -> Dict[str, Any]:
    """
    Parse received response frame according to the protocol specification.
    
    Frame format: AA ID CW DL d0 d1 d2 d3 d4 d5 d6 d7 d8 R0 R1 CC
    Byte positions:
    - [0]:     Frame header (0xAA)
    - [1]:     Station ID (0-255)
    - [2]:     Control Word (command/response type)
    - [3]:     Data Length (0-9, actual number of data bytes used)
    - [4-12]:  Data field (d0~d8, 9 bytes fixed, but only first data_len bytes are valid)
    - [13-14]: CRC checksum (R0 R1, 2 bytes)
    - [15]:    Frame tail (0xCC)
    
    CRC Calculation:
    - CRC is calculated over bytes [1:13] (ID + CW + DL + d0~d8, total 12 bytes)
    - Uses RTU CRC-16 algorithm (Modbus standard)
    - Received CRC is compared with calculated CRC to verify data integrity
    
    Data Field Handling:
    - The data field is always 9 bytes (d0~d8) in the frame
    - However, only the first 'data_len' bytes contain actual data
    - Remaining bytes (data_len to 8) are padding/ignored
    
    Args:
        frame_data: Complete frame data received (must be exactly 16 bytes)
        
    Returns:
        Dictionary containing parsed results with the following fields:
        - station_id: Station ID (0-255)
        - control_word: Control word (raw byte value)
        - control_word_info: Parsed control word information (command name, description, flags)
        - data_len: Data length (0-9, number of valid data bytes)
        - data_bytes: Data bytes list (only first data_len bytes, truncated from d0~d8)
        - crc_valid: Whether CRC check is valid (True if received CRC matches calculated CRC)
        
    Raises:
        ValueError: If frame format is incorrect (wrong length, invalid header/tail)
    """
    # Validate frame length
    if len(frame_data) < EXPECTED_FRAME_LENGTH:
        raise ValueError(f"Frame too short: expected at least {EXPECTED_FRAME_LENGTH} bytes, got {len(frame_data)}")
    
    # Validate frame header (must be 0xAA)
    if frame_data[0] != FRAME_HEAD:
        raise ValueError(f"Invalid frame header: expected 0x{FRAME_HEAD:02X}, got 0x{frame_data[0]:02X}")
    
    # Validate frame tail (must be 0xCC)
    if frame_data[-1] != FRAME_TAIL:
        raise ValueError(f"Invalid frame tail: expected 0x{FRAME_TAIL:02X}, got 0x{frame_data[-1]:02X}")
    
    # Extract frame fields according to protocol specification
    station_id = frame_data[1]        # Byte 1: Station ID
    control_word = frame_data[2]      # Byte 2: Control Word
    data_len = frame_data[3]          # Byte 3: Data Length (0-9)
    data_bytes = list(frame_data[4:4+FIXED_DATA_FIELD_LENGTH])  # Bytes 4-12: d0~d8 (9 bytes)
    received_crc = frame_data[13:15]  # Bytes 13-14: R0 R1 (2 bytes CRC)
    
    # Verify CRC checksum for data integrity
    # CRC is calculated over: ID + CW + DL + d0~d8 (12 bytes total: bytes 1-12)
    crc_data = frame_data[1:13]  # Extract bytes for CRC calculation
    calculated_crc = rtu_crc16(bytes(crc_data))  # Calculate CRC using RTU CRC-16 algorithm
    crc_valid = (received_crc == calculated_crc)  # Compare received vs calculated CRC
    
    # Truncate actual data according to data_len
    # Only the first 'data_len' bytes are valid; remaining bytes are padding
    actual_data_bytes = data_bytes[:data_len] if data_len > 0 else []
    
    # Parse Control Word to extract command information
    # This provides human-readable command name, description, and flags
    control_word_info = parse_control_word(control_word)
    
    # Build result dictionary with all parsed information
    result = {
        'station_id': station_id,
        'control_word': control_word,
        'control_word_info': control_word_info,  # Parsed Control Word information
        'data_len': data_len,
        'data_bytes': actual_data_bytes,  # Only valid data bytes (truncated)
        'crc_valid': crc_valid
    }
    
    return result


def _print_parsed_response(parsed: Optional[Dict[str, Any]], is_timeout: bool = False) -> None:
    """Print parsed response frame information"""
    if not constants.PRINT_MESSAGES:
        return

    if parsed is None:
        if is_timeout:
            print(Colors.red("FAIL Timeout - No response received"))
        else:
            print(Colors.red("FAIL No response received"))
        return

    # Print basic frame information
    cw_info = parsed['control_word_info']
    cw_name = cw_info['command_name']
    cw_desc = cw_info['command_description']

    print(Colors.blue("Parsed Response Frame:"))
    print("-" * 60)
    # First line: Station ID and Control Word
    print(Colors.blue(f"Station ID: 0x{parsed['station_id']:02X} ({parsed['station_id']}) | Control Word: 0x{parsed['control_word']:02X} ({parsed['control_word']}) - {cw_name} ({cw_desc})"))
    # Second line: Data Length, Data Bytes (if any), and CRC Valid
    data_info = f"Data Length: {parsed['data_len']}"
    if parsed['data_len'] > 0:
        data_info += f" | Data Bytes: {bytes_to_hex_string(bytes(parsed['data_bytes']))} ({parsed['data_bytes']})"
    data_info += f" | CRC Valid: {'OK Yes' if parsed['crc_valid'] else 'FAIL No'}"
    print(Colors.blue(data_info))
    print("-" * 60)


def _process_received_data(received_data: bytes, send_time: float, is_timeout: bool = False) -> Optional[Dict[str, Any]]:
    """Process received data and return parsed response"""
    if not received_data:
        return None

    receive_time = time.perf_counter()
    response_time_ms = (receive_time - send_time) * 1000

    if constants.PRINT_MESSAGES:
        print(Colors.blue(f"OK Response received after {response_time_ms:.2f} ms"))
        print(Colors.blue(f"Hexadecimal: {bytes_to_hex_string(received_data)}"))

    try:
        parsed = parse_response_frame(received_data)
        _print_parsed_response(parsed, is_timeout)
        return parsed
    except ValueError as e:
        if constants.PRINT_MESSAGES:
            print(Colors.red(f"FAIL Failed to parse response: {e}"))
        return None