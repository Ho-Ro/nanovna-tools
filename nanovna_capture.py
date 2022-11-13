#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line tool to capture a screen shot from NanoVNA
connect via USB serial, issue the command 'capture'
and fetch 320x240 rgb565 pixel.
These pixels are converted to rgb888 values
that are stored as an image (e.g. png)
'''

import argparse
from datetime import datetime
import serial
from serial.tools import list_ports
import struct
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
group = ap.add_mutually_exclusive_group()
group.add_argument( '-n', '--nanovna', action = 'store_true',
    help = 'use with NanoVNA-H (default)' )
group.add_argument( '-t', '--tinysa', action = 'store_true',
    help = 'use with tinySA' )
ap.add_argument( "-o", "--out",
    help="write the data into file OUT" )

options = ap.parse_args()
outfile = options.out
nanodevice = options.device or getdevice()

if options.tinysa:
    devicename = 'tinySA'
else:
    devicename = 'NanoVNA'


# The size of the screen
width = 320
height = 240

# NanoVNA sends captured image as 16 bit RGB565 pixel
size = width * height * 2
pix_bytes = 2

crlf = b'\r\n'
prompt = b'ch> '

ba = b'' # empty bytearray for received pixel values

# do the communication
with serial.Serial( nanodevice, timeout=1 ) as NanoVNA: # open serial connection
    NanoVNA.write( b'pause\r' )  # stop screen update
    echo = NanoVNA.read_until( b'pause' + crlf + prompt ) # wait for completion
    # print( echo )
    NanoVNA.write( b'capture\r' )  # request screen capture
    echo = NanoVNA.read_until( b'capture' + crlf ) # wait for start of transfer
    # print( echo )
    while( len( ba ) < size ): # read until ready
        ba += NanoVNA.read( size - len( ba ) )
    echo = NanoVNA.read_until( prompt ) # wait for cmd completion
    # print( echo )
    NanoVNA.write( b'resume\r' )  # resume the screen update
    echo = NanoVNA.read_until( b'resume' + crlf + prompt ) # wait for completion
    # print( echo )

# convert bytestream to 1D word array
rgb565 = struct.unpack( ">76800H", ba )
# convert to 32bit numpy array Rrrr.rGgg.gggB.bbbb -> 0000.0000.0000.0000.Rrrr.rGgg.gggB.bbbb
rgb565_32 = numpy.array( rgb565, dtype=numpy.uint32 )
# convert zero padded 16bit RGB565 pixel to 32bit RGBA8888 pixel
# 0000.0000.0000.0000.Rrrr.rGgg.gggB.bbbb -> 1111.1111.Rrrr.r000.Gggg.gg00.Bbbb.b000
rgba8888 = 0xFF000000 + ((rgb565_32 & 0xF800) >> 8) + ((rgb565_32 & 0x07E0) << 5) + ((rgb565_32 & 0x001F) << 19)

# make an image from pixel array, see: https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.frombuffer
image =  Image.frombuffer('RGBA', (320, 240), rgba8888, 'raw', 'RGBA', 0, 1)

filename = options.out or datetime.now().strftime( f'{devicename}_%Y%m%d_%H%M%S.png' )

try:
    image.save( filename ) # .. and save it to file (format according extension)
except ValueError: # unknown (or missing) exension
    image.save( filename + '.png' ) # force PNG format
