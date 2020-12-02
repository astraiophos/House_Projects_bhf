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
import time
import RPi.GPIO as GPIO
from state_log_manager import check_door_state, StateLogManager
from light_sensor import list_average, rc_time, take_measurement
from door_motor import set_sequence, turn_motor, setup_pins


# ----------------------------------------------------------------------------------------------------------------------
# Utility functions


def file_path(mystr):
    if Path(mystr).is_file():
        return mystr
    else:
        raise FileNotFoundError("File path provided does not exist: {}".format(mystr))


def is_float(mystr):
    try:
        float(mystr)
        return True
    except ValueError:
        return False


def float_2_steps(revs, rev_steps="half"):
    """
    This will convert the number of revolutions desired into the proper number of motor steps, depending too on whether
    the half-step or full-step turns are used for turing the motor.
    :param revs:        The number of revolutions (floating point value assumed)
    :param rev_steps:   Accepted choices are "half" or "full"
    :return:
    """
    if rev_steps == 1:
        rev_count = 4096
    elif rev_steps == 2:
        rev_count = 2048
    else:
        raise TypeError("Accepted choices are 'full' or 'half', provided value was: {}".format(rev_steps))
    import decimal
    decimal.getcontext().rounding = decimal.ROUND_DOWN
    revs = decimal.Decimal(revs)
    steps = int(round(decimal.Decimal(revs * rev_count), 0))
    return steps


def str_2_bool(mystr):
    trues = ['t', 'true', '1']
    falses = ['f', 'false', '0']
    mystr = mystr.lower()
    if mystr in trues:
        return True
    elif mystr in falses:
        return False
    else:
        raise TypeError("Cannot convert {} to boolean. Provide acceptable boolean value".format(mystr))


def is_time_between(begin_time, end_time, check_time=None):
    # Credit to @Joe Holloway and @rouble for this answer on stackoverflow.com
    # If check time is not given, default to current UTC time
    check_time = check_time or datetime.datetime.now().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else: # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def is_time_greater(time_limit, check_time=None):
    """
    This will check the current time against the time_limit. If the current time is greater, the function will return
    [True], else it returns False
    :param time_limit:  The time to check against (the deadline or limit)
    :param check_time:  The current time or some other time
    :return:            boolean
    """
    check_time = check_time or datetime.datetime.now().time()
    print("Time limit: {}".format(time_limit.strftime('%H:%M:%S')))
    print("Current Time: {}".format(check_time.strftime('%H:%M:%S')))
    if check_time > time_limit:
        return True
    else:
        return False


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
parser.add_argument('--reading_samples',
                    dest='reading_samples',
                    type=int,
                    default=10,
                    help='This dictates the number of samples to take an average of before reporting the number.\n'
                         'Default is [10].'
                    )
parser.add_argument('--resistor_time',
                    dest='resistor_time',
                    type=int,
                    default=2,
                    help='The number of seconds to wait between checking the photoresistor timing. Default is [2].'
                    )
parser.add_argument('--charging_pin',
                    dest='charging_pin',
                    type=int,
                    default=25,
                    help='The GPIO pin for charging the capacitor, then signaling the reading pin. Default is [25].'
                    )
parser.add_argument('--reading_pin',
                    dest='reading_pin',
                    type=int,
                    default=26,
                    help='The GPIO pin for reading when the capacitor is charged. Default is [26].'
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
                    default=7,
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
                    default=20,
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
                    default=12,
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
        self.check_times = [self.open_check, self.close_check]
        self.open_limit = datetime.time(late_open, 00)
        self.close_limit = datetime.time(late_close, 00)

    def time_to_check(self):
        for frame in self.check_times:
            if is_time_between(begin_time=frame[0], end_time=frame[1]) is True:
                return True
        return False

    def openclose_check(self, action_frame=None):
        if is_time_between(begin_time=self.open_frame[0], end_time=self.open_frame[1]) is True:
            action_frame = 'open'
        elif is_time_between(begin_time=self.close_frame[0], end_time=self.close_frame[1]) is True:
            action_frame = 'close'
        if action_frame is not None:
            door_state_lex = check_door_state()
            if door_state_lex['door_state'] == action_frame:
                return action
            else:
                return None

    def limit_check(self):
        limit_action = None
        if is_time_greater(time_limit=self.open_limit) is True:
            if self.openclose_check('open') == 'open':
                limit_action = 'open'
        if is_time_greater(time_limit=self.close_limit) is True:
            if self.openclose_check('close') == 'close':
                limit_action = 'close'
        return limit_action


# ----------------------------------------------------------------------------------------------------------------------
# Main Program
if __name__ == '__main__':
    try:
        # Use BCM GPIO references instead of physical pin numbers
        GPIO.setmode(GPIO.BCM)
        # Set up the pins for driving the motor for the door
        setup_pins(args.driver_pins)
        # Set up the information for turning the motor the correct number of times
        num_steps = float_2_steps(args.revolutions, args.step_size)
        step_sequence = set_sequence(args.step_size)
        # Establish when to check the photoresistor
        check_times = TimeFrame(args.early_open, args.late_open, args.early_close, args.late_close)
        while True:
            action = None
            print("Checking the available actions based on the time")
            if check_times.time_to_check() is True:
                print("Taking Readings")
                rec_list = [0 for i in range(args.trend_len)]
                i = 0
                reading = take_measurement(
                    charge_pin=args.charging_pin,
                    measure_pin=args.reading_pin,
                    sample_num=args.reading_samples,
                    wtime=args.resistor_time
                )
                rec_list = rec_list[1:] + [reading]
                i += 1
                time.sleep(args.reading_intervals * 60)
                trend = trend_check(rec_list)
                if trend == check_times.openclose_check():
                    action = trend
            elif check_times.limit_check() is not None:
                print("Enforcing limit rules")
                action = check_times.limit_check()
            if action is not None:
                print("The door will {} now".format(action))
                door_info = turn_motor(
                    action=action,
                    seq=step_sequence,
                    seq_steps=num_steps,
                    gpio_pins=args.driver_pins,
                    wait_time=args.step_time
                )
                StateLogManager(log_data=door_info, log_loc=args.state_log)
            else:
                time.sleep(60)
    except KeyboardInterrupt:
        print("Closing the program")
    finally:
        GPIO.cleanup()