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
Motor control helper functions for serial communication

This module contains helper functions for motor control operations including:
- Waiting for PTP motion completion
- Waiting for S1 trigger signals
- Executing PTP motions
- Moving to home position
- Utility functions for waiting with messages
"""

import asyncio
import time
from typing import Optional, List, Union, Callable, Dict, Any

from constants import (
    RTCN_MXN_INP,
    RTCN_DIO_P1L,
    DEFAULT_PTP_MOTION_TIMEOUT,
    DUAL_MOTOR_MOTION_TIMEOUT,
    SCF_S1C_IDX,
    ILC_EST_IDX,
    ILC_NOP_IDX
)
from utils import Colors
from sdk_functions import (
    SdkGetDIOport,
    SdkSetPtpMxnR,
    SdkSetPtpSPD,
    SdkSetBeginMxn,
    SdkSetInputLogic,
    SdkSetJogMxn,
    SdkSetPtpMxnA
)


# ==============================================================================
# Event Manager Class
# ==============================================================================

class EventManager:
    """
    Manages asyncio events for PTP motion and DIO port notifications.
    
    This class provides a centralized way to manage events that are used
    for synchronization between motor control operations and real-time
    notifications from the device.
    """
    
    def __init__(self) -> None:
        """Initialize event manager with empty event dictionaries"""
        self.ptp_motion_events: Dict[int, asyncio.Event] = {}
        self.dio_port_events: Dict[tuple, asyncio.Event] = {}
    
    def get_ptp_motion_event(self, sid: int) -> asyncio.Event:
        """
        Get or create PTP motion event for a specific station
        
        Args:
            sid: Station ID
            
        Returns:
            asyncio.Event for the specified station
        """
        if sid not in self.ptp_motion_events:
            self.ptp_motion_events[sid] = asyncio.Event()
        return self.ptp_motion_events[sid]
    
    def get_dio_port_event(self, sid: int, d0_code: int) -> asyncio.Event:
        """
        Get or create DIO port event for a specific station and port state
        
        Args:
            sid: Station ID
            d0_code: DIO port state code (e.g., RTCN_DIO_P1L, RTCN_DIO_P1H)
            
        Returns:
            asyncio.Event for the specified station and port state
        """
        key = (sid, d0_code)
        if key not in self.dio_port_events:
            self.dio_port_events[key] = asyncio.Event()
        return self.dio_port_events[key]


# ==============================================================================
# Helper Functions
# ==============================================================================

async def wait_with_message(seconds: float, message: str) -> None:
    """
    Wait for specified seconds and print message
    
    Args:
        seconds: Number of seconds to wait
        message: Message to display before waiting
    """
    print("\n" + "-" * 60)
    print(message)
    print("-" * 60)
    await asyncio.sleep(seconds)
    print(f"OK {seconds} second{'s' if seconds != 1.0 else ''} elapsed")


async def wait_for_ptp_motion_in_position(
    event_manager: EventManager,
    station_ids: Union[int, List[int]], 
    timeout: Optional[float] = None
) -> bool:
    """
    Wait for PTP Motion In Position real-time notification message(s).
    
    This function waits for the device to send a "PTP Motion In Position" notification,
    which indicates that a Point-To-Point motion has completed and reached the target
    position. This enables asynchronous motion control without polling.
    
    How It Works:
    1. Each station has an asyncio.Event that tracks PTP motion completion
    2. When handle_active_messages() receives a PTP Motion In Position notification,
       it sets the corresponding station's event
    3. This function waits for the event(s) to be set
    4. For multiple stations, waits for ALL stations to complete (synchronized motion)
    
    Event Synchronization:
    - Events are cleared before waiting to ensure we detect new notifications
    - For single station: waits for one event
    - For multiple stations: waits for all events using asyncio.gather()
    - Uses asyncio.wait_for() to enforce timeout
    
    Timeout Handling:
    - Single station: Uses DEFAULT_PTP_MOTION_TIMEOUT
    - Multiple stations: Uses DUAL_MOTOR_MOTION_TIMEOUT (longer, as multiple motors
      may take different times to complete)
    - On timeout, reports which stations completed and which are still pending
    
    Args:
        event_manager: EventManager instance for accessing events
        station_ids: Station ID(s) to wait for. Can be a single int or list of ints.
                    For multiple stations, waits for ALL to complete.
        timeout: Optional timeout in seconds. If None, uses default based on
                number of stations.
    
    Returns:
        True if all stations completed within timeout, False if timeout occurred.
    
    Example:
        # Wait for single station
        await wait_for_ptp_motion_in_position(event_manager, 5)
        
        # Wait for multiple stations (both must complete)
        await wait_for_ptp_motion_in_position(event_manager, [5, 12])
    """
    # Determine timeout based on number of stations if not specified
    if timeout is None:
        # Use longer timeout for multiple stations (they may finish at different times)
        if isinstance(station_ids, list) and len(station_ids) > 1:
            timeout = DUAL_MOTOR_MOTION_TIMEOUT
        else:
            timeout = DEFAULT_PTP_MOTION_TIMEOUT
    
    # Normalize station_ids to a list for uniform processing
    if isinstance(station_ids, int):
        wait_stations = [station_ids]
    else:
        wait_stations = list(station_ids)
    
    print("\n" + "-" * 60)
    if len(wait_stations) == 1:
        print(f"Waiting for PTP Motion In Position notification from Station {wait_stations[0]}...")
    else:
        print(f"Waiting for PTP Motion In Position notification from Stations {wait_stations}...")
    print("-" * 60)
    
    # Clear events for all stations we're waiting for
    # This ensures we detect new notifications (events may have been set previously)
    for sid in wait_stations:
        event_manager.get_ptp_motion_event(sid).clear()
    
    start_time = time.perf_counter()
    try:
        # Create wait tasks for all stations
        # Each task waits for its station's event to be set
        wait_tasks = [event_manager.get_ptp_motion_event(sid).wait() for sid in wait_stations]
        
        # Wait for ALL stations to complete (synchronized wait)
        # asyncio.gather() waits for all tasks to complete
        # asyncio.wait_for() enforces the timeout
        await asyncio.wait_for(asyncio.gather(*wait_tasks), timeout=timeout)
        
        # All stations completed successfully
        elapsed_time = time.perf_counter() - start_time
        elapsed_ms = elapsed_time * 1000
        if len(wait_stations) == 1:
            print(Colors.green(f"OK PTP Motion In Position notification received from Station {wait_stations[0]} after {elapsed_ms:.2f} ms"))
        else:
            print(Colors.green(f"OK PTP Motion In Position notification received from all {len(wait_stations)} stations after {elapsed_ms:.2f} ms"))
        return True
    except asyncio.TimeoutError:
        # Timeout occurred - check which stations completed and which are pending
        elapsed_time = time.perf_counter() - start_time
        completed = [sid for sid in wait_stations if event_manager.get_ptp_motion_event(sid).is_set()]
        pending = [sid for sid in wait_stations if not event_manager.get_ptp_motion_event(sid).is_set()]
        
        if len(wait_stations) == 1:
            print(Colors.red(f"WARNING Timeout ({timeout}s) waiting for PTP Motion In Position notification from Station {wait_stations[0]}"))
        else:
            print(Colors.red(f"WARNING Timeout ({timeout}s) waiting for PTP Motion In Position notification"))
            if completed:
                print(Colors.green(f"  OK Completed stations: {completed}"))
            if pending:
                print(Colors.red(f"  X Pending stations: {pending}"))
        return False


async def wait_for_s1_trigger(
    event_manager: EventManager,
    station_id: int,
    timeout: float = 10.0
) -> bool:
    """
    Wait for S1 trigger signal (Home sensor signal) using event mechanism.
    
    This function waits for IN1 (Home sensor) Low Level notification via DIO port
    real-time notification. It waits for P1L (P1 Low Level) event.
    
    How It Works:
    1. Clear P1L event to ensure we detect new notifications
    2. Wait for P1L event to be set
    3. When event is set, it means IN1 has changed to Low Level
    
    Args:
        event_manager: EventManager instance for accessing events
        station_id: Station ID to check
        timeout: Maximum time to wait in seconds (default: 10.0)
    
    Returns:
        True if S1 trigger signal detected within timeout, False if timeout occurred
    """
    print("\n" + "-" * 60)
    print(f"Waiting for S1 trigger signal (Home sensor P1 Low Level) from Station {station_id}...")
    print("-" * 60)
    
    # Clear P1L event to ensure we detect new notifications
    # This ensures we detect new state changes (events may have been set previously)
    event_manager.get_dio_port_event(station_id, RTCN_DIO_P1L).clear()
    
    start_time = time.perf_counter()
    try:
        # Wait for P1L event to be set
        await asyncio.wait_for(
            event_manager.get_dio_port_event(station_id, RTCN_DIO_P1L).wait(),
            timeout=timeout
        )
        
        # Event was set - S1 trigger signal detected
        elapsed_time = time.perf_counter() - start_time
        elapsed_ms = elapsed_time * 1000
        print(Colors.green(f"OK S1 trigger signal (P1 Low Level) detected from Station {station_id} after {elapsed_ms:.2f} ms"))
        return True
            
    except asyncio.TimeoutError:
        # Timeout occurred
        elapsed_time = time.perf_counter() - start_time
        print(Colors.red(f"WARNING Timeout ({timeout}s) waiting for S1 trigger signal (P1 Low Level) from Station {station_id}"))
        return False


async def execute_ptp_motion(
    event_manager: EventManager,
    execute_and_check_sdk: Callable,
    station_id: int,
    position: int,
    speed: int,
    label: str
) -> None:
    """
    Execute a complete PTP (Point-To-Point) motion sequence.
    
    This helper function encapsulates the standard PTP motion workflow:
    1. Set target absolute position (SdkSetPtpMxnA)
    2. Set motion speed (SdkSetPtpSPD)
    3. Start motion (SdkSetBeginMxn)
    4. Wait for motion completion (wait_for_ptp_motion_in_position)
    
    The function waits for the "PTP Motion In Position" notification from the device,
    which indicates the motion has completed and reached the target position.
    
    Args:
        event_manager: EventManager instance for accessing events
        execute_and_check_sdk: Function to execute SDK commands and check responses
        station_id: Station ID to control
        position: Target absolute position (in encoder counts or units)
        speed: Motion speed (in speed units)
        label: Label for logging purposes
    """
    await execute_and_check_sdk(SdkSetPtpMxnA, f"SdkSetPtpMxnA({position})", station_id, position)
    await execute_and_check_sdk(SdkSetPtpSPD, f"SdkSetPtpSPD({speed})", station_id, speed)
    await execute_and_check_sdk(SdkSetBeginMxn, f"SdkSetBeginMxn({label})", station_id)
    await wait_for_ptp_motion_in_position(event_manager, station_id, timeout=DEFAULT_PTP_MOTION_TIMEOUT)


async def goto_home(
    event_manager: EventManager,
    execute_and_check_sdk: Callable,
    can_id: int
) -> tuple[bool, bool]:
    """
    Move motor to home position using home sensor.
    
    This function implements the home positioning sequence:
    1. Get current IN1 digital level
    2. If IN1 is LOW (Home sensor triggered), move away first
    3. Setup IN1 input logic (falling edge: Emergency Stop, rising edge: No Action)
    4. Move to home position with low speed (Jog motion)
    5. Wait for S1 trigger signal (Home sensor signal)
    6. Disable IN1 input logic
    
    Args:
        event_manager: EventManager instance for accessing events
        execute_and_check_sdk: Function to execute SDK commands and check responses
        can_id: Station ID (CAN ID) to control
    
    Returns:
        Tuple of (success: bool, s1_timeout: bool):
        - success: True if successful, False if error occurred
        - s1_timeout: True if S1 trigger timeout occurred, False otherwise
    """
    print("\n" + "=" * 60)
    print(f"GotoHome - Station ID: {can_id}")
    print("=" * 60)
    
    try:
        # Get current IN1 Digital Level
        result_dio = await execute_and_check_sdk(SdkGetDIOport, "SdkGetDIOport", can_id)
        if not result_dio or not result_dio.get('dio_structured'):
            print(Colors.red(f"X Failed to get DIO port status for Station {can_id}"))
            return False
        
        dio_structured = result_dio['dio_structured']
        in1_value = 0
        if 'inputs' in dio_structured and 'IN1' in dio_structured['inputs']:
            in1_value = dio_structured['inputs']['IN1']['value']
        
        # Move away from Home Sensor if IN1 is Low (i.e., Home Sensor is triggered)
        if in1_value == 0:
            print(f"IN1 is LOW (Home sensor triggered), moving away first...")
            
            # Setup PTP(PR) motion, SP=3000, PR=10000
            # Note: C++ code uses SdkSetPtpMxnR with SP and PR, but Python version
            # uses separate SdkSetPtpSPD and SdkSetPtpMxnR
            await execute_and_check_sdk(SdkSetPtpMxnR, "SdkSetPtpMxnR(10000)", can_id, 10000)
            await execute_and_check_sdk(SdkSetPtpSPD, "SdkSetPtpSPD(3000)", can_id, 3000)
            
            # Begin Motion
            await execute_and_check_sdk(SdkSetBeginMxn, "SdkSetBeginMxn", can_id)
            
            # Wait for movement finish (i.e., "Motor In Position" Flag from Motor)
            motion_complete = await wait_for_ptp_motion_in_position(event_manager, can_id, timeout=DEFAULT_PTP_MOTION_TIMEOUT)
            if not motion_complete:
                print(Colors.red(f"X Station {can_id}: WaitFlag Fail! (PTP motion did not complete)"))
                return False
        
        # Setup IN1 Input Logic
        # The falling edge action is ILC_EST_IDX (Emergent Stop)
        # Set the rising and falling edge action to blank (ILC_NOP_IDX)
        # Note: bOTS0=0, bPOT0=1 means falling edge FG flag disabled, POT flag enabled
        # In Python, we use SdkSetInputLogic with action codes
        # For SCF_S1C_IDX (input_index=0), falling_edge_action=ILC_EST_IDX, rising_edge_action=ILC_NOP_IDX
        print("\n" + "-" * 60)
        print(f"Setting up IN1 input logic for Station {can_id}")
        print("  Falling edge action: ILC_EST_IDX (Emergency Stop)")
        print("  Rising edge action: ILC_NOP_IDX (No Action)")
        print("-" * 60)
        
        result_il = await execute_and_check_sdk(
            SdkSetInputLogic,
            "SdkSetInputLogic(SCF_S1C_IDX, ILC_EST_IDX, ILC_NOP_IDX)",
            can_id,
            SCF_S1C_IDX,  # Input index 0 (IN1)
            ILC_EST_IDX,  # Falling edge action: Emergency Stop
            ILC_NOP_IDX   # Rising edge action: No Action
        )
        
        if not result_il:
            print(Colors.red(f"X Failed to set input logic for Station {can_id}"))
            return False
        
        # Verify the input logic was set correctly
        if result_il.get('il_info'):
            il_info = result_il['il_info']
            if il_info.get('falling_edge_action') != ILC_EST_IDX or il_info.get('rising_edge_action') != ILC_NOP_IDX:
                print(Colors.red(f"X Input logic verification failed for Station {can_id}"))
                print(f"  Expected: falling_edge=ILC_EST_IDX, rising_edge=ILC_NOP_IDX")
                print(f"  Got: falling_edge={il_info.get('falling_edge_action')}, rising_edge={il_info.get('rising_edge_action')}")
                return False
        
        # Move to the Home Position with Low Speed
        print("\n" + "-" * 60)
        print(f"Starting Jog motion to home position (speed=-10000) for Station {can_id}")
        print("-" * 60)
        
        # Setup Jog motion with negative speed (move towards home)
        await execute_and_check_sdk(SdkSetJogMxn, "SdkSetJogMxn(-10000)", can_id, -10000)
        
        # Begin Motion
        await execute_and_check_sdk(SdkSetBeginMxn, "SdkSetBeginMxn", can_id)
        
        # Wait for S1 trigger flag (home sensor signal)
        print("--------------------------------------------------------------------------------")
        print("Press IN1 on UIM342_I/O_Board to simulate the home sensor signal (in 10 seconds).")
        print("--------------------------------------------------------------------------------")
        
        s1_triggered = await wait_for_s1_trigger(event_manager, can_id, timeout=10.0)
        s1_timeout = False
        if not s1_triggered:
            s1_timeout = True
            print(Colors.red(f"ID:{can_id} Waiting S1 Trig Signal Failed!"))
            # Stop the motor immediately if S1 trigger timeout
            # The motor is still running with Jog motion, need to stop it
            print("\n" + "-" * 60)
            print(f"Stopping motor for Station {can_id} due to S1 trigger timeout...")
            print("-" * 60)
            try:
                # Set Jog speed to zero to stop the motion
                await execute_and_check_sdk(SdkSetJogMxn, "SdkSetJogMxn(stop)", can_id, 0)
                await execute_and_check_sdk(SdkSetBeginMxn, "SdkSetBeginMxn(stop)", can_id)
                await asyncio.sleep(0.2)  # Wait a bit for motor to stop
                print(Colors.green(f"OK Motor stopped for Station {can_id}"))
            except Exception as stop_error:
                print(Colors.yellow(f"WARNING Failed to stop motor for Station {can_id}: {stop_error}"))
            # Continue anyway to disable input logic
        
        # Disable IN1 Input Logic
        print("\n" + "-" * 60)
        print(f"Disabling IN1 input logic for Station {can_id}")
        print("-" * 60)
        
        # Set both falling and rising edge actions to ILC_NOP_IDX (No Action)
        await execute_and_check_sdk(
            SdkSetInputLogic,
            "SdkSetInputLogic(SCF_S1C_IDX, ILC_NOP_IDX, ILC_NOP_IDX)",
            can_id,
            SCF_S1C_IDX,  # Input index 0 (IN1)
            ILC_NOP_IDX,  # Falling edge action: No Action
            ILC_NOP_IDX   # Rising edge action: No Action
        )
        
        print(Colors.green(f"OK GotoHome completed for Station {can_id}"))
        return (True, s1_timeout)
        
    except Exception as e:
        print(Colors.red(f"X GotoHome error for Station {can_id}: {e}"))
        return (False, False)
