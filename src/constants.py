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
Constants and definitions for serial communication protocol
"""

# Default communication parameters
DEFAULT_BAUDRATE = 57600
DEFAULT_TIMEOUT = 1.0

# Message printing flag (set to False to disable message printing)
# Default value is False - will be initialized by init_print_messages()
PRINT_MESSAGES = False  # Print sent command messages and received response messages


def init_print_messages() -> None:
    """
    Initialize print message flag by prompting user for confirmation.
    Default value is False (no output).
    """
    global PRINT_MESSAGES
    
    print("\nMessage Printing Configuration:")
    print("  Enable: Print all sent command messages and received response messages (for debugging)")
    print("  Disable: No message output (default, for normal use)")
    print("  [y] Enable  [n] Disable (default)")
    
    while True:
        try:
            choice = input("Your choice (default: n): ").strip().lower()
            
            if not choice or choice == 'n':
                PRINT_MESSAGES = False
                break
            elif choice == 'y':
                PRINT_MESSAGES = True
                break
            else:
                print("Invalid choice. Please enter y or n.")
        except (EOFError, KeyboardInterrupt):
            # User pressed Ctrl+C or EOF, use default value
            PRINT_MESSAGES = False
            break
    
    print()

# Timing constants (in seconds)
INITIALIZATION_DELAY = 0.1  # Delay after serial port initialization
ACTIVE_MESSAGE_QUEUE_TIMEOUT = 0.1  # Timeout for active message queue polling
DEFAULT_PTP_MOTION_TIMEOUT = 3.0  # Default timeout for PTP motion in position notification
DUAL_MOTOR_MOTION_TIMEOUT = 10.0  # Timeout for dual motor motion completion
BROADCAST_TIMEOUT = 1.0  # Timeout for broadcast commands (SdkGetML)
MAX_BROADCAST_RESPONSES = 255  # Maximum number of responses for broadcast commands

# Gateway station ID
GATEWAY_STATION_ID = 3  # Gateway station ID (not a real device station)

# Test motion parameters
DEFAULT_JOG_SPEED = 10000  # Default jog motion speed
DEFAULT_PTP_POSITION = 20000  # Default PTP absolute position
DEFAULT_PTP_SPEED = 20000  # Default PTP motion speed
DEFAULT_PTP_SPEED_X = 10000  # Default PTP speed for STATION_ID_X
DEFAULT_PTP_SPEED_Y = 5000  # Default PTP speed for STATION_ID_Y
DEFAULT_PTP_RELATIVE_POSITION = -20000  # Default PTP relative position

# Wait delays (in seconds)
WAIT_AFTER_ORIGIN = 1.0  # Wait time after setting origin
WAIT_BEFORE_STOP = 3.0  # Wait time before stopping motor
WAIT_BEFORE_ESTOP = 2.0  # Wait time before emergency stop
WAIT_BEFORE_ORIGIN = 2.0  # Wait time before setting origin
WAIT_AFTER_ORIGIN_SET = 1.0  # Wait time after origin set
WAIT_BEFORE_DUAL_MOTOR = 2.0  # Wait time before dual motor control
WAIT_AFTER_DUAL_MOTOR = 2.0  # Wait time after dual motor motion complete

# Command Definitions
__ER = 0x0F  # Error Report - Error report/error notification
__ML = 0x0B  # Get Model - Get the model, function module and firmware version
__MT = 0x10  # Motor Configuration - Motor driver configuration
__MO = 0x15  # Motor On/Off - Motor switch control
__BG = 0x16  # Begin Motion - Start motion
__ST = 0x17  # Stop Motion 
__JV = 0x1D  # Jog Velocity - Jog speed setting
__SP = 0x1E  # Speed - Speed setting
__PR = 0x1F  # Position Relative - Relative position
__PA = 0x20  # Position Absolute - Absolute position
__OG = 0x21  # Origin - Return to origin
__AC = 0x19  # Acceleration: [GET] _AC 00 ... [SET] _AC 04 a0 a1 a2 a3 ... [ACK] _AC 04 a0 a1 a2 a3; In Time Method: a3:a0=[10...60000]ms; In Value Method: a3:a0=[10...1000000000]pps/s
__DC = 0x1A  # Deceleration: [GET] _DC 00 ... [SET] _DC 04 d0 d1 d2 d3 ... [ACK] _DC 04 d0 d1 d2 d3; In Time Method: d3:d0=[10...60000]ms; In Value Method: d3:d0=[10...1000000000]pps/s
__SS = 0x1B  # Start Speed (Cut-In Speed): [GET] _SS 00 ... [SET] _SS 04 v0 v1 v2 v3 ... [ACK] _SS 04 v0 v1 v2 v3; v3:v0=[0...65535]pps
__SD = 0x1C  # Stop Deceleration: [GET] _SD 00 ... [SET] _SD 04 d0 d1 d2 d3 ... [ACK] _SD 04 d0 d1 d2 d3; d3:d0=[400...1,000,000,000]pps/s
__IC = 0x06  # Power-Up Configuration - Power-up configuration query
__IE = 0x07  # Inform Enable: IE[i] GET/SET notification enable; i=0:IN1, 1:IN2, 2:IN3, 8:PTP finish; value 0:disable, 1:enable
__DV = 0x2E  # Desire Value - Desired value/target value
__RT = 0x5A  # Real-Time Notification - Real-time notification message
__MS = 0x11  # Motion Status & Disp. - Motion Status and Displacement: [GET] _MS 01 00 ... [ACK] _MS 08 00 ms0 ms1 00 PR0 PR1 PR2 PR3 (index 0: Get Status Flags and Relative Position) or [GET] _MS 01 01 ... [ACK] _MS 08 01 sp0 sp1 sp2 PA0 PA1 PA2 PA3 (index 1: Get Speed & Position)
__DI = 0x37  # Digital Signal Inputs and Outputs - DIO port status; [GET] _DI 00... [ACK] _DI 04 IN0 OP0 IN1 OP1; d0(IN0) bit0~bit7=IN1~IN8, d1(OP0) bit0~bit3=OP1~OP4
__IL = 0x34  # Input Triggered Action Logic - Input trigger action logic configuration

RTCN_MXN_INP = 0x29  # PTP Motion, In Position

# Real-Time Notification DIO Port State Codes
RTCN_DIO_P1L = 0x01  # P1 Low Level
RTCN_DIO_P1H = 0x02  # P1 High Level
RTCN_DIO_P2L = 0x03  # P2 Low Level
RTCN_DIO_P2H = 0x04  # P2 High Level
RTCN_DIO_P3L = 0x05  # P3 Low Level
RTCN_DIO_P3H = 0x06  # P3 High Level
RTCN_DIO_P4L = 0x07  # P4 Low Level
RTCN_DIO_P4H = 0x08  # P4 High Level

# DIO Port Code to Port Name and State Name Mapping
# Maps DIO port state codes to (port_name, state_name) tuples
DIO_PORT_CODE_MAP = {
    RTCN_DIO_P1L: ("P1", "Low Level"),
    RTCN_DIO_P1H: ("P1", "High Level"),
    RTCN_DIO_P2L: ("P2", "Low Level"),
    RTCN_DIO_P2H: ("P2", "High Level"),
    RTCN_DIO_P3L: ("P3", "Low Level"),
    RTCN_DIO_P3H: ("P3", "High Level"),
    RTCN_DIO_P4L: ("P4", "Low Level"),
    RTCN_DIO_P4H: ("P4", "High Level"),
}

# DV Response d0 Index Definitions
DVR_MOD_IDX = 0  # DV[0] Query Control Mode
DVR_CUR_IDX = 1  # DV[1] Query CUR desired value
DVR_SPD_IDX = 2  # DV[2] Query SP desired value
DVR_PRM_IDX = 3  # DV[3] Query PR desired value
DVR_PAM_IDX = 4  # DV[4] Query PA desired value
DVR_TIS_IDX = 5  # DV[5] Query TI desired value

# IC Response d0 Index Definitions (Power-Up Configuration)
ICFG_AMO_IDX = 0  # PowerUp DRV-ON - Power-up enable
ICFG_CCW_IDX = 1  # Positive Direct - Motor direction (0:CW, 1:CCW)
ICFG_UPG_IDX = 2  # Exec, UPG - UPG enable
ICFG_LCK_IDX = 3  # Input Lock Sys - Input lock system
ICFG_ACM_IDX = 4  # Acc./Dec. Unit - Acceleration/Deceleration unit (0:pps/ms, 1:ms)
ICFG_ABS_IDX = 5  # Encoder Type - Encoder type (0:Inc., 1:abs)
ICFG_QEM_IDX = 6  # Closed-Loop Mode - Closed-loop control mode
ICFG_SLM_IDX = 7  # Software Limits - Software limits

# MT Response d0 Index Definitions (Motor Configuration)
MTS_MCS_IDX = 0  # Micro-Step - Micro-step subdivision (mm=[1,2,4,8,16,32,64,128])
MTS_CUR_IDX = 1  # Current Run - Working current (ii=[5...80] x0.1 Amp)
MTS_PSV_IDX = 2  # Current Idle - Idle current percentage (pp=[0...100]%)
MTS_ENA_IDX = 3  # DRV-ON Delay - Power-on enable delay (t1:t0=[0...60000]ms)
MTS_BRK_IDX = 5  # Brake Lock - Brake enable/release (ss=[0:Release; 1:Lock])

# IE Response d0 Index Definitions (Inform Enable Configuration)
IE_IN1_IDX = 0  # Port IN1 change notification (0: disable, 1: enable)
IE_IN2_IDX = 1  # Port IN2 change notification (0: disable, 1: enable)
IE_IN3_IDX = 2  # Port IN3 change notification (0: disable, 1: enable)
IE_PTP_IDX = 8  # PTP positioning finish notification (0: disable, 1: enable)

# Input Logic Index Definitions (IL Command) - Following Only for UIM342/341/720
SCF_S1C_IDX = 0   # Input# 1 : [GET] _IL 01  00 ... [SET] _IL 03  00 Af Ar ... [ACK] _IL 03  00 Af Ar ...; Ar=[Action Code on Rising Edge]; Af=[Action Code on Falling Edge];
SCF_S2C_IDX = 1   # Input# 2 : [GET] _IL 01  01 ... [SET] _IL 03  01 Af Ar ... [ACK] _IL 03  01 Af Ar ...; Ar=[Action Code on Rising Edge]; Af=[Action Code on Falling Edge];
SCF_S3C_IDX = 2   # Input# 3
SCF_STL_IDX = 16  # On Stall      : [GET] _IL 01  10 ... [SET] _IL 03  10 As 00 ... [ACK] _IL 03  10 As 00 ...; As=[Action Code on Stall] Action triggered on stall (Only for UIM342/341)
SCF_TLC_IDX = 17  # On TorqueLimit: [GET] _IL 01  11 ... [SET] _IL 03  11 Ac Tq ... [ACK] _IL 03  11 Ac Tq ...; Ac=[Action Code on Torque Limit] Action triggered on torque limit;  Tq=[10...300]% (Torque Limit) (Only for UIM720)

# Input Triggered Action Code Definitions (On Input Triggered Action)
ILC_NOP_IDX = 0x00  # 00 Disable              / No Action
ILC_OFF_IDX = 0x01  # 01 Driver OFF            / Driver OFF
ILC_EST_IDX = 0x02  # 02 Emergent Stop         / Emergency Stop
ILC_DST_IDX = 0x03  # 03 Decelerating Stop     / Decelerating Stop
ILC_OPR_IDX = 0x04  # 04 Origin + reverse PR;  / Set Origin + Reverse Position Relative
ILC_OES_IDX = 0x05  # 05 Origin + EStop;      / Set Origin + Emergency Stop
ILC_ODS_IDX = 0x06  # 06 Origin + DStop;      / Set Origin + Decelerating Stop
ILC_RJV_IDX = 0x07  # 07 Reverse JV;   ~JV     / Reverse Jog Velocity
ILC_SJV_IDX = 0x08  # 08 Signed  JV; +/-JV     / Signed Jog Velocity
ILC_RPR_IDX = 0x09  # 09 Reverse PR;   ~PR     / Reverse Position Relative
ILC_SPR_IDX = 0x0A  # 10 Signed  PR; +/-PR     / Signed Position Relative
ILC_SPA_IDX = 0x0B  # 11 Signed  PA; +/-PA     / Signed Position Absolute
ILC_PVT_IDX = 0x0F  # 15 Execute PVT / Execute PVT

# Error Code Definitions (d1 in ER response)
ERR_INS_SYNT = 0x32  # Instruction's Syntax is wrong.
ERR_INS_NUMB = 0x33  # Instruction's Data are wrong.
ERR_INS_IDXR = 0x34  # Instruction's Sub-Index is wrong.
ERR_SYS_STTM = 0x35  # [TIME] Cannot change system time, while the motor is running.
ERR_MXN_DCSD = 0x3C  # [MXN] Stop Decelleration (SD) is slower than the Decelleration(DC).
ERR_MXN_MRUN = 0x3D  # [MXN] Cannot change or query, while the motor is running.
ERR_MXN_MOFF = 0x3E  # [MXN] Cannot BG, when the motor driver is OFF.
ERR_MXN_MTSD = 0x3F  # [MXN] Cannot BG, when the motor is performing Emergency Stop.
ERR_MXN_BENA = 0x40  # [MXN] Cannot BG, when the motor Brake is Locked.
ERR_MXN_BDIS = 0x41  # [MXN] Cannot turn off the motor driver, when the motor Brake is unlocked.
ERR_MXN_SPOG = 0x42  # [MXN] Cannot set origin (for ABS encoder only), when the motor is running.
ERR_PVT_RUNG = 0x46  # [PVT] Cannot set PV or MP[0], when the motor is running.
ERR_PVT_WPOV = 0x47  # [PVT] Index of QP/QV/QT exceeds MP[6]
ERR_PVT_IOFN = 0x48  # [PVT] QA Mask not meeting I/O function requirements
ERR_PVB_OVFL = 0x49  # [PVT] PVT buffer overflow
ERR_SXP_BUSY = 0x4A  # [PVT] Sx processing not complete, new parameters not accepted

# Frame format constants
FRAME_HEAD = 0xAA
FRAME_TAIL = 0xCC
FRAME_LENGTH = 16
FIXED_DATA_FIELD_LENGTH = 9
EXPECTED_FRAME_LENGTH = 16  # AA + ID + CW + DL + d0~d8(9) + R0 + R1 + CC