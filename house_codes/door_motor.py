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
import datetime
from state_log_manager import check_door_state, StateLogManager
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
                    dest='door_action',
                    choices=['open', 'close'],
                    type=str.lower,
                    required=True,
                    help='Specify the direction you want the motor to turn. If you say [open] the motor will rotate\n'
                         'clockwise. If [close], then the motor will turn counterclockwise.'
                    )
parser.add_argument('--wait_time',
                    dest='wait_time',
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


def turn_motor(action, seq, seq_steps, gpio_pins, wait_time):
    """
    This function will turn the motor in the direction specified for the number of revolutions/steps specified.
    :param action:      Boolean defining whether the motor turns clockwise or counterclockwise
    :param seq:         The driver board sequence for turning the motor
    :param seq_steps:   The number of steps in the sequence (repeats allowed)
    :param gpio_pins:   The GPIO pins to use for in1, in2, in3, and in4 on the driver board (in order)
    :param wait_time:   The time to wait between each step or half-step
    :return:
    """
    if action == 'open':
        step_dir = 1
    elif action == 'close':
        step_dir = -1
    i = 0
    counter = 0
    while i < seq_steps:
        print("On step: {}".format(i))
        print("Total steps: {}".format(seq_steps))
        for pin in range(0, 4):
            xpin = gpio_pins[pin]
            if seq[counter][pin] != 0:
                GPIO.output(xpin, True)
            else:
                GPIO.output(xpin, False)
        # If we reach the end of the sequence start again
        if abs(counter) == len(seq) - 1:
            counter = 0
        elif abs(counter) < len(seq) - 1:
            counter += step_dir
        # Wait before moving on and increase counter for sequence steps
        i += 1
        time.sleep(wait_time)
    door_state = {'door_state': action, 'time': datetime.datetime.now()}
    return door_state


def setup_pins(gpio_pins):
    """
    Setup the GPIO pins for output
    :param gpio_pins:   The GPIO pins to set up
    :return:
    """
    # Set all pins as output
    for pin in gpio_pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, False)


# ----------------------------------------------------------------------------------------------------------------------
# Main Program
if __name__ == '__main__':
    try:
        cur_status = check_door_state(args.state_log)
        if args.door_action == cur_status['door_state']:
            if args.door_action == 'open':
                print("The door has already been {}ed.".format(args.door_action))
            else:
                print("The door has already been {}d.".format(args.door_action))
        else:
            # Use BCM GPIO references instead of physical pin numbers
            GPIO.setmode(GPIO.BCM)
            setup_pins(args.driver_pins)
            # Find the number of steps to make the number of revolutions specified by the user
            num_steps = float_2_steps(args.revolutions, args.step_size)
            step_sequence = set_sequence(args.step_size)
            door_info = turn_motor(
                action=args.door_action,
                seq=step_sequence,
                seq_steps=num_steps,
                gpio_pins=args.driver_pins,
                wait_time=args.wait_time
            )
            StateLogManager(log_data=door_info, log_loc=args.state_log)
    except KeyboardInterrupt:
        print("Closing the program")
    finally:
        GPIO.cleanup()
