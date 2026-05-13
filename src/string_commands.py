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
String-based command parser and executor for motor control
Supports commands like: BG;ML;PA60000;JV1000;
"""

import asyncio
import re
from typing import Optional, List, Dict, Any, Union
from constants import (
    __ER, __ML, __MT, __MO, __BG, __ST, __JV, __SP, __PR, __PA, __OG,
    __AC, __DC, __SS, __SD, __IC, __IE, __DV, __RT, __MS, __DI, __IL
)
import constants
from utils import Colors
from sdk_functions import (
    SdkSetBeginMxn, SdkGetML, SdkSetPtpMxnA, SdkSetJogMxn,
    SdkSetPtpMxnR, SdkSetPtpSPD, SdkSetMotorOn, SdkSetStopMxn,
    SdkSetOrigin, SdkGetMotionStatus, SdkGetDIOport, SdkGetInputLogic,
    SdkSetInputLogic, SdkGetMotorConfig, SdkSetMotorConfig,
    SdkGetInitialConfig, SdkGetAcceleration, SdkGetDeceleration,
    SdkGetCutInSpeed, SdkGetStopDeceleration, SdkGetPtpMxnA
)


class StringCommandParser:
    """
    Parser for string-based motor control commands
    Supports format: CMD1;CMD2;CMD3; (semicolon-separated)
    """

    def __init__(self):
        # Command mapping from string to SDK function and parameters
        self.command_map = {
            'BG': self._cmd_bg,           # Begin Motion
            'ML': self._cmd_ml,           # Get Model
            'PA': self._cmd_pa,           # Position Absolute
            'PR': self._cmd_pr,           # Position Relative
            'JV': self._cmd_jv,           # Jog Velocity
            'SP': self._cmd_sp,           # Speed
            'MO': self._cmd_mo,           # Motor On/Off
            'ST': self._cmd_st,           # Stop Motion
            'OG': self._cmd_og,           # Origin
            'MS': self._cmd_ms,           # Motion Status
            'DI': self._cmd_di,           # Digital I/O
            'IL': self._cmd_il,           # Input Logic
            'MT': self._cmd_mt,           # Motor Config
            'IC': self._cmd_ic,           # Initial Config
            'AC': self._cmd_ac,           # Acceleration
            'DC': self._cmd_dc,           # Deceleration
            'SS': self._cmd_ss,           # Start Speed
            'SD': self._cmd_sd,           # Stop Deceleration
        }

        # Station ID for commands (will be set when executing)
        self.station_id = 5  # Default station ID

    def parse_commands(self, command_string: str) -> List[Dict[str, Any]]:
        """
        Parse semicolon-separated command string into executable commands

        Args:
            command_string: String like "BG;ML;PA60000;JV1000;"

        Returns:
            List of parsed command dictionaries
        """
        commands = []

        # Split by semicolon and filter out empty strings
        cmd_parts = [part.strip() for part in command_string.split(';') if part.strip()]

        for cmd_part in cmd_parts:
            if not cmd_part:
                continue

            # Parse command and parameters
            cmd_info = self._parse_single_command(cmd_part)
            if cmd_info:
                commands.append(cmd_info)

        return commands

    def _parse_single_command(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single command with optional parameters

        Args:
            command: Single command like "BG", "PA60000", "JV1000"

        Returns:
            Parsed command dictionary or None if invalid
        """
        if not command:
            return None

        # Extract command name (letters) and parameters (numbers)
        match = re.match(r'^([A-Z]+)(-?\d*)$', command.upper())
        if not match:
            print(Colors.red(f"✗ Invalid command format: {command}"))
            return None

        cmd_name = match.group(1)
        param_str = match.group(2)

        # Convert parameter to integer if present
        param = None
        if param_str:
            try:
                param = int(param_str)
            except ValueError:
                print(Colors.red(f"✗ Invalid parameter for {cmd_name}: {param_str}"))
                return None

        # Check if command is supported
        if cmd_name not in self.command_map:
            print(Colors.red(f"✗ Unsupported command: {cmd_name}"))
            return None

        return {
            'command': cmd_name,
            'parameter': param,
            'original': command
        }

    async def execute_commands(self, command_string: str, station_id: int = 5) -> List[Dict[str, Any]]:
        """
        Execute a string of semicolon-separated commands

        Args:
            command_string: String like "BG;ML;PA60000;JV1000;"
            station_id: Station ID to execute commands on

        Returns:
            List of execution results
        """
        self.station_id = station_id

        # Parse commands
        commands = self.parse_commands(command_string)
        if not commands:
            print(Colors.yellow("⚠ No valid commands found"))
            return []

        print(Colors.green(f"\nExecuting {len(commands)} commands on Station {station_id}:"))
        print(Colors.green(f"Commands: {command_string}"))

        results = []

        # Execute each command
        for i, cmd_info in enumerate(commands, 1):
            cmd_name = cmd_info['command']
            param = cmd_info['parameter']

            print(f"\n{i}. Executing: {cmd_info['original']}")

            try:
                # Get the command function
                cmd_func = self.command_map[cmd_name]

                # Execute the command
                result = await cmd_func(param)

                results.append({
                    'command': cmd_name,
                    'parameter': param,
                    'success': True,
                    'result': result
                })

                print(Colors.green(f"   ✓ {cmd_name} executed successfully"))

            except Exception as e:
                error_msg = f"✗ {cmd_name} failed: {e}"
                print(Colors.red(f"   {error_msg}"))

                results.append({
                    'command': cmd_name,
                    'parameter': param,
                    'success': False,
                    'error': str(e)
                })

        return results

    # Individual command implementations

    async def _cmd_bg(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Begin Motion"""
        return await SdkSetBeginMxn(self.station_id)

    async def _cmd_ml(self, param: Optional[int]) -> Union[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
        """Get Model"""
        if self.station_id == 0:
            # Broadcast to all stations
            return await SdkGetML(0)
        else:
            return await SdkGetML(self.station_id)

    async def _cmd_pa(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Position Absolute"""
        if param is None:
            # Get current absolute position
            return await SdkGetPtpMxnA(self.station_id)
        else:
            # Set absolute position
            return await SdkSetPtpMxnA(self.station_id, param)

    async def _cmd_pr(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Position Relative"""
        if param is None:
            raise ValueError("PR command requires a parameter")
        return await SdkSetPtpMxnR(self.station_id, param)

    async def _cmd_jv(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Jog Velocity"""
        if param is None:
            raise ValueError("JV command requires a parameter")
        return await SdkSetJogMxn(self.station_id, param)

    async def _cmd_sp(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Speed"""
        if param is None:
            raise ValueError("SP command requires a parameter")
        return await SdkSetPtpSPD(self.station_id, param)

    async def _cmd_mo(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Motor On/Off"""
        if param is None:
            raise ValueError("MO command requires a parameter (0=OFF, 1=ON)")
        return await SdkSetMotorOn(self.station_id, param)

    async def _cmd_st(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Stop Motion"""
        return await SdkSetStopMxn(self.station_id)

    async def _cmd_og(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Origin"""
        return await SdkSetOrigin(self.station_id)

    async def _cmd_ms(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Motion Status"""
        index = param if param is not None else 0
        return await SdkGetMotionStatus(self.station_id, index)

    async def _cmd_di(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Digital I/O"""
        return await SdkGetDIOport(self.station_id)

    async def _cmd_il(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Input Logic"""
        index = param if param is not None else 0
        return await SdkGetInputLogic(self.station_id, index)

    async def _cmd_mt(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Motor Config"""
        index = param if param is not None else 0
        return await SdkGetMotorConfig(self.station_id, index)

    async def _cmd_ic(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Initial Config"""
        index = param if param is not None else 0
        return await SdkGetInitialConfig(self.station_id, index)

    async def _cmd_ac(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Acceleration"""
        return await SdkGetAcceleration(self.station_id)

    async def _cmd_dc(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Deceleration"""
        return await SdkGetDeceleration(self.station_id)

    async def _cmd_ss(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Start Speed"""
        return await SdkGetCutInSpeed(self.station_id)

    async def _cmd_sd(self, param: Optional[int]) -> Optional[Dict[str, Any]]:
        """Stop Deceleration"""
        return await SdkGetStopDeceleration(self.station_id)


# Convenience function for easy use
async def execute_string_commands(command_string: str, station_id: int = 5) -> List[Dict[str, Any]]:
    """
    Execute string-based motor control commands

    Args:
        command_string: Semicolon-separated commands like "BG;ML;PA60000;JV1000;"
        station_id: Station ID to execute commands on (default: 5)

    Returns:
        List of execution results

    Example:
        results = await execute_string_commands("BG;ML;PA60000;JV1000;", station_id=5)
    """
    parser = StringCommandParser()
    return await parser.execute_commands(command_string, station_id)