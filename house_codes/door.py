#!/usr/bin/python3
"""
Author:         Jacob B Fullerton
Date:           November 24, 2020
Usage:          This code is meant to extend functionality on a raspberry pi board to make use of a stepper motor
                (28BYJ-48) with a driver board (ULN2003) in support of a chicken coop door.
Pseudo Code:    The code in general works in the following manner:
                1.  Accepts user arguments
                2.  Based on the arguments provided, it will turn the motor
                3.  Change the state log of the chicken coop door
"""

import argparse
from pathlib import Path
from house_codes.state_log_manager import StateLogManager
import time
import RPi.GPIO as GPIO


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


def float_2_steps(mystr):
    import decimal
    decimal.getcontext().rounding = decimal.ROUND_DOWN
    if is_float is not False:
        revs = decimal.Decimal(mystr)
        steps = round(decimal.Decimal(revs * 64), 0)
        return steps
    else:
        raise TypeError("Please provide a numeric value: {}".format(mystr))


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


# ----------------------------------------------------------------------------------------------------------------------
# User Input (Parser)


parser = argparse.ArgumentParser()
parser.add_argument('--state_log',
                    dest='state_log',
                    type=file_path,
                    default=Path("../data/state_log.txt"),
                    help='Provide the path to the state log file (the file that tracks the current state of the coop\n'
                         'door. Default location is [../data/state_log.txt] in relation to this script.'
                    )
parser.add_argument('--door_action',
                    dest='open_door',
                    type=str.lower,
                    choices=['open', 'close'],
                    required=True,
                    help='Specify whether you want the door to open or close. Acceptable options are [open] or [close].'
                    )
parser.add_argument('--wait_time',
                    dest='wait_time',
                    type=is_float,
                    default=0.001,
                    help='Specify the amount of time you want to wait between setting the step of the stepper motor.'
                    )
parser.add_argument('--revolutions',
                    dest='open_door',
                    type=float_2_steps,
                    default=3,
                    help='Specify the number of revolutions to turn. This motor operates using half-steps (a total \n'
                         'of 64 half-steps, or 2.8125 degrees per half-step). To specify partial revolutions, use a \n'
                         'floating decimal value (e.g. one half of a revolution is 0.5 revolutions, or 32 half-\n'
                         'steps). Do not type the number of half-steps, but understand that the code will translate\n'
                         'the number of revolutions from a floating point decimal value into the number of steps\n'
                         'needed to drive the motor. The default is [3.0] revolutions.'
                    )


# ----------------------------------------------------------------------------------------------------------------------
# Primary functions

