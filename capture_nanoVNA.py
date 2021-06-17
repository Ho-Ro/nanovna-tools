#!/usr/bin/python

# SPDX-License-Identifier: GPL-2.0+

'''
Command line tool to capture a screen shot from nanoVNA
connect via USB serial, issue the command 'capture'
and fetch 320x240 rgb565 pixel.
These pixels are converted to rgb888 values
that are stored as an image (e.g. png)
'''

import argparse
from datetime import datetime
import serial
import numpy
from PIL import Image

# define default values
nanoPort = '/dev/ttyACM0'
fileName = datetime.now().strftime("nanoVNA_%Y%m%d_%H%M%S.png")

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( "-o", "--out", default = fileName,
    help="write the data into file OUT" )
ap.add_argument( "-p", "--port", default = nanoPort,
    help="connect to serial port PORT" )

options = ap.parse_args()
outfile = options.out
nanoPort = options.port


# nanoVNA serial commands:
# scan scan_bin data frequencies freq sweep power bandwidth saveconfig clearconfig touchcal
# touchtest pause resume cal save recall trace marker edelay capture vbat tcxo reset smooth
# vbat_offset transform threshold help info version color

# The size of the screen
width = 320
height = 240

# nanoVNA sends captured image in chunks of two lines, each RGB565 pixel has two bytes
chunk_size = 2
pix_bytes = 2

rgb565 = b'' # empty bytearray for received pixel values

crlf = b'\r\n'
prompt = b'ch> '

with serial.Serial( nanoPort, timeout=1 ) as nanoVNA: # open serial connection
    nanoVNA.write( b'pause\r' )  # stop screen update
    echo = nanoVNA.read_until( b'pause' + crlf + prompt ) # wait for completion
    print( echo )
    nanoVNA.write( b'capture\r' )  # request screen capture
    echo = nanoVNA.read_until( b'capture' + crlf ) # wait for start of transfer
    print( echo )
    for chunk in range( int( height / chunk_size ) ): # fetch the picture
        rgb565 += nanoVNA.read( chunk_size * width * pix_bytes ) # two rows of 320 pixel of 16 bit
    echo = nanoVNA.read_until( prompt ) # wait for cmd completion
    print( echo )
    nanoVNA.write( b'resume\r' )  # resume the screen update
    echo = nanoVNA.read_until( b'resume' + crlf + prompt ) # wait for completion
    print( echo )

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

png = Image.fromarray( rgb888, 'RGB' ) # create a png image
png.save( outfile ) # .. and save it to file

