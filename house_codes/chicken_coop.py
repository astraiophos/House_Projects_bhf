#!/usr/bin/python3
"""
Author:         Jacob B Fullerton
Date:           December 1, 2020
Usage:          This code is the automation script for running the raspberry pi with a photoresistor and a motor
                to automate a chicken coop door.
Pseudo Code:    The code in general works in the following manner:
                1.  Takes a reading every 15 minutes from the photocell
                2.  Checks that the readings are either increasing or decreasing in light over the course of 1.25 hours
                    (5 readings). The number of readings can be changed by the user.
                3.  If light is increasing/decreasing consistently over the readings, then it will check the time to
                    verify that the time is within the acceptable window for opening the door (if getting lighter) or
                    closing the door.
                4.  The script will check the state log and make sure the door is not already open/closed before making
                    any action (preventing duplicate actions from happening in a row, damaging the system).
                5.  Continue to run in a loop until the user interrupts the script (meant to run in perpetuity).
"""

import argparse
from pathlib import Path
import datetime
from state_log_manager import check_door_state, StateLogManager
from light_sensor import list_average, rc_time, take_measurement
from door_motor import file_path, is_float, float_2_steps, str_2_bool, set_sequence, turn_motor, setup_pins
import time
import RPi.GPIO as GPIO


# ----------------------------------------------------------------------------------------------------------------------
# Utility functions


def is_time_between(begin_time, end_time, check_time=None):
    # Credit to @Joe Holloway and @rouble for this answer on stackoverflow.com
    # If check time is not given, default to current UTC time
    check_time = check_time or datetime.utcnow().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else: # crosses midnight
        return check_time >= begin_time or check_time <= end_time


# ----------------------------------------------------------------------------------------------------------------------
# User Input (Parser)


parser = argparse.ArgumentParser()
parser.add_argument('--trend_len',
                    dest='trend_len',
                    type=int,
                    default=5,
                    help='The number of consecutive readings for validating what the light trend is. Default is [5].'
                    )
parser.add_argument('--reading_intervals',
                    dest='reading_intervals',
                    type=int,
                    default=15,
                    help='The number of minutes to wait between taking readings. Default is [15].'
                    )
parser.add_argument('--resistor_time',
                    dest='resistor_time',
                    type=int,
                    default=2,
                    help='The number of seconds to wait between checking the photoresistor timing. Default is [2].'
                    )
parser.add_argument('--state_log',
                    dest='state_log',
                    type=file_path,
                    default=Path("../data/state_log.txt"),
                    help='Provide the path to the state log file (the file that tracks the current state of the coop\n'
                         'door. Default location is [../data/state_log.txt] in relation to this script.'
                    )
parser.add_argument('--early_open',
                    dest='early_open',
                    type=int,
                    choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                    default=5,
                    help='The earliest hour of the day (using 24-hour format as integer) door can possibly open.'
                    )
parser.add_argument('--late_open',
                    dest='late_open',
                    type=int,
                    choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                    default=5,
                    help='The latest hour of the day (using 24-hour format as integer) door can possibly open.'
                    )
parser.add_argument('--early_close',
                    dest='early_close',
                    type=int,
                    choices=[13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
                    default=17,
                    help='The earliest hour of the day (using 24-hour format as integer) door can possibly close.'
                    )
parser.add_argument('--late_close',
                    dest='late_close',
                    type=int,
                    choices=[13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
                    default=8,
                    help='The latest hour of the day (using 24-hour format as integer) door can possibly close.'
                    )
parser.add_argument('--step_time',
                    dest='step_time',
                    type=is_float,
                    default=0.001,
                    help='Specify the amount of time you want to wait between setting the step of the stepper motor.\n'
                         'Default is [0.001].'
                    )
parser.add_argument('--revolutions',
                    dest='revolutions',
                    type=float,
                    default=3,
                    help='Specify the number of revolutions to turn. This motor operates using half-steps (a total \n'
                         'of 4096 half-steps, or 0.0879 degrees per half-step). To specify partial revolutions, use a \n'
                         'floating decimal value (e.g. one half of a revolution is 0.5 revolutions, or 2048 half-\n'
                         'steps). Do not type the number of half-steps, but understand that the code will translate\n'
                         'the number of revolutions from a floating point decimal value into the number of steps\n'
                         'needed to drive the motor. The default is [3.0] revolutions.'
                    )
parser.add_argument('--step_size',
                    dest='step_size',
                    choices=[1, 2],
                    type=int,
                    default=1,
                    help='If you want to use the motor in half-step mode, use the value [1]. If you want to try the\n'
                         'motor in full-step mode, use the value [2].'
                    )
parser.add_argument('--driver_pins',
                    dest='driver_pins',
                    nargs=4,
                    default=[17, 22, 23, 24],
                    help='If you change the pinout from the Raspberry Pi board, you can change the pins here. The \n'
                         'pin numbers must be the GPIO pins (not to be confused with the physical pin numbering).\n'
                         'The default GPIO pins used are, [17, 22, 23, 24].'
                    )
args = parser.parse_args()


# ----------------------------------------------------------------------------------------------------------------------
# Primary functions


def trend_check(light_list):
    """
    This will take the readings (whatever length). Assumes that the most recent reading is the final position of the
    list, and that the earliest reading is the first item of the list. If the readings are all trending smaller, the
    function will return 'open'. If the readings are all trending bigger, the function will return 'close'
    In practice, the way this works is smaller numbers mean that there is more light (less resistance), while larger
    values indicates that the resistor is getting less light (higher resistance).
    :param light_list:  The list of recordings from the photoresistor.
    :return:            Returns a string: [open/close].
    """
    val = light_list.pop(0)
    increase = 0
    decrease = 0
    action = None
    for rec in light_list:
        if rec > val:
            increase += 1
        else:
            decrease += 1
        val = rec
    if increase == 0:
        action = 'close'
    elif decrease == 0:
        action = 'open'
    return action


class TimeFrame:
    def __init__(self, early_open, late_open, early_close, late_close):
        """
        Establish the parameters for when the door is allowed to be opened
        :param early_open:  Earliest coop can open
        :param late_open:   Latest coop can open
        :param early_close: Earliest coop can close
        :param late_close:  Latest coop can close
        """
        self.open_frame = [datetime.time(early_open, 00), datetime.time(late_open, 00)]
        self.open_check = [datetime.time(early_open - 2, 30), datetime.time(late_open - 2, 30)]
        self.close_frame = [datetime.time(early_close, 00), datetime.time(late_close, 00)]
        self.close_check = [datetime.time(early_close - 2, 30), datetime.time(late_close - 2, 30)]
    


# ----------------------------------------------------------------------------------------------------------------------
# Main Program
if __name__ == '__main__':
    try:

    except KeyboardInterrupt:
        print("Closing the program")
    finally:
        GPIO.cleanup()