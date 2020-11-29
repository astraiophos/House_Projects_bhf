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


def float_2_steps(mystr, rev_steps="half"):
    """
    This will convert the number of revolutions desired into the proper number of motor steps, depending too on whether
    the half-step or full-step turns are used for turing the motor.
    :param mystr:       The number of revolutions (floating point value assumed)
    :param rev_steps:   Accepted choices are "half" or "full"
    :return:
    """
    if rev_steps.lower() == 'half':
        rev_count = 64
    elif rev_steps.lower() == 'full':
        rev_count = 32
    else:
        raise TypeError("Accepted choices are 'full' or 'half', provided value was: {}".format(rev_steps))
    import decimal
    decimal.getcontext().rounding = decimal.ROUND_DOWN
    revs = decimal.Decimal(mystr)
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
parser.add_argument('--clockwise',
                    dest='clockwise',
                    type=str_2_bool,
                    required=True,
                    help='Specify the direction you want the motor to turn. If you say [True], the motor will turn\n'
                         'clockwise. If [False], then counterclockwise.'
                    )
parser.add_argument('--wait_time',
                    dest='wait_time',
                    type=is_float,
                    default=0.001,
                    help='Specify the amount of time you want to wait between setting the step of the stepper motor.'
                    )
parser.add_argument('--revolutions',
                    dest='revolutions',
                    type=float,
                    default=3,
                    help='Specify the number of revolutions to turn. This motor operates using half-steps (a total \n'
                         'of 64 half-steps, or 2.8125 degrees per half-step). To specify partial revolutions, use a \n'
                         'floating decimal value (e.g. one half of a revolution is 0.5 revolutions, or 32 half-\n'
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


# ----------------------------------------------------------------------------------------------------------------------
# Primary functions


def set_sequence(step=1):
    """
    This builds and returns a list of the motor stepping sequence for sending the right signal to the driver board.
    If the "step" value is set to 1, then it will return the sequence for half-step-turns on the motor. If set to 2,
    then the full-step-turn sequence will be provided
    :return: List of high-low 4-pin combinations in order (order matters) for stepping the motor.
    """
    seq = [
        [1, 0, 0, 1],
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1]
    ]
    if step == 1:
        return seq
    elif step == 2:
        i = 1
        full_seq = []
        while i < len(seq):
            full_seq.append(seq[i])
            i += 2
        return full_seq

###TODO Need to change the "clockwise" parameter to be "open" or "close" and define "open" as the clockwise direction (matters for how we write the state log)
def turn_motor(clockwise, seq, seq_steps, ):
    """
    This function will turn the motor in the direction specified for the number of revolutions/steps specified.
    :param clockwise:   Boolean defining whether the motor turns clockwise or counterclockwise
    :param seq:         The driver board sequence for turning the motor
    :param seq_steps:   The number of steps in the sequence (repeats allowed)
    :return:
    """
    if clockwise is True:
        step_dir = 1
    elif clockwise is False:
        step_dir = -1
    else:
        raise TypeError("Expected either 'True' or 'False' for the 'clockwise' variable of this function. Provided: {}"
                        "".format(clockwise))

