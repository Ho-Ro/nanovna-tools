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

# define default values
fileName = datetime.now().strftime("NanoVNA_%Y%m%d_%H%M%S.png")

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to device' )
ap.add_argument( "-o", "--out", default = fileName,
    help="write the data into file OUT" )

options = ap.parse_args()
outfile = options.out
nanodevice = options.device or getdevice()


# The size of the screen
width = 320
height = 240

# NanoVNA sends captured image in chunks of two lines, each RGB565 pixel has two bytes
chunk_size = 2
pix_bytes = 2

rgb565 = b'' # empty bytearray for received pixel values

crlf = b'\r\n'
prompt = b'ch> '

# do the communication
with serial.Serial( nanodevice, timeout=1 ) as NanoVNA: # open serial connection
    NanoVNA.write( b'pause\r' )  # stop screen update
    echo = NanoVNA.read_until( b'pause' + crlf + prompt ) # wait for completion
    # print( echo )
    NanoVNA.write( b'capture\r' )  # request screen capture
    echo = NanoVNA.read_until( b'capture' + crlf ) # wait for start of transfer
    # print( echo )
    for chunk in range( int( height / chunk_size ) ): # fetch the picture
        rgb565 += NanoVNA.read( chunk_size * width * pix_bytes ) # two rows of 320 pixel of 16 bit
    echo = NanoVNA.read_until( prompt ) # wait for cmd completion
    # print( echo )
    NanoVNA.write( b'resume\r' )  # resume the screen update
    echo = NanoVNA.read_until( b'resume' + crlf + prompt ) # wait for completion
    # print( echo )

# Prepare black RGB888 data array
rgb888 = numpy.zeros( ( height, width, 3 ), dtype=numpy.uint8 )

pixel = 0 # iterate over all pixels
for row in range( height ):
    for col in range( width ):
        # fetch big endian uint16
        msb = rgb565[ pix_bytes * pixel ]
        lsb = rgb565[ pix_bytes * pixel + 1 ]
        # RrrrrGgg.gggBbbbb
        # decode rgb565 -> rgb888
        r8 = msb & 0xf8
        g8 = ( msb & 0x07 ) << 5 | ( lsb & 0xe0 ) >> 3
        b8 = ( lsb & 0x1f ) << 3
        # write three colour bytes
        rgb888[ row, col ] = [ r8, g8, b8 ]
        pixel += 1 # next pixel
    # clear last column because of random artifacts in some lines
    rgb888[ row, width - 1 ] = [ 0, 0, 0 ]

image = Image.fromarray( rgb888, 'RGB' ) # create an image
image.save( outfile ) # .. and save it to file (format according extension)

