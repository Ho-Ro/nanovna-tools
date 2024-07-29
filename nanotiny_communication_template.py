#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line template to send a serial shell command to NanoVNA or tinySA:
- Connect via USB serial
- Encode the command string to bytearray
- Send the command + CR
- Get the command echo + CRLF
- Get the response + CRLF + prompt
- Format the response (remove CRLF + prompt)
- Decode the response bytearray to string
- Write the response string to stdout
'''

import argparse
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
            return device.device
    raise OSError("device not found")


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser(
    description =
'''A very simple template to explore the NanoVNA and tinySA serial communication and build own applications.
When called without options it connects to the 1st detected NanoVNA or tinySA.
The script sends the command `vbat` and displays the result.
It does this step-by-step with commented commands to make own modifications easy.''' )

ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to device' )
ap.add_argument( '-D', '--detect', dest = 'detect', default = False, action= 'store_true',
    help = 'detect the NanoVNA or tinySA device and exit' )
ap.add_argument( '-v', '--verbose', dest = 'verbose', default = False, action= 'store_true',
    help = 'be verbose about the communication' )

options = ap.parse_args()

# if option ""-d"" was given, open this device, else autodetect the device
nanodevice = options.device or getdevice()

# option "-D": show device and exit
if options.detect:
    print( nanodevice )
    sys.exit()

# use this command
cmd_string = 'vbat'

# convert the string to a bytearray needed by write()
cmd_bytearray = cmd_string.encode()

cr = b'\r'
lf = b'\n'
crlf = cr + lf
prompt = b'ch> '

# open serial connection and close automatically afte use
with serial.Serial( nanodevice, timeout=1 ) as NanoVNA:

    # send command and options terminated by CR
    if options.verbose:
        print( "Send:   ", cmd_bytearray + cr )
    NanoVNA.write( cmd_bytearray + cr )

    # wait for command echo terminated by CR LF
    echo = NanoVNA.read_until( cmd_bytearray + crlf )
    if options.verbose:
        print( "Echo:   ", echo )

    # get command response bytearray until prompt
    echo = NanoVNA.read_until( crlf + prompt )
    if options.verbose:
        print( "Receive:", echo )

# remove CR LF and prompt, decode the bytearray and write the string to stdout
response_bytearray = echo[ :-len( crlf + prompt ) ]
response_string = response_bytearray.decode()
print( response_string )
