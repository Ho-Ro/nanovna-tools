#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line tool to capture a screen shot from NanoVNA or tinySA
connect via USB serial, issue the command 'capture'
and fetch 320x240 or 480x320 rgb565 pixel.
These pixels are converted to rgb8888 values
that are stored as an image (e.g. png)
'''

import argparse
from datetime import datetime
import serial
from serial.tools import list_ports
import struct
import sys
import numpy
from PIL import Image


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
typ = ap.add_mutually_exclusive_group()
typ.add_argument( '-n', '--nanovna', action = 'store_true',
    help = 'use with NanoVNA-H (default)' )
typ.add_argument( '--h4', action = 'store_true',
    help = 'use with NanoVNA-H4' )
typ.add_argument( '-t', '--tinysa', action = 'store_true',
    help = 'use with tinySA' )
typ.add_argument( '--ultra', action = 'store_true',
    help = 'use with tinySA Ultra' )
ap.add_argument( "-o", "--out",
    help="write the data into file OUT" )

options = ap.parse_args()
outfile = options.out
nanodevice = options.device or getdevice()

# The size of the screen (2.8" devices)
width = 320
height = 240

if options.tinysa:
    devicename = 'tinySA'
elif options.ultra:
    devicename = 'tinySA Ultra' # 4" device
    width = 480
    height = 320
elif options.h4:
    devicename = 'NanoVNA-H4' # 4" device
    width = 480
    height = 320
else:
    devicename = 'NanoVNA-H'

# NanoVNA sends captured image as 16 bit RGB565 pixel
size = width * height

crlf = b'\r\n'
prompt = b'ch> '

# do the communication
with serial.Serial( nanodevice, timeout=1 ) as nano_tiny: # open serial connection
    nano_tiny.write( b'pause\r' )  # stop screen update
    echo = nano_tiny.read_until( b'pause' + crlf + prompt ) # wait for completion
    # print( echo )
    nano_tiny.write( b'capture\r' )  # request screen capture
    echo = nano_tiny.read_until( b'capture' + crlf ) # wait for start of transfer
    # print( echo )
    bytestream = nano_tiny.read( 2 * size )
    echo = nano_tiny.read_until( prompt ) # wait for cmd completion
    # print( echo )
    nano_tiny.write( b'resume\r' )  # resume the screen update
    echo = nano_tiny.read_until( b'resume' + crlf + prompt ) # wait for completion
    # print( echo )

if len( bytestream ) != 2 * size:
    print( 'capture error - wrong screen size?' )
    sys.exit()

# convert bytestream to 1D word array
rgb565 = struct.unpack( f'>{size}H', bytestream )
# convert to 32bit numpy array Rrrr.rGgg.gggB.bbbb -> 0000.0000.0000.0000.Rrrr.rGgg.gggB.bbbb
rgb565_32 = numpy.array( rgb565, dtype=numpy.uint32 )
# convert zero padded 16bit RGB565 pixel to 32bit RGBA8888 pixel
# 0000.0000.0000.0000.Rrrr.rGgg.gggB.bbbb -> 1111.1111.Rrrr.r000.Gggg.gg00.Bbbb.b000
rgba8888 = 0xFF000000 + ((rgb565_32 & 0xF800) >> 8) + ((rgb565_32 & 0x07E0) << 5) + ((rgb565_32 & 0x001F) << 19)

# make an image from pixel array, see: https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.frombuffer
image =  Image.frombuffer('RGBA', ( width, height ), rgba8888, 'raw', 'RGBA', 0, 1)

filename = options.out or datetime.now().strftime( f'{devicename}_%Y%m%d_%H%M%S.png' )

try:
    image.save( filename ) # .. and save it to file (format according extension)
except ValueError: # unknown (or missing) exension
    image.save( filename + '.png' ) # force PNG format
