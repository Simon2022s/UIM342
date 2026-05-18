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
Mock serial protocol for demonstration without hardware dependency
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
import constants
from utils import Colors


class MockSerialProtocol:
    """Mock serial protocol for demonstration purposes"""

    def __init__(self):
        self.response_queue = asyncio.Queue()
        self.active_message_queue = asyncio.Queue()
        self.is_connected = False

    async def connect(self, port: str, baudrate: int = 57600) -> bool:
        """Mock connection"""
        print(Colors.green(f"Mock serial connection established to {port}"))
        self.is_connected = True
        return True

    def write(self, data: bytes) -> None:
        """Mock write - simulate sending command and receiving response"""
        if not self.is_connected:
            raise RuntimeError("Not connected")

        # Simulate response after a short delay
        asyncio.create_task(self._simulate_response(data))

    async def _simulate_response(self, command_data: bytes) -> None:
        """Simulate device response"""
        # Extract station ID and control word from command
        if len(command_data) >= 4:
            station_id = command_data[1]
            control_word = command_data[2] & 0x7F  # Remove request flag

            # Simulate response delay
            await asyncio.sleep(0.05)

            # Create mock response based on control word
            response = self._create_mock_response(station_id, control_word)
            if response:
                await self.response_queue.put(response)

    def _create_mock_response(self, station_id: int, control_word: int) -> Optional[bytes]:
        """Create mock response based on control word"""
        # Mock response frame: AA ID CW DL data... CRC CC
        response = bytearray([0xAA, station_id, control_word, 0])  # Basic frame

        # Add mock data based on command
        if control_word == 0x0B:  # Get Model (__ML)
            response[2] = control_word  # Response control word
            response[3] = 8  # Data length
            response.extend([0x22, 0x14, 0x1A, 0x03, 0xCA, 0x09, 0x9B, 0x01])  # Mock model data
        elif control_word == 0x16:  # Begin Motion (__BG)
            response[2] = control_word
            response[3] = 4
            response.extend([0x00, 0x00, 0x00, 0x00])
        elif control_word == 0x20:  # Position Absolute (__PA)
            response[2] = 0x2E  # Desire Value response
            response[3] = 5
            response.extend([0x04, 0x00, 0x00, 0x00, 0x00])
        elif control_word == 0x1D:  # Jog Velocity (__JV)
            response[2] = 0x2E  # Desire Value response
            response[3] = 5
            response.extend([0x02, 0x00, 0x00, 0x00, 0x00])
        else:
            # Generic success response
            response[2] = control_word
            response[3] = 1
            response.extend([0x01])  # Success

        # Add mock CRC
        response.extend([0x00, 0x00])
        # Add frame tail
        response.extend([0xCC])

        return bytes(response)

    def close(self) -> None:
        """Mock close connection"""
        self.is_connected = False
        print(Colors.yellow("Mock serial connection closed"))


class MockSDKClient:
    """Mock SDK client for demonstration"""

    def __init__(self):
        self.protocol = MockSerialProtocol()
        self.connected = False

    async def connect(self, port: str, baudrate: int = 57600) -> bool:
        """Connect to mock device"""
        self.connected = await self.protocol.connect(port, baudrate)
        return self.connected

    async def send_command(self, data: bytes, description: str) -> Dict[str, Any]:
        """Send command and wait for response"""
        if not self.connected:
            raise RuntimeError("Not connected to device")

        print(f"\n{Colors.green(description)}")
        print(f"{Colors.green('Mock Command:')} {data.hex().upper()}")

        # Send command
        self.protocol.write(data)

        # Wait for response
        try:
            response = await asyncio.wait_for(self.protocol.response_queue.get(), timeout=1.0)
            print(f"{Colors.blue('Mock Response:')} {response.hex().upper()}")

            return {
                'success': True,
                'station_id': response[1] if len(response) > 1 else 0,
                'control_word': response[2] if len(response) > 2 else 0,
                'data_len': response[3] if len(response) > 3 else 0,
                'data_bytes': list(response[4:4+response[3]]) if len(response) > 4 else [],
                'crc_valid': True,
                'response_data': response
            }
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'Timeout waiting for response'}

    def close(self) -> None:
        """Close connection"""
        self.protocol.close()
        self.connected = False


# Global mock client instance
_mock_sdk_client: Optional[MockSDKClient] = None


def get_mock_sdk_client() -> MockSDKClient:
    """Get or create mock SDK client"""
    global _mock_sdk_client
    if _mock_sdk_client is None:
        _mock_sdk_client = MockSDKClient()
    return _mock_sdk_client


async def mock_execute_string_commands(command_string: str, station_id: int = 5) -> List[Dict[str, Any]]:
    """
    Mock version of string command execution for demonstration
    """
    from string_commands import StringCommandParser
    from utils import build_command_frame

    client = get_mock_sdk_client()

    # Ensure client is connected
    if not client.connected:
        await client.connect("COM4_MOCK", 57600)

    parser = StringCommandParser()

    # Parse commands
    commands = parser.parse_commands(command_string)
    if not commands:
        print(Colors.yellow("WARNING No valid commands found"))
        return []

    print(Colors.green(f"\nExecuting {len(commands)} mock commands on Station {station_id}:"))
    print(Colors.green(f"Commands: {command_string}"))

    results = []

    for i, cmd_info in enumerate(commands, 1):
        cmd_name = cmd_info['command']
        param = cmd_info['parameter']

        print(f"\n{i}. Mock Executing: {cmd_info['original']}")

        try:
            # Build mock command frame based on command
            control_word_map = {
                'BG': 0x16 | 0x80,  # __BG
                'ML': 0x0B | 0x80,  # __ML
                'PA': 0x20 | 0x80,  # __PA
                'JV': 0x1D | 0x80,  # __JV
                'SP': 0x1E | 0x80,  # __SP
                'MO': 0x15 | 0x80,  # __MO
                'ST': 0x17 | 0x80,  # __ST
                'OG': 0x21 | 0x80,  # __OG
            }

            if cmd_name in control_word_map:
                control_word = control_word_map[cmd_name]

                # Build data bytes based on command and parameter
                data_bytes = []
                if param is not None:
                    if cmd_name in ['PA', 'JV', 'SP']:
                        # 32-bit signed integer
                        from utils import int32_signed_to_bytes
                        data_bytes = int32_signed_to_bytes(param)
                    elif cmd_name == 'MO':
                        # Single byte
                        data_bytes = [param]

                # Build command frame
                frame = build_command_frame(station_id, control_word, len(data_bytes), data_bytes)

                # Send mock command
                result = await client.send_command(frame, f"Mock {cmd_name} Command")

                results.append({
                    'command': cmd_name,
                    'parameter': param,
                    'success': result['success'],
                    'result': result
                })

                if result['success']:
                    print(Colors.green(f"   OK {cmd_name} executed successfully"))
                else:
                    print(Colors.red(f"   X {cmd_name} failed: {result.get('error', 'Unknown error')}"))
            else:
                # Command not implemented in mock
                print(Colors.yellow(f"   WARNING {cmd_name} not implemented in mock (skipped)"))
                results.append({
                    'command': cmd_name,
                    'parameter': param,
                    'success': True,
                    'result': {'mock': True, 'message': 'Not implemented in mock'}
                })

        except Exception as e:
            error_msg = f"X {cmd_name} failed: {e}"
            print(Colors.red(f"   {error_msg}"))

            results.append({
                'command': cmd_name,
                'parameter': param,
                'success': False,
                'error': str(e)
            })

    return results