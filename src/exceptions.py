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
Custom exceptions for SDK communication errors
"""

from typing import List


class SDKCommunicationError(Exception):
    """Base exception for SDK communication errors"""
    pass


class NoResponseError(SDKCommunicationError):
    """Raised when no response is received from device"""
    def __init__(self, function_name: str):
        self.function_name = function_name
        super().__init__(f"{function_name} failed - No response received")


class NoStationsError(SDKCommunicationError):
    """Raised when no stations responded"""
    def __init__(self, function_name: str):
        self.function_name = function_name
        super().__init__(f"{function_name} failed - No stations responded")


class NoDeviceStationsError(SDKCommunicationError):
    """Raised when no device stations are available (only gateway or none)"""
    def __init__(self, has_gateway: bool = False):
        self.has_gateway = has_gateway
        if has_gateway:
            super().__init__("Gateway is online, but no other device stations are online")
        else:
            super().__init__("No device stations responded")


class TargetStationNotFoundError(SDKCommunicationError):
    """Raised when target station ID is not found in available stations"""
    def __init__(self, target_station_id: int, available_station_ids: List[int], has_gateway: bool = False):
        self.target_station_id = target_station_id
        self.available_station_ids = available_station_ids
        self.has_gateway = has_gateway
        super().__init__(
            f"Target Station ID {target_station_id} (0x{target_station_id:02X}) is not found in available device stations"
        )
