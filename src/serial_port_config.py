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
Serial port configuration management functions.

This module provides functions for:
- Enumerating available serial ports
- Selecting and saving serial port configuration
- Loading saved port configuration
"""

import os
import json
import time
from typing import Optional, Dict, Any
from serial.tools import list_ports


def get_config_file_path() -> str:
    """
    Get the absolute path to the serial port configuration file.

    This function uses the script's location to determine the config file path,
    making it work correctly regardless of the current working directory.

    Returns:
        str: Absolute path to the config file
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root, then into config directory
    config_file = os.path.join(script_dir, '..', 'config', 'serial_port_config.json')
    return os.path.abspath(config_file)


def select_serial_port(use_saved: bool = False, auto_connect: bool = False) -> Optional[str]:
    """
    Enumerate and select serial port
    
    Args:
        use_saved: Whether to use saved port configuration
        auto_connect: Whether to auto-connect without user interaction
        
    Returns:
        Selected port name or None if cancelled
    """
    # Get available serial ports
    ports = list_ports.comports()
    
    if not ports:
        print("No serial ports found!")
        return None
    
    # Load saved configuration
    config_file: str = get_config_file_path()
    saved_config: Dict[str, Any] = {}

    if use_saved and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
        except (json.JSONDecodeError, IOError):
            saved_config = {}
    
    # If auto_connect is True and we have saved config, try to use it directly
    if auto_connect and saved_config.get('selected_index', 0) > 0:
        saved_index = saved_config['selected_index']
        if 1 <= saved_index <= len(ports):
            selected_port = ports[saved_index - 1].device
            print(f"Auto-connecting to saved port: {selected_port}")
            return selected_port
    
    # Display available ports
    print("\nAvailable serial ports:")
    print("-" * 60)
    for i, port in enumerate(ports, 1):
        marker = ""
        if saved_config.get('selected_index') == i:
            marker = " ← Previously selected"
        print(f"{i}. {port.device} - {port.description}{marker}")
    
    # Get user selection
    while True:
        try:
            if saved_config.get('selected_index', 0) > 0:
                default_choice = saved_config['selected_index']
                choice = input(f"\nSelect port (1-{len(ports)}, default: {default_choice}): ").strip()
                if not choice:
                    choice = str(default_choice)
            else:
                choice = input(f"\nSelect port (1-{len(ports)}): ").strip()
            
            if not choice:
                continue
                
            index = int(choice)
            if 1 <= index <= len(ports):
                selected_port = ports[index - 1].device
                
                # Save selection
                save_config: Dict[str, Any] = {
                    'selected_index': index,
                    'selected_port': selected_port,
                    'timestamp': time.time()
                }
                
                try:
                    with open(config_file, 'w') as f:
                        json.dump(save_config, f, indent=2)
                    print(f"OK Port selection saved to {config_file}")
                except IOError as e:
                    print(f"WARNING Warning: Could not save port selection: {e}")
                
                return selected_port
            else:
                print(f"Invalid selection. Please enter 1-{len(ports)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return None


def load_port_config() -> int:
    """
    Load saved port configuration and return selected index.
    
    Returns:
        int: Selected port index (1-based), or 0 if no saved config
    """
    config_file = get_config_file_path()

    if not os.path.exists(config_file):
        return 0
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config.get('selected_index', 0)
    except (json.JSONDecodeError, IOError):
        return 0
