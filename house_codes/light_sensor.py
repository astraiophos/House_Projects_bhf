#!/usr/bin/python3
"""
Author:         Jacob B Fullerton
Date:           November 30, 2020
Usage:          This code is meant to extend functionality on a raspberry pi board to make use of a photoresistor.
Pseudo Code:    The code in general works in the following manner:
                1.  Accepts user arguments
                2.  Based on the arguments provided, it will take a reading and return the reading
"""

import argparse
import datetime
import time
import RPi.GPIO as GPIO


# ----------------------------------------------------------------------------------------------------------------------
# Utility functions

def list_average(alist):
    """
    Takes the average of a list of values and returns the average
    :param alist: A list of numeric values
    :return:
    """
    return sum(alist)/len(alist)


# ----------------------------------------------------------------------------------------------------------------------
# Primary functions


def rc_time(tpin, mpin):
    """
    This function will take a single reading (not an average) of the photoresistor.
    :param tpin:        The pin used to start charging the capcitor
    :param mpin:        The pin used to measure when the capacitor is fully charged.
    :return:
    """
    # Set both pins to "output mode" then to "no output"
    GPIO.setup(mpin, GPIO.OUT)
    GPIO.setup(tpin, GPIO.OUT)
    GPIO.output(mpin, False)
    GPIO.output(tpin, False)
    # Wait a short period
    time.sleep(0.2)
    # Take the time
    start_time = datetime.datetime.now()
    # Change the measuring pin to "input mode"
    GPIO.setup(mpin, GPIO.IN)
    # Change the timing pin to a high voltage
    GPIO.output(tpin, True)
    # Wait until the measuring pin goes high
    while GPIO.input(mpin) == GPIO.LOW:
        pass
    time_elapsed = datetime.datetime.now() - start_time
    time_elapsed = time_elapsed.total_seconds()
    # Stop charging the capacitor
    GPIO.output(tpin, False)
    return time_elapsed


def take_measurement(
        charge_pin=25,
        measure_pin=26,
        sample_num=10,
        wtime=2
):
    """
    This is the driver function for this script for taking a photoresistor reading.
    :param charge_pin:  The pin which provides a charge to the capacitor.
    :param measure_pin: The pin that measures when the capacitor is fully charged
    :param sample_num:  The number of samples to take for a reading
    :param wtime:       The amount of time to wait before taking a sample reading
    :return:            The number of seconds (on average) the capacitor took to charge fully.
    """
    try:
        # Use BCM GPIO references instead of physical pin numbers
        GPIO.setmode(GPIO.BCM)
        i = 0
        samples = []
        while i < sample_num:
            time.sleep(args.wait_time)
            samples.append(rc_time(tpin=args.charging_pin, mpin=args.measuring_pin))
            i += 1
        reading = list_average(alist=samples)
        return reading
    except KeyboardInterrupt:
        print("Closing the program")
    finally:
        GPIO.cleanup()


# ----------------------------------------------------------------------------------------------------------------------
# Main Program
if __name__ == '__main__':
    # User Input (Parser)

    parser = argparse.ArgumentParser()
    parser.add_argument('--num_samples',
                        dest='num_samples',
                        type=int,
                        default=10,
                        help='This dictates the number of samples to take an average of before reporting the number.\n'
                             'Default is [10].'
                        )
    parser.add_argument('--wait_time',
                        dest='wait_time',
                        type=float,
                        default=2,
                        help='This is the number of seconds to wait between each individual reading (before averaging).\n'
                             'Can accept decimal values.'
                        )
    parser.add_argument('--charging_pin',
                        dest='charging_pin',
                        type=int,
                        default=25,
                        help='If you change the pinout from the Raspberry Pi board, you can change the pins here. The \n'
                             'pin numbers must be the GPIO pins (not to be confused with the physical pin numbering).\n'
                             'This pin represents the pin that passes through the capacitor before looping back to\n'
                             'the measuring pin. Turning this pin on will first charge the capacitor before signaling\n'
                             'the measuring pin as "HIGH", the time will be measured for charging the capacitor.\n'
                             'The default GPIO pin used is [25].'
                        )
    parser.add_argument('--measuring_pin',
                        dest='measuring_pin',
                        type=int,
                        default=26,
                        help='If you change the pinout from the Raspberry Pi board, you can change the pins here. The \n'
                             'pin numbers must be the GPIO pins (not to be confused with the physical pin numbering).\n'
                             'This pin will listen for the signal coming from the "charging_pin", waiting for the signal\n'
                             'to change to "high" when the capacitor is fully charged. The default GPIO pin used is [26].'
                        )
    args = parser.parse_args()