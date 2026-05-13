#!/usr/bin/env python3
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
Demo version of main.py for testing string commands without hardware dependency
This version skips hardware connection and goes directly to interactive string command mode
"""

import asyncio
import sys
import os
from typing import Optional

# Import required modules
from utils import Colors
from mock_serial_protocol import mock_execute_string_commands


async def demo_string_command_mode():
    """
    Demo version that goes directly to interactive string command mode
    """
    print("=" * 60)
    print(Colors.yellow("UIM342 String Command Demo Mode"))
    print("=" * 60)
    print(Colors.blue("This is a demo version for testing string commands"))
    print(Colors.blue("No actual hardware connection required"))
    print("=" * 60)

    print("\n" + Colors.green("Demo system initialized"))
    print(Colors.green("Ready for string command testing"))

    # Demo station configuration
    station_id = 5
    print(f"\n{Colors.blue('Station Configuration:')}")
    print(f"  - Demo Station ID: {station_id}")
    print(f"  - Mock hardware: Connected")
    print(f"  - String commands: Ready")

    print("\n" + "=" * 60)
    print(Colors.yellow("Interactive String Command Mode"))
    print("=" * 60)
    print("Enter string commands like: BG;ML;PA60000;JV1000;")
    print("Type 'quit' to exit, 'help' for available commands")
    print("Type 'demo' to run a demo sequence")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nEnter commands: ").strip()

            if not user_input or user_input.lower() == 'quit':
                print(Colors.green("Exiting demo mode..."))
                break
            elif user_input.lower() == 'help':
                print_help()
                continue
            elif user_input.lower() == 'demo':
                await run_demo_sequence()
                continue

            # Execute the string commands with mock hardware
            results = await mock_execute_string_commands(user_input, station_id=station_id)

            # Show summary
            if results:
                success_count = sum(1 for r in results if r['success'])
                print(f"\nExecuted {len(results)} commands: {success_count} successful, {len(results) - success_count} failed")

        except (EOFError, KeyboardInterrupt):
            print("\n\nDemo mode interrupted.")
            break
        except Exception as e:
            print(f"\nX Error: {e}")

    print("\nDemo completed. Thank you!")


async def run_demo_sequence():
    """Run a demo sequence of commands"""
    print(f"\n{Colors.yellow('Running Demo Sequence...')}")

    demo_commands = [
        "MO1;PA60000;SP20000;BG;",    # Enable, set position and speed, start
        "JV10000;BG;",               # Jog motion
        "ST;MO0;",                   # Stop and disable
        "PA;ML;"                     # Query position and model
    ]

    for i, cmd_string in enumerate(demo_commands, 1):
        print(f"\n{i}. Demo: {cmd_string}")

        results = await mock_execute_string_commands(cmd_string, station_id=5)

        if results:
            success_count = sum(1 for r in results if r['success'])
            print(f"   {success_count}/{len(results)} commands successful")

        # Wait between sequences
        await asyncio.sleep(1)

    print(f"\nDemo sequence completed!")


def print_help():
    """Print available commands help"""
    print("\nAvailable commands:")
    print("  BG        - Begin Motion")
    print("  ML        - Get Model Information")
    print("  PA<pos>   - Set/Get Absolute Position (e.g., PA60000)")
    print("  PR<pos>   - Set Relative Position (e.g., PR1000)")
    print("  JV<speed> - Set Jog Velocity (e.g., JV10000)")
    print("  SP<speed> - Set Speed (e.g., SP20000)")
    print("  MO<0/1>   - Motor On/Off (e.g., MO1 for ON)")
    print("  ST        - Stop Motion (Emergency Stop)")
    print("  OG        - Set Origin")
    print("  MS<idx>   - Get Motion Status (e.g., MS0 or MS1)")
    print("  DI        - Get Digital I/O Status")
    print("  IL<idx>   - Get Input Logic (e.g., IL0)")
    print("  MT<idx>   - Get Motor Config (e.g., MT0)")
    print("  AC        - Get Acceleration")
    print("  DC        - Get Deceleration")
    print("  SS        - Get Start Speed")
    print("  SD        - Get Stop Deceleration")
    print("\nSpecial commands:")
    print("  demo      - Run demo sequence")
    print("  help      - Show this help")
    print("  quit      - Exit demo")
    print("\nExamples:")
    print("  MO1;PA60000;SP20000;BG;")
    print("  MO1;JV10000;BG;ST;MO0;")
    print("  PA;ML;MS0;DI;")


def main():
    """Main function for demo mode"""
    try:
        asyncio.run(demo_string_command_mode())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()