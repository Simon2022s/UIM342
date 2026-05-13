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
UIM2513 Gateway and UIM342 Motor Control Serial Communication Example
You can debug independently, view the console output messages, and understand the communication process of each command.
"""

"""
Station IDs will be automatically assigned based on detected device stations:
- If 1 motor is detected: STATION_ID_X = that motor's station ID
- If 2 motors are detected: STATION_ID_X = smaller station ID, STATION_ID_Y = larger station ID
"""
# Dual motor station IDs (will be auto-assigned after station detection)
STATION_ID_X: int = 0  # X-axis motor station ID (auto-assigned)
STATION_ID_Y: int = 0  # Y-axis motor station ID (auto-assigned)


import asyncio
import serial

# Try to import serial_asyncio, fallback to alternative if not available
try:
    import serial_asyncio
    HAS_SERIAL_ASYNCIO = True
except ImportError:
    # Fallback for environments where serial_asyncio is not available
    HAS_SERIAL_ASYNCIO = False
    print("Warning: serial_asyncio not available, using alternative approach")
import sys
from typing import Optional, List, Union, Callable, Dict, Any

# Import modules with explicit imports
from constants import (
    DEFAULT_BAUDRATE, DEFAULT_TIMEOUT,
    ICFG_AMO_IDX, ICFG_ACM_IDX,
    SCF_S1C_IDX,SCF_S2C_IDX,SCF_S3C_IDX,SCF_STL_IDX,
    MTS_BRK_IDX, MTS_MCS_IDX, MTS_CUR_IDX, MTS_PSV_IDX,
    RTCN_MXN_INP,
    RTCN_DIO_P1L, RTCN_DIO_P1H, RTCN_DIO_P2L, RTCN_DIO_P2H, RTCN_DIO_P3L, RTCN_DIO_P3H,
    DIO_PORT_CODE_MAP,
    GATEWAY_STATION_ID,
    INITIALIZATION_DELAY, ACTIVE_MESSAGE_QUEUE_TIMEOUT,
    DEFAULT_PTP_MOTION_TIMEOUT, DUAL_MOTOR_MOTION_TIMEOUT,
    DEFAULT_JOG_SPEED,
    DEFAULT_PTP_POSITION, DEFAULT_PTP_SPEED, DEFAULT_PTP_RELATIVE_POSITION,
    DEFAULT_PTP_SPEED_X, DEFAULT_PTP_SPEED_Y,
    WAIT_AFTER_ORIGIN, WAIT_BEFORE_STOP, WAIT_BEFORE_ESTOP,
    WAIT_BEFORE_ORIGIN, WAIT_AFTER_ORIGIN_SET,
    WAIT_BEFORE_DUAL_MOTOR, WAIT_AFTER_DUAL_MOTOR,
    ILC_NOP_IDX, ILC_OFF_IDX, ILC_EST_IDX, ILC_ODS_IDX, ILC_RPR_IDX, ILC_SPR_IDX, ILC_SPA_IDX, ILC_PVT_IDX,
    init_print_messages
)
import constants
from utils import bytes_to_hex_string, Colors
from parsers import parse_rtcn_d0_code
from protocol import SerialProtocol, parse_response_frame
from sdk_functions import (
    SDKClient, set_sdk_client, get_sdk_client,
    SdkGetML, SdkGetInitialConfig, SdkGetDIOport, SdkGetInputLogic, SdkSetInputLogic,
    SdkGetMotorConfig, SdkSetMotorConfig, SdkGetMotionStatus,
    SdkGetAcceleration, SdkGetDeceleration, SdkGetCutInSpeed, SdkGetStopDeceleration,
    SdkSetMotorOn, SdkSetJogMxn, SdkSetBeginMxn, SdkSetStopMxn, SdkSetOrigin,
    SdkSetPtpMxnA, SdkSetPtpMxnR, SdkSetPtpSPD, SdkGetPtpMxnA
)
from motor_control_helpers import (
    EventManager,
    wait_with_message,
    wait_for_ptp_motion_in_position,
    wait_for_s1_trigger,
    goto_home,
    execute_ptp_motion
)
from parsers import (
    execute_and_check_sdk,
    check_sdk_response,
    check_sdk_getml_response,
    get_device_station_ids
)
from serial_port_config import (
    get_config_file_path,
    select_serial_port,
    load_port_config
)

# ==============================================================================
# Custom Exceptions (imported from exceptions module)
# ==============================================================================

# Try to import string_commands for interactive mode
# This import is done at module level to catch any import errors early
try:
    # Ensure the current directory is in Python path for module import
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from string_commands import execute_string_commands
    STRING_COMMANDS_AVAILABLE = True
except Exception as e:
    # If import fails, we'll try again in interactive mode
    STRING_COMMANDS_AVAILABLE = False

from exceptions import (
    SDKCommunicationError,
    NoResponseError,
    NoStationsError,
    NoDeviceStationsError,
    TargetStationNotFoundError
)


async def serial_communication_async(
    port: str,
    baudrate: int = DEFAULT_BAUDRATE,
    timeout: float = DEFAULT_TIMEOUT,
    station_id: int = 0  # Will be set properly after auto-detection
) -> None:
    """
    Complete async serial communication with all test cases

    Args:
        port: Serial port name (required)
        baudrate: Baud rate (default: 57600)
        timeout: Read timeout in seconds (default: 1.0)
        station_id: Station address (default: 0x05)
    """

    # Declare global variables at the beginning of the function
    global STATION_ID_X, STATION_ID_Y
    print("=" * 60)
    print("Serial Communication Example - Complete Version (Refactored)")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"Baudrate: {baudrate}")
    print(f"Parameters: 8 data bits, No parity, 1 stop bit (8,N,1)")
    print("=" * 60)
    
    # Ask user to confirm before opening serial port
    print(f"\nReady to open serial port {port}")
    print("-" * 60)
    while True:
        try:
            choice = input(f"Use port {port}? [y/n] (default: y, press Enter to continue): ").strip().lower()
            if not choice or choice == 'y':
                break  # Continue with current port
            elif choice == 'n':
                # User wants to select a different port, raise exception to trigger reselection
                raise ValueError(f"User requested to change serial port from {port}")
            else:
                print("Invalid choice. Please enter y or n.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nOperation cancelled by user.")
            return  # Exit the async function gracefully
    
    # Initialize variables for cleanup
    transport: Optional[asyncio.Transport] = None
    active_message_task: Optional[asyncio.Task[None]] = None
    
    try:
        # Create protocol factory function
        protocol_instance: Optional[SerialProtocol] = None
        
        def protocol_factory() -> SerialProtocol:
            nonlocal protocol_instance
            protocol_instance = SerialProtocol(b'')
            return protocol_instance
        
        print(f"\nOpening serial port {port}...")

        if HAS_SERIAL_ASYNCIO:
            # Use serial_asyncio if available
            loop = asyncio.get_event_loop()
            transport, protocol = await serial_asyncio.create_serial_connection(
                loop,
                protocol_factory,
                port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
        else:
            # Fallback: Enter demo mode with mock hardware
            print(Colors.yellow("\n⚠ serial_asyncio not available in this Python environment"))
            print(Colors.yellow("Entering DEMO MODE with mock hardware for string command testing..."))

            # Ask user if they want to continue with demo mode
            while True:
                try:
                    choice = input("\nContinue with demo mode? [y/n] (default: y): ").strip().lower()
                    if not choice or choice == 'y':
                        break
                    elif choice == 'n':
                        print("\nExiting program.")
                        return
                    else:
                        print("Invalid choice. Please enter y or n.")
                except (EOFError, KeyboardInterrupt):
                    print("\n\nExiting program.")
                    return

            # Import and use mock SDK client
            from mock_serial_protocol import get_mock_sdk_client

            print(f"\nOpening mock serial port {port}...")
            mock_client = get_mock_sdk_client()
            await mock_client.connect(port, baudrate)

            # Create mock protocol instance
            protocol_instance = mock_client.protocol
            transport = mock_client  # Use mock client as transport

            # Set mock SDK client
            sdk_client = mock_client
            set_sdk_client(sdk_client)

            # In demo mode, skip to interactive string command mode
            print(Colors.green(f"✓ Mock serial port {port} opened"))
            print(Colors.green("✓ Demo mode ready for string command testing"))

            # Auto-detect mock device
            global STATION_ID_X, STATION_ID_Y
            STATION_ID_X = 5  # Mock station ID
            STATION_ID_Y = 0  # No second motor in demo
            station_id = STATION_ID_X

            print("\n" + "=" * 60)
            print(Colors.yellow("Demo Mode - String Command Testing"))
            print("=" * 60)
            print(Colors.green(f"✓ Auto-assigned: STATION_ID_X = {STATION_ID_X}"))
            print(Colors.blue(f"Ready to test string commands like: BG;ML;PA60000;JV1000;"))

            # Skip to interactive mode directly
            goto_interactive_mode = True
            return  # Exit the serial communication function early in demo mode
        
        print(f"✓ Serial port {port} opened")
        
        # Initialize print message flags after successful serial connection
        init_print_messages()
        
        # Create SDK client and set it via dependency injection
        sdk_client = SDKClient(transport, protocol_instance)
        set_sdk_client(sdk_client)
        
        # Wait a short time to ensure connection is stable
        await asyncio.sleep(INITIALIZATION_DELAY)
        
        # Create event manager for PTP motion and DIO port notifications
        event_manager = EventManager()
        
        # Background task to handle real-time notification messages from device
        async def handle_active_messages() -> None:
            """
            Continuously monitor and handle real-time notification messages from device.
            
            This background task runs independently and processes asynchronous messages
            sent by the device without a command request. These include:
            - Motion completion notifications (PTP Motion In Position)
            - Error notifications
            - Status change notifications
            
            Message Flow:
            1. Device sends real-time notification message autonomously
            2. SerialProtocol routes it to active_message_queue (not response_queue)
            3. This task retrieves it from the queue and processes it
            4. For PTP Motion In Position notifications, sets an event to signal completion
            
            Event Synchronization:
            - Each station has its own asyncio.Event for PTP motion completion
            - When a PTP Motion In Position notification is received, the corresponding
              event is set, allowing wait_for_ptp_motion_in_position() to detect completion
            - This enables asynchronous motion control without polling
            
            Timeout Handling:
            - Uses timeout on queue.get() to periodically check for cancellation
            - Timeout is expected and normal - it allows the loop to continue
            - If an error occurs, waits before retrying to avoid tight error loops
            """
            while True:
                try:
                    # Wait for real-time notification message with timeout
                    # Timeout allows periodic checking for task cancellation
                    frame = await asyncio.wait_for(protocol_instance.active_message_queue.get(), timeout=ACTIVE_MESSAGE_QUEUE_TIMEOUT)

                    # Process real-time notification message
                    if constants.PRINT_MESSAGES:
                        print(Colors.purple("\n" + "=" * 60))
                        print(Colors.purple("Real-time Notification Message Received from Device:"))
                        print(Colors.purple("=" * 60))
                        print(Colors.purple(f"Hexadecimal: {bytes_to_hex_string(frame)}"))

                    # Parse real-time notification message
                    try:
                        parsed = parse_response_frame(frame)
                        cw_info = parsed['control_word_info']

                        if constants.PRINT_MESSAGES:
                            print(Colors.purple("Parsed Real-time Notification Message:"))
                            print("-" * 60)
                            print(Colors.purple(f"Station ID: 0x{parsed['station_id']:02X} ({parsed['station_id']}) | Control Word: 0x{parsed['control_word']:02X} ({parsed['control_word']}) - {cw_info['command_name']} ({cw_info['command_description']})"))
                            data_info = f"Data Length: {parsed['data_len']}"
                            if parsed['data_len'] > 0:
                                data_info += f" | Data Bytes: {bytes_to_hex_string(bytes(parsed['data_bytes']))} ({parsed['data_bytes']})"
                            data_info += f" | CRC Valid: {'✓ Yes' if parsed['crc_valid'] else '✗ No'}"
                            print(Colors.purple(data_info))

                        # Check if this is a Real-Time Notification and parse d0 code
                        # Real-time notifications have a d0 code that indicates the notification type
                        if cw_info['is_real_time_notification'] and parsed['data_len'] > 0 and len(parsed['data_bytes']) > 0:
                            d0_code = parsed['data_bytes'][0]  # First data byte contains notification code
                            rtcn_d0_info = parse_rtcn_d0_code(d0_code)

                            if constants.PRINT_MESSAGES:
                                print(Colors.purple(f"Real-Time Notification Code (d0): 0x{rtcn_d0_info['raw_value']:02X} ({rtcn_d0_info['raw_value']}) - {rtcn_d0_info['code_name']} ({rtcn_d0_info['code_description']})"))

                            # Check if this is PTP Motion In Position notification
                            # This notification indicates that a PTP motion has completed and reached target position
                            if d0_code == RTCN_MXN_INP:
                                # Set the event for the specific station that sent this notification
                                # This allows wait_for_ptp_motion_in_position() to detect completion
                                notif_station_id = parsed['station_id']
                                event_manager.get_ptp_motion_event(notif_station_id).set()
                                if constants.PRINT_MESSAGES:
                                    print(Colors.purple(f"PTP Motion In Position event set for Station ID: {notif_station_id}"))

                            # Check if this is DIO Port state change notification
                            # These notifications indicate that a DIO port (P1, P2, P3, P4) has changed state
                            elif d0_code in [RTCN_DIO_P1L, RTCN_DIO_P1H, RTCN_DIO_P2L, RTCN_DIO_P2H,
                                             RTCN_DIO_P3L, RTCN_DIO_P3H]:
                                notif_station_id = parsed['station_id']
                                # Set the event for the specific station and port state
                                # This allows wait_for_s1_trigger() to detect state changes
                                event_manager.get_dio_port_event(notif_station_id, d0_code).set()

                                # Get port name and state name from dictionary mapping
                                port_name, state_name = DIO_PORT_CODE_MAP.get(d0_code, ("Unknown", "Unknown"))

                                if constants.PRINT_MESSAGES:
                                    print(Colors.purple(f"DIO Port {port_name} {state_name} notification received from Station ID: {notif_station_id}"))
                                    print(Colors.purple(f"DIO Port {port_name} {state_name} event set for Station ID: {notif_station_id}"))

                        if constants.PRINT_MESSAGES:
                            print(Colors.purple("=" * 60))
                    except ValueError as e:
                        if constants.PRINT_MESSAGES:
                            print(Colors.red(f"⚠ Failed to parse real-time notification message: {e}"))
                except asyncio.TimeoutError:
                    # Timeout is expected and normal - allows loop to continue and check for cancellation
                    continue
                except Exception as e:
                    # Unexpected error - log and wait before retrying to avoid tight error loops
                    print(Colors.red(f"⚠ Error handling real-time notification message: {e}"))
                    await asyncio.sleep(ACTIVE_MESSAGE_QUEUE_TIMEOUT)
        
        # Start background task for real-time notification messages
        active_message_task = asyncio.create_task(handle_active_messages())
        
        # Note: execute_and_check_sdk, check_sdk_response and check_sdk_getml_response
        # are now imported from parsers module for unified error handling
        
        # ============================================================
        # Start complete test flow
        # ============================================================
        
        # Call SdkGetML to get model, function module and firmware version (broadcast to all stations)
        result_ml = await SdkGetML(0)
        
        # Auto-detect device stations and assign STATION_ID_X and STATION_ID_Y
        device_station_ids = get_device_station_ids(result_ml)
        
        num_motors = len(device_station_ids)
        print("\n" + "=" * 60)
        print(Colors.yellow(f"Auto-detected {num_motors} motor(s): {device_station_ids}"))
        print("=" * 60)
        
        if num_motors == 1:
            # Single motor: assign to STATION_ID_X
            STATION_ID_X = device_station_ids[0]
            STATION_ID_Y = 0  # No Y motor
            station_id = STATION_ID_X
            print(Colors.green(f"✓ Auto-assigned: STATION_ID_X = {STATION_ID_X}"))
        elif num_motors >= 2:
            # Two or more motors: assign smaller ID to X, larger ID to Y
            STATION_ID_X = device_station_ids[0]  # Smaller station ID
            STATION_ID_Y = device_station_ids[1]  # Larger station ID
            station_id = STATION_ID_X
            print(Colors.green(f"✓ Auto-assigned: STATION_ID_X = {STATION_ID_X}, STATION_ID_Y = {STATION_ID_Y}"))
        else:
            # This should not happen as get_device_station_ids raises exception if no stations
            raise NoDeviceStationsError(has_gateway=False)
        
        # Validate that the assigned station_id exists
        check_sdk_getml_response(result_ml, station_id)
        
        # Display station assignment information
        print("\n" + "=" * 60)
        if num_motors == 1:
            print(Colors.blue(f"Station Configuration Information:"))
            print(Colors.blue(f"  - Detected {num_motors} motor(s)"))
            print(Colors.blue(f"  - STATION_ID_X = {STATION_ID_X} (corresponds to station {STATION_ID_X})"))
            print(Colors.yellow(f"  - Note: Only 1 motor detected, dual motor control will be skipped"))
        else:
            print(Colors.blue(f"Station Configuration Information:"))
            print(Colors.blue(f"  - Detected {num_motors} motor(s)"))
            print(Colors.blue(f"  - STATION_ID_X = {STATION_ID_X} (corresponds to station {STATION_ID_X})"))
            print(Colors.blue(f"  - STATION_ID_Y = {STATION_ID_Y} (corresponds to station {STATION_ID_Y})"))
        print("=" * 60)
        
        # Wait for user confirmation before continuing
        print("\n" + "-" * 60)
        while True:
            try:
                choice = input("Confirm station configuration and continue? [y/n] (default: y, press Enter to continue): ").strip().lower()
                if not choice or choice == 'y':
                    break  # Continue with current configuration
                elif choice == 'n':
                    print("\nOperation cancelled by user.")
                    return  # Exit the async function gracefully
                else:
                    print("Invalid choice. Please enter y or n.")
            except (EOFError, KeyboardInterrupt):
                print("\n\nOperation cancelled by user.")
                return  # Exit the async function gracefully
        
        # Query initial configurations
        print("\n" + "=" * 60)
        print(Colors.yellow("Querying Initial Configurations..."))
        print("=" * 60)
        await execute_and_check_sdk(SdkGetInitialConfig, "SdkGetInitialConfig(ICFG_AMO_IDX)", station_id, ICFG_AMO_IDX)
        await execute_and_check_sdk(SdkGetInitialConfig, "SdkGetInitialConfig(ICFG_ACM_IDX)", station_id, ICFG_ACM_IDX)
        await execute_and_check_sdk(SdkGetDIOport, "SdkGetDIOport", station_id)

        # Query input logic configuration
        print("\n" + "=" * 60)
        print(Colors.yellow("Querying Input Logic Configuration..."))
        print("=" * 60)
        await execute_and_check_sdk(SdkGetInputLogic, "SdkGetInputLogic(SCF_S1C_IDX)", station_id, SCF_S1C_IDX)
        
        # Query motor configurations
        print("\n" + "=" * 60)
        print(Colors.yellow("Querying Motor Configurations..."))
        print("=" * 60)
        await execute_and_check_sdk(SdkGetMotorConfig, "SdkGetMotorConfig(MTS_MCS_IDX)", station_id, MTS_MCS_IDX)
        await execute_and_check_sdk(SdkGetMotorConfig, "SdkGetMotorConfig(MTS_CUR_IDX)", station_id, MTS_CUR_IDX)
        await execute_and_check_sdk(SdkGetMotorConfig, "SdkGetMotorConfig(MTS_PSV_IDX)", station_id, MTS_PSV_IDX)
        
        # Query motion status
        await execute_and_check_sdk(SdkGetMotionStatus, "SdkGetMotionStatus(command_index=0)", station_id, 0)
        await execute_and_check_sdk(SdkGetMotionStatus, "SdkGetMotionStatus(command_index=1)", station_id, 1)
        
        # Query Motion Parameters (AC, DC, SS, SD)
        print("\n" + "=" * 60)
        print(Colors.yellow("Querying Motion Parameters..."))
        print("=" * 60)
        
        await execute_and_check_sdk(SdkGetAcceleration, "SdkGetAcceleration", station_id)
        await execute_and_check_sdk(SdkGetDeceleration, "SdkGetDeceleration", station_id)
        await execute_and_check_sdk(SdkGetCutInSpeed, "SdkGetCutInSpeed", station_id)
        await execute_and_check_sdk(SdkGetStopDeceleration, "SdkGetStopDeceleration", station_id)
        
        # Enable motor and release brake
        await execute_and_check_sdk(SdkSetMotorOn, "SdkSetMotorOn", station_id, 1)
        
        # Release brake (Brake off) - MTS_BRK_IDX = 5, value = 0
        print("\n" + "=" * 60)
        print(f"ID:{station_id} SdkSetMotorConfig[5] = 0 (Brake off)")
        print("=" * 60)
        await execute_and_check_sdk(SdkSetMotorConfig, "SdkSetMotorConfig(Brake off)", station_id, MTS_BRK_IDX, 0)
        print(Colors.green("✓ SdkSetMotorConfig (Brake off) ... [  OK  ]"))
        
        # Start jog motion
        await execute_and_check_sdk(SdkSetJogMxn, "SdkSetJogMxn", station_id, DEFAULT_JOG_SPEED)
        await execute_and_check_sdk(SdkSetBeginMxn, "SdkSetBeginMxn", station_id)
        
        print("\n" + "=" * 60)
        print("Communication completed")
        print("=" * 60)
        
        # Wait and query motion status
        await wait_with_message(WAIT_BEFORE_STOP, f"Waiting {WAIT_BEFORE_STOP} seconds before stopping motor...")
        await execute_and_check_sdk(SdkGetMotionStatus, "SdkGetMotionStatus(During Jog Motion)", station_id, 1)
        
        # Stop jog motion
        await execute_and_check_sdk(SdkSetJogMxn, "SdkSetJogMxn(stop)", station_id, 0)
        await execute_and_check_sdk(SdkSetBeginMxn, "SdkSetBeginMxn(stop)", station_id)
        
        # Test emergency stop
        await wait_with_message(WAIT_BEFORE_ESTOP, f"Waiting {WAIT_BEFORE_ESTOP} seconds before calling SdkSetStopMxn...")
        print("\n" + "-" * 60)
        print("Calling SdkSetStopMxn (Emergency Stop demo)...")
        print("-" * 60)
        await execute_and_check_sdk(SdkSetStopMxn, "SdkSetStopMxn(Demo)", station_id)
        
        # Set origin
        await wait_with_message(WAIT_BEFORE_ORIGIN, f"Waiting {WAIT_BEFORE_ORIGIN} seconds before calling SdkSetOrigin...")
        await execute_and_check_sdk(SdkSetOrigin, "SdkSetOrigin", station_id)
        await wait_with_message(WAIT_AFTER_ORIGIN, f"Waiting {WAIT_AFTER_ORIGIN} second after SdkSetOrigin...")
        
        # PTP Motion Tests
        print("\n" + "=" * 60)
        print("PTP Motion Tests")
        print("=" * 60)
        
        # Execute PTP motions
        await execute_ptp_motion(event_manager, execute_and_check_sdk, station_id, DEFAULT_PTP_POSITION, DEFAULT_PTP_SPEED, "PTP1")
        await execute_ptp_motion(event_manager, execute_and_check_sdk, station_id, 0, DEFAULT_PTP_SPEED, "PTP2")
        
        # Relative motion
        await execute_and_check_sdk(SdkSetPtpMxnR, f"SdkSetPtpMxnR({DEFAULT_PTP_RELATIVE_POSITION})", station_id, DEFAULT_PTP_RELATIVE_POSITION)
        await execute_and_check_sdk(SdkSetPtpSPD, f"SdkSetPtpSPD({DEFAULT_PTP_SPEED})", station_id, DEFAULT_PTP_SPEED)
        await execute_and_check_sdk(SdkSetBeginMxn, "SdkSetBeginMxn(PTP3)", station_id)
        await wait_for_ptp_motion_in_position(event_manager, station_id, timeout=DEFAULT_PTP_MOTION_TIMEOUT)
        
        # Query absolute position
        await execute_and_check_sdk(SdkGetPtpMxnA, "SdkGetPtpMxnA", station_id)

        # Ask user if they want to enter interactive mode
        print("\n" + "=" * 60)
        while True:
            try:
                choice = input(Colors.yellow("Enter interactive string command mode? [y/n] (default: y): ")).strip().lower()
                if not choice or choice == 'y':
                    enter_interactive = True
                    break
                elif choice == 'n':
                    enter_interactive = False
                    break
                else:
                    print("Invalid choice. Please enter y or n.")
            except (EOFError, KeyboardInterrupt):
                print("\nSkipping interactive mode.")
                enter_interactive = False
                break

        if not enter_interactive:
            print(Colors.green("Skipping interactive mode."))
            return

        # Check if string_commands is available
        global STRING_COMMANDS_AVAILABLE
        if not STRING_COMMANDS_AVAILABLE:
            print(Colors.red("Interactive mode is not available due to missing dependencies."))
            print(Colors.yellow("Attempting to import string_commands again..."))
            try:
                from string_commands import execute_string_commands
                print(Colors.green("Success! Interactive mode is ready."))
                STRING_COMMANDS_AVAILABLE = True
            except Exception as e:
                print(Colors.red(f"Failed to import string_commands: {e}"))
                print(Colors.yellow("Skipping interactive mode."))
                return

        # Interactive String Command Mode
        print("\n" + "=" * 60)
        print(Colors.yellow("Interactive String Command Mode"))
        print("=" * 60)
        print("Enter string commands like: BG;ML;PA60000;JV1000;")
        print("Type 'quit' to exit, 'help' for available commands")
        print("=" * 60)

        while True:
            try:
                user_input = input("\nEnter commands (or 'quit' to continue): ").strip()

                if not user_input or user_input.lower() == 'quit':
                    print(Colors.green("Exiting interactive mode..."))
                    break
                elif user_input.lower() == 'help':
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
                    print("\nExamples:")
                    print("  BG;ML;PA60000;JV10000;MO1")
                    print("  PA0;SP5000;BG")
                    print("  MS0;DI;ML")
                    continue

                # Execute the string commands
                results = await execute_string_commands(user_input, station_id)

                # Show summary
                if results:
                    success_count = sum(1 for r in results if r['success'])
                    print(f"\nExecuted {len(results)} commands: {success_count} successful, {len(results) - success_count} failed")

            except (EOFError, KeyboardInterrupt):
                print("\n\nInteractive mode interrupted.")
                break
            except Exception as e:
                print(Colors.red(f"\n✗ Error in interactive mode: {e}"))

        # GotoHome - Move to home position
        goto_home_success, x_axis_s1_timeout = await goto_home(event_manager, execute_and_check_sdk, station_id)
        
        # Track if X axis (STATION_ID_X) had S1 timeout
        # This will be used to stop X axis motor before dual motor control if needed
        x_axis_s1_timeout_flag = x_axis_s1_timeout if station_id == STATION_ID_X else False

        
        # ============================================================
        # Dual Motor Control Demo (STATION_ID_X and STATION_ID_Y)
        # ============================================================
        # This section demonstrates synchronized control of two motors (X and Y axes).
        # The motors are controlled independently but can be synchronized for coordinated motion.
        #
        # Control Flow:
        # 1. Enable both motors (power on)
        # 2. Release brakes on both motors (allow movement)
        # 3. Set origin (zero position) for both motors
        # 4. Set target positions for both motors
        # 5. Set different speeds (to demonstrate asynchronous completion)
        # 6. Start motion on both motors simultaneously
        # 7. Wait for BOTH motors to complete (synchronized wait)
        # 8. Lock brakes and disable motors
        #
        # Synchronization:
        # - Motors start simultaneously (commands sent sequentially but quickly)
        # - wait_for_ptp_motion_in_position() waits for ALL stations to complete
        # - This ensures both motors finish before proceeding
        # - Different speeds demonstrate that faster motor waits for slower one
        #
        # Note: This section only executes if 2 motors are detected (STATION_ID_Y != 0)
        if STATION_ID_Y != 0:
            print("\n" + "=" * 60)
            print("Dual Motor Control Demo - STATION_ID_X and STATION_ID_Y")
            print("=" * 60)
            
            await wait_with_message(WAIT_BEFORE_DUAL_MOTOR, f"Waiting {WAIT_BEFORE_DUAL_MOTOR} seconds before dual motor control...")
            
            # If X axis had S1 timeout during goto_home, stop X axis motor before starting dual motor control
            # This ensures X axis motor is stopped if it was still running from the failed goto_home
            if x_axis_s1_timeout_flag:
                print("\n" + "-" * 60)
                print(f"Stopping X axis motor (Station {STATION_ID_X}) before dual motor control due to previous S1 timeout...")
                print("-" * 60)
                try:
                    # Set Jog speed to zero to stop the motion
                    await execute_and_check_sdk(SdkSetJogMxn, f"SdkSetJogMxn(stop, STATION_ID_X={STATION_ID_X})", STATION_ID_X, 0)
                    await execute_and_check_sdk(SdkSetBeginMxn, f"SdkSetBeginMxn(stop, STATION_ID_X={STATION_ID_X})", STATION_ID_X)
                    await asyncio.sleep(0.2)  # Wait a bit for motor to stop
                    print(Colors.green(f"✓ X axis motor (Station {STATION_ID_X}) stopped"))
                except Exception as stop_error:
                    print(Colors.yellow(f"⚠ Failed to stop X axis motor (Station {STATION_ID_X}): {stop_error}"))
            
            # Wait 1 second before starting dual motor control
            print("\n" + "-" * 60)
            print("Waiting 1 second before starting dual motor control...")
            print("-" * 60)
            await asyncio.sleep(1.0)
            print(Colors.green("✓ 1 second elapsed"))
            
            # Step 1: Enable both motors (STATION_ID_X and STATION_ID_Y)
            # Motor must be enabled before any motion commands can be executed
            print("\n" + "-" * 60)
            print(f"Enabling motors: STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetMotorOn, f"SdkSetMotorOn(STATION_ID_X={STATION_ID_X}, enable)", STATION_ID_X, 1)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} motor enabled"))
            
            await execute_and_check_sdk(SdkSetMotorOn, f"SdkSetMotorOn(STATION_ID_Y={STATION_ID_Y}, enable)", STATION_ID_Y, 1)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} motor enabled"))
            
            # Step 2: Release brake for both motors (Brake off) - MTS_BRK_IDX = 5, value = 0
            # Brake must be released before motor can move. Brake prevents movement when motor is off.
            print("\n" + "-" * 60)
            print(f"Releasing brakes: STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetMotorConfig, f"SdkSetMotorConfig(STATION_ID_X={STATION_ID_X}, Brake off)", STATION_ID_X, MTS_BRK_IDX, 0)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} brake released"))
            
            await execute_and_check_sdk(SdkSetMotorConfig, f"SdkSetMotorConfig(STATION_ID_Y={STATION_ID_Y}, Brake off)", STATION_ID_Y, MTS_BRK_IDX, 0)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} brake released"))
            
            # Step 3: Call SdkSetOrigin for both motors (clear position to zero)
            # Setting origin establishes the current position as zero reference point.
            # This is important for absolute position control.
            print("\n" + "-" * 60)
            print(f"Setting origin (clear to zero): STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetOrigin, f"SdkSetOrigin(STATION_ID_X={STATION_ID_X})", STATION_ID_X)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} origin set"))
            
            await execute_and_check_sdk(SdkSetOrigin, f"SdkSetOrigin(STATION_ID_Y={STATION_ID_Y})", STATION_ID_Y)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} origin set"))
            
            # Delay after origin set to allow position to stabilize
            await wait_with_message(WAIT_AFTER_ORIGIN_SET, f"Waiting {WAIT_AFTER_ORIGIN_SET} second after origin set...")
            
            # Step 4: Set absolute position to DEFAULT_PTP_POSITION for both motors
            # This sets the target position for PTP (Point-To-Point) motion.
            # Both motors will move to the same absolute position.
            print("\n" + "-" * 60)
            print(f"Setting PTP position to {DEFAULT_PTP_POSITION}: STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetPtpMxnA, f"SdkSetPtpMxnA(STATION_ID_X={STATION_ID_X}, {DEFAULT_PTP_POSITION})", STATION_ID_X, DEFAULT_PTP_POSITION)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} position set to {DEFAULT_PTP_POSITION}"))
            
            await execute_and_check_sdk(SdkSetPtpMxnA, f"SdkSetPtpMxnA(STATION_ID_Y={STATION_ID_Y}, {DEFAULT_PTP_POSITION})", STATION_ID_Y, DEFAULT_PTP_POSITION)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} position set to {DEFAULT_PTP_POSITION}"))
            
            # Step 5: Set different speeds: STATION_ID_X=DEFAULT_PTP_SPEED_X, STATION_ID_Y=DEFAULT_PTP_SPEED_Y
            # Using different speeds demonstrates that wait_for_ptp_motion_in_position() waits
            # for ALL motors to complete, even if they finish at different times.
            # The faster motor will wait for the slower one before proceeding.
            print("\n" + "-" * 60)
            print(f"Setting different speeds: STATION_ID_X={STATION_ID_X}->{DEFAULT_PTP_SPEED_X}, STATION_ID_Y={STATION_ID_Y}->{DEFAULT_PTP_SPEED_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetPtpSPD, f"SdkSetPtpSPD(STATION_ID_X={STATION_ID_X}, {DEFAULT_PTP_SPEED_X})", STATION_ID_X, DEFAULT_PTP_SPEED_X)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} speed set to {DEFAULT_PTP_SPEED_X}"))
            
            await execute_and_check_sdk(SdkSetPtpSPD, f"SdkSetPtpSPD(STATION_ID_Y={STATION_ID_Y}, {DEFAULT_PTP_SPEED_Y})", STATION_ID_Y, DEFAULT_PTP_SPEED_Y)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} speed set to {DEFAULT_PTP_SPEED_Y}"))
            
            # Step 6: Start motion for both motors
            # SdkSetBeginMxn initiates the motion that was configured with position and speed.
            # Both motors start moving simultaneously (commands sent sequentially but quickly).
            print("\n" + "-" * 60)
            print(f"Starting motion: STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetBeginMxn, f"SdkSetBeginMxn(STATION_ID_X={STATION_ID_X})", STATION_ID_X)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} motion started"))
            
            await execute_and_check_sdk(SdkSetBeginMxn, f"SdkSetBeginMxn(STATION_ID_Y={STATION_ID_Y})", STATION_ID_Y)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} motion started"))
            
            # Step 7: Wait for BOTH motors to complete (PTP Motion In Position)
            # This is a synchronized wait - the function waits for ALL specified stations
            # to send "PTP Motion In Position" notifications before returning.
            # Even if one motor finishes faster, we wait for both to complete.
            print("\n" + "-" * 60)
            print(f"Waiting for both motors to complete: STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await wait_for_ptp_motion_in_position(event_manager, [STATION_ID_X, STATION_ID_Y], timeout=DUAL_MOTOR_MOTION_TIMEOUT)
            
            # Delay after motion complete to allow system to stabilize
            await wait_with_message(WAIT_AFTER_DUAL_MOTOR, f"Waiting {WAIT_AFTER_DUAL_MOTOR} seconds after dual motor motion complete...")
            
            # Step 8: Lock brakes for both motors
            # Locking the brake prevents movement when motor is disabled.
            # This is a safety measure to hold position.
            print("\n" + "-" * 60)
            print(f"Locking brakes: STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetMotorConfig, f"SdkSetMotorConfig(STATION_ID_X={STATION_ID_X}, Brake on)", STATION_ID_X, MTS_BRK_IDX, 1)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} brake locked"))
            
            await execute_and_check_sdk(SdkSetMotorConfig, f"SdkSetMotorConfig(STATION_ID_Y={STATION_ID_Y}, Brake on)", STATION_ID_Y, MTS_BRK_IDX, 1)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} brake locked"))
            
            # Step 9: Disable both motors
            # Disabling the motor turns off power. Brake should be locked first to hold position.
            print("\n" + "-" * 60)
            print(f"Disabling motors: STATION_ID_X={STATION_ID_X}, STATION_ID_Y={STATION_ID_Y}")
            print("-" * 60)
            await execute_and_check_sdk(SdkSetMotorOn, f"SdkSetMotorOn(STATION_ID_X={STATION_ID_X}, disable)", STATION_ID_X, 0)
            print(Colors.green(f"✓ STATION_ID_X={STATION_ID_X} motor disabled"))
            
            await execute_and_check_sdk(SdkSetMotorOn, f"SdkSetMotorOn(STATION_ID_Y={STATION_ID_Y}, disable)", STATION_ID_Y, 0)
            print(Colors.green(f"✓ STATION_ID_Y={STATION_ID_Y} motor disabled"))
        else:
            # Single motor mode: skip dual motor control
            print("\n" + "=" * 60)
            print(Colors.yellow("Dual Motor Control Demo - Skipped"))
            print("=" * 60)
            print(Colors.yellow(f"Only 1 motor detected (STATION_ID_X={STATION_ID_X}), skipping dual motor control."))
            print(Colors.yellow("Dual motor control requires 2 motors."))
        
        print("\n" + "=" * 60)
        print("Complete Test Suite Finished Successfully!")
        print("=" * 60)
        
    except serial.SerialException as e:
        print(Colors.red(f"\n✗ Serial port error: {e}"))
        print("Please check:")
        print(f"  1. Whether {port} port exists")
        print("  2. Whether the port is occupied by another program")
        print("  3. Whether the port parameters are correct")
        print("  4. Try reselecting a different serial port")
        # Re-raise to allow main() to handle port reselection
        raise
    except (NoResponseError, NoStationsError, NoDeviceStationsError, TargetStationNotFoundError) as e:
        # SDK communication errors - these are expected errors that should stop execution
        print(Colors.red(f"\n✗ {type(e).__name__}: {e}"))
        print(Colors.red("Program terminated due to communication error."))
    except ValueError as e:
        print(Colors.red(f"\n✗ Data format error: {e}"))
    except Exception as e:
        print(Colors.red(f"\n✗ Error occurred: {type(e).__name__}: {e}"))
    finally:
        # Emergency motor safety cleanup: stop motors, disable, and lock brakes
        # This ensures motors are in a safe state even if program exits abnormally
        try:
            sdk_client = None
            try:
                sdk_client = get_sdk_client()
            except RuntimeError:
                # SDK client not initialized, skip cleanup
                pass
            
            if sdk_client and (STATION_ID_X != 0 or STATION_ID_Y != 0):
                print("\n" + "=" * 60)
                print(Colors.yellow("Emergency Motor Safety Cleanup..."))
                print("=" * 60)
                
                # List of stations to clean up
                stations_to_cleanup = []
                if STATION_ID_X != 0:
                    stations_to_cleanup.append(STATION_ID_X)
                if STATION_ID_Y != 0:
                    stations_to_cleanup.append(STATION_ID_Y)
                
                for station_id in stations_to_cleanup:
                    try:
                        # Step 1: Set speed to zero (stop motion)
                        print(f"Setting speed to zero for Station {station_id}...")
                        await SdkSetJogMxn(station_id, 0)
                        await asyncio.sleep(0.1)
                        
                        # Step 2: Lock brake (brake on)
                        print(f"Locking brake for Station {station_id}...")
                        await SdkSetMotorConfig(station_id, MTS_BRK_IDX, 1)
                        await asyncio.sleep(0.1)
                        
                        # Step 3: Disable motor (motor off)
                        print(f"Disabling motor for Station {station_id}...")
                        await SdkSetMotorOn(station_id, 0)
                        await asyncio.sleep(0.1)
                        
                        print(Colors.green(f"✓ Station {station_id} safety cleanup completed"))
                    except Exception as cleanup_error:
                        # Continue cleanup for other stations even if one fails
                        print(Colors.red(f"⚠ Failed to cleanup Station {station_id}: {cleanup_error}"))
                
                print(Colors.green("✓ Emergency motor safety cleanup completed"))
        except Exception as e:
            # If cleanup itself fails, just log and continue
            print(Colors.yellow(f"⚠ Emergency cleanup failed: {e}"))
        
        # Cleanup resources
        if active_message_task and not active_message_task.done():
            active_message_task.cancel()
            try:
                await active_message_task
            except asyncio.CancelledError:
                pass
        
        if transport:
            transport.close()
            await asyncio.sleep(0.1)  # Wait for close to complete
            print(f"\n✓ Serial port {port} closed")


def main() -> None:
    """Main function"""
    try:
        # Try to auto-connect with saved port (no user interaction)
        saved_index: int = load_port_config()
        auto_connect_attempted: bool = False
        
        if saved_index > 0:
            # Have saved config, try auto-connect
            selected_port: Optional[str] = select_serial_port(use_saved=True, auto_connect=True)
            auto_connect_attempted = True
        else:
            # No saved config, prompt user to select
            selected_port: Optional[str] = select_serial_port(use_saved=False, auto_connect=False)
        
        if selected_port is None:
            print("\nExiting program.")
            sys.exit(0)
        
        # Try to run async communication with selected port
        try:
            asyncio.run(serial_communication_async(selected_port))
        except (serial.SerialException, OSError, ValueError) as e:
            # Connection failed, prompt user to reselect port
            print(Colors.red(f"\n✗ Connection failed: {e}"))
            if auto_connect_attempted:
                print(Colors.yellow("\nAuto-connect failed."))
            
            # Ask user if they want to reselect serial port
            print("-" * 60)
            while True:
                try:
                    choice = input("Do you want to reselect serial port? [y/n] (default: y): ").strip().lower()
                    if not choice or choice == 'y':
                        break  # Continue to port reselection
                    elif choice == 'n':
                        print("\nExiting program.")
                        sys.exit(0)
                    else:
                        print("Invalid choice. Please enter y or n.")
                except (EOFError, KeyboardInterrupt):
                    print("\n\nExiting program.")
                    sys.exit(0)
            
            # Retry with port reselection
            while True:
                selected_port = select_serial_port(use_saved=False, auto_connect=False)
                
                if selected_port is None:
                    print("\nExiting program.")
                    sys.exit(0)
                
                try:
                    # Try again with new port selection
                    asyncio.run(serial_communication_async(selected_port))
                    break  # Success, exit retry loop
                except (serial.SerialException, OSError, ValueError) as retry_error:
                    print(Colors.red(f"\n✗ Connection failed again: {retry_error}"))
                    
                    # Ask user if they want to try again
                    print("-" * 60)
                    while True:
                        try:
                            retry_choice = input("Do you want to try selecting a different port? [y/n] (default: y): ").strip().lower()
                            if not retry_choice or retry_choice == 'y':
                                break  # Continue to port reselection
                            elif retry_choice == 'n':
                                print("\nExiting program.")
                                sys.exit(0)
                            else:
                                print("Invalid choice. Please enter y or n.")
                        except (EOFError, KeyboardInterrupt):
                            print("\n\nExiting program.")
                            sys.exit(0)
                    # Continue loop to retry
                except (NoResponseError, NoStationsError, NoDeviceStationsError, TargetStationNotFoundError) as sdk_error:
                    # SDK communication errors - these are fatal, exit program
                    print(Colors.red(f"\n✗ {type(sdk_error).__name__}: {sdk_error}"))
                    print(Colors.red("Program terminated due to communication error."))
                    sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(Colors.red(f"\nUnexpected error: {type(e).__name__}: {e}"))
        sys.exit(1)


if __name__ == "__main__":
    main()