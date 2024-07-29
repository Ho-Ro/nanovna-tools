#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line tool to send a serial shell command to NanoVNA or tinySA:
Connect via USB serial, issue the command and get the response.
Write the response (without the following prompt) to stdout or a file.
NanoVNA serial commands:
scan scan_bin data frequencies freq sweep power bandwidth saveconfig clearconfig touchcal
touchtest pause resume cal save recall trace marker edelay capture vbat tcxo reset smooth
vbat_offset transform threshold help info version color
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
ap = argparse.ArgumentParser()
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to device' )
ap.add_argument( '-D', '--detect', dest = 'detect', default = False, action= 'store_true',
    help = 'detect the NanoVNA device' )
ap.add_argument( '-o', '--out', nargs = '?', type=argparse.FileType( 'wb' ),
    help = 'write output to FILE, default = sys.stdout', metavar = 'FILE', default = sys.stdout )
ap.add_argument( 'command', metavar = 'CMD', nargs = '*', action = 'append',
    help = 'command and arguments' )

options = ap.parse_args()

nanodevice = options.device or getdevice()
outfile = options.out

if options.detect:
    print( nanodevice )
    sys.exit()

cmdline = ''

for cmd in options.command[ 0 ]:
    cmdline = cmdline + cmd + ' '

cmdline = cmdline[ : -1 ].encode() # convert string to bytearray

cr = b'\r'
lf = b'\n'
crlf = cr + lf
prompt = b'ch> '

with serial.Serial( nanodevice, timeout=1 ) as NanoVNA: # open serial connection
    NanoVNA.write( cmdline + cr )                     # send command and options terminated by CR
    echo = NanoVNA.read_until( cmdline + crlf )       # wait for command echo terminated by CR LF
    echo = NanoVNA.read_until( crlf + prompt )        # get command response until prompt

response = echo[ :-len( crlf + prompt ) ]             # remove '\r\nch> '

if outfile == sys.stdout:
    print( response.decode() )                        # write string to stdout
else:
    outfile.write( response + lf )                    # write bytes to outfile
