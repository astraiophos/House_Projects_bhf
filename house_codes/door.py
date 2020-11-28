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
                    default=0.01,
                    help='Specify the amount of time you want to wait between setting the step of the stepper motor.'
                    )
parser.add_argument('--revolutions',
                    dest='open_door',
                    type=float_2_steps,
                    default=###TODO,
                    help='Specify the number of revolutions to turn (motor is capable of 32 steps per revolution, or\n'
                         '5.625 degrees of rotation).'
                    )


# ----------------------------------------------------------------------------------------------------------------------
# Primary functions

