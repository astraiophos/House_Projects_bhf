#!/usr/bin/python3
# Import required libraries
import sys
import time
import RPi.GPIO as GPIO
 
# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)
 
# Define GPIO signals to use
# Physical pins 11,15,16,18
# GPIO17,GPIO22,GPIO23,GPIO24
StepPins = [17,22,23,24]
 
# Set all pins as output
for pin in StepPins:
  print("Setup pins")
  GPIO.setup(pin,GPIO.OUT)
  GPIO.output(pin, False)
 
# Define advanced sequence
# as shown in manufacturers datasheet
Seq = [[1,0,0,1],
       [1,0,0,0],
       [1,1,0,0],
       [0,1,0,0],
       [0,1,1,0],
       [0,0,1,0],
       [0,0,1,1],
       [0,0,0,1]]
 
StepCount = len(Seq)
StepDir = 1 # Set to 1 or 2 for clockwise
            # Set to -1 or -2 for anti-clockwise
 
# Read wait time from command line
if len(sys.argv) > 1:
  WaitTime = int(sys.argv[1])/float(1000)
else:
  WaitTime = 10/float(1000)
 
# Initialise variables
StepCounter = 0
 
# Start main loop
try:
  while True:
 
    print(StepCounter)
    print(Seq[StepCounter])
 
    for pin in range(0, 4):
      xpin = StepPins[pin]#
      if Seq[StepCounter][pin]!=0:
        print("Enable GPIO %i" %(xpin))
        GPIO.output(xpin, True)
      else:
        GPIO.output(xpin, False)
 
    # If we reach the end of the sequence
    # start again
    if (StepCounter == StepCount - 1):
      StepCounter = 0
    elif (StepCounter < StepCount - 1):
      StepCounter += StepDir
 
    # Wait before moving on
    time.sleep(WaitTime)
except KeyboardInterrupt:
    print("Closing the program")
finally:
    GPIO.cleanup()

