#!/usr/bin/python3
# Import required libraries
import time
import RPi.GPIO as GPIO

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Define GPIO signals to use
# Physical pin 22 and 37
# GPIO25, GPIO 26
timing_pin = 25
measure_pin = 26

def rc_time (tpin, mpin):
  count = 0

  # Set both pins to "output mode" then to "no output"
  GPIO.setup(mpin, GPIO.OUT)
  GPIO.setup(tpin, GPIO.OUT)
  GPIO.output(mpin, False)
  GPIO.output(tpin, False)

  # Wait a short period
  time.sleep(0.2)

  # Change the measuring pin to "input mode"
  GPIO.setup(mpin, GPIO.IN)

  # Wait a short period
  time.sleep(0.2)

  # Change the timing pin to a high voltage
  GPIO.output(tpin, True)

  # Count until the pin goes high
  while (GPIO.input(mpin) == GPIO.LOW):
    count += 1

  return count

# Catch when the script is interrupted, cleanup GPIO pins
try:
  # Main script
  while True:
    print(rc_time(timing_pin, measure_pin))
except KeyboardInterrupt:
  pass
finally:
  GPIO.cleanup()