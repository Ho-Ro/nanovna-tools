#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line tool to read the RTC of NanoVNA-H or NanoVNA-H4 and sync it with the system time
'''

import argparse
from datetime import datetime
import serial
from serial.tools import list_ports
import sys


# ChibiOS/RT Virtual COM Port
VID = 0x0483 #1155
PID = 0x5740 #22336

# Get nanovna device automatically
def getdevice() -> str:
    device_list = list_ports.comports()
    for device in device_list:
        if device.vid == VID and device.pid == PID:
            return device
    raise OSError("device not found")


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser( description='Show and sync the RTC time of NanoVNA-H or NanoVNA-H4' )
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to device' )
ap.add_argument( '-s', '--sync', action = 'store_true',
    help = 'sync the NanoVNA time to the system time' )

options = ap.parse_args()

if options.device:
    device = None
    nano_tiny_device = options.device
else:
    device = getdevice()
    nano_tiny_device = device.device

cr = b'\r'
crlf = b'\r\n'
prompt = b'ch> '


# do the communication
with serial.Serial( nano_tiny_device, timeout=1 ) as nano_tiny: # open serial connection

    nano_tiny.write( b'time' + cr )  # get date and time
    echo = nano_tiny.read_until( b'time' + crlf ) # wait for start of cmd
    echo = nano_tiny.read_until( crlf ) # get 1st part of answer
    print( f'NanoVNA time: {echo[:-2].decode().replace( "/", "-")}' )
    echo = nano_tiny.read_until( crlf ) # skip 2nd part (usage)
    echo = nano_tiny.read_until( prompt ) # wait for cmd completion
    if echo != prompt: # error
        print( 'timesync error - does the device support the "time" cmd?' )
        sys.exit()

    now = datetime.now()
    print( f'System time:  {now.strftime( "%04Y-%02m-%02d %02H:%02M:%02S" )}' )

    if options.sync:
        time_cmd = now.strftime( 'time b 0x%02y%02m%02d 0x%02H%02M%02S' ).encode()
        nano_tiny.write( time_cmd + cr )  # set date and time
        echo = nano_tiny.read_until( time_cmd + crlf ) # wait for start of cmd
        echo = nano_tiny.read_until( prompt ) # wait for cmd completion

        if echo != prompt: # error
            print( 'timesync error - does the device support the "time b ..." cmd?' )
            sys.exit()
        else:
            print( 'Time sync ok' )

