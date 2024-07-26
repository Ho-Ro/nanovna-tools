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
            return device
    raise OSError("device not found")


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser( description='Capture a screen shot from NanoVNA or tinySA')
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
ap.add_argument( '-i', '--invert', action = 'store_true',
    help='invert the colors, e.g. for printing' )
ap.add_argument( '-o', '--out',
    help='write the data into file OUT' )
ap.add_argument( '-r', '--rle', action = 'store_true',
    help='use RLE transfer, e.g. for slow serial connections' )

options = ap.parse_args()
outfile = options.out
if options.device:
    device = None
    nano_tiny_device = options.device
else:
    device = getdevice()
    nano_tiny_device = device.device

# The size of the screen (2.8" devices)
width = 320
height = 240

# set by option
if options.tinysa:
    devicename = 'tinySA'
elif options.ultra:
    devicename = 'tinySA Ultra'
    width = 480
    height = 320
elif options.h4:
    devicename = 'NanoVNA-H4'
    width = 480
    height = 320
# get it from USB descriptor (supported by newer FW from DiSlord or Erik)
elif device and 'tinySA4' in device.description:
    devicename = 'tinySA Ultra'
    width = 480
    height = 320
elif device and 'tinySA' in device.description:
    devicename = 'tinySA'
elif device and 'NanoVNA-H4' in device.description:
    devicename = 'NanoVNA-H4'
    width = 480
    height = 320
# fall back to default name
else:
    devicename = 'NanoVNA-H'

# NanoVNA sends captured image as 16 bit RGB565 pixel
size = width * height

crlf = b'\r\n'
prompt = b'ch> '

# do the communication
with serial.Serial( nano_tiny_device, timeout=1 ) as nano_tiny: # open serial connection
    nano_tiny.write( b'\rpause\r' )  # stop screen update
    echo = nano_tiny.read_until( b'pause' + crlf + prompt ) # wait for completion
    if options.rle:
        nano_tiny.write( b'capture rle\rresume\r' )  # request screen capture, type ahead resume
        echo = nano_tiny.read_until( b'capture rle' + crlf ) # wait for start of transfer
        bytestream = nano_tiny.read_until(prompt + b'resume' + crlf + prompt) # wait for completion
        if b'capture?\r\nch> ' in bytestream: # error message
            print( 'capture error - does the device support the "capture" cmd?' )
            sys.exit()
        header,width, height,bpp,compression,psize=struct.unpack_from('<HHHBBH',bytestream,0)
        sptr=0xa
        size=width*height
        palette=struct.unpack_from('<{:d}H'.format(psize),bytestream,sptr)
        sptr=sptr+psize
        bitmap=bytearray(size*2)
        dptr=0
        row=0
        while(row<height):
            #process RLE block
            bsize=struct.unpack_from('<H',bytestream,sptr)[0]
            sptr=sptr+2
            nptr=sptr+bsize
            while(sptr<nptr):
                count=struct.unpack_from('<b',bytestream,sptr)[0]
                sptr+=1
                if(count<0):
                    color=palette[bytestream[sptr]]
                    sptr+=1
                    while(count<=0):
                        count=count+1
                        struct.pack_into('<H',bitmap,dptr,color)
                        dptr+=2
                else:
                    while(count>=0):
                        count=count-1
                        struct.pack_into('<H',bitmap,dptr,palette[bytestream[sptr]])
                        dptr+=2
                        sptr+=1
            row+=1
        captured_bytes=bitmap
    else:
        nano_tiny.write( b'capture\r' )  # request screen capture
        echo = nano_tiny.read_until( b'capture' + crlf ) # wait for start of transfer
        captured_bytes = nano_tiny.read( 2 * size )
        echo = nano_tiny.read_until( prompt ) # wait for cmd completion
        nano_tiny.write( b'resume\r' )  # resume the screen update
        echo = nano_tiny.read_until( b'resume' + crlf + prompt ) # wait for completion
        if len( captured_bytes ) != 2 * size:
            if captured_bytes == b'capture?\r\nch> ': # error message
                print( 'capture error - does the device support the "capture" cmd?' )
            else:
                print( 'capture error - wrong screen size?' )
            sys.exit()

# convert captured_bytes to 1D word array
rgb565 = struct.unpack( f'>{size}H', captured_bytes )
# convert to 32bit numpy array Rrrr.rGgg.gggB.bbbb -> 0000.0000.0000.0000.Rrrr.rGgg.gggB.bbbb
rgb565_32 = numpy.array( rgb565, dtype=numpy.uint32 )

# convert zero padded 16bit RGB565 pixel to 32bit RGBA8888 pixel
# 0000.0000.0000.0000.Rrrr.rGgg.gggB.bbbb -> 1111.1111.Rrrr.r000.Gggg.gg00.Bbbb.b000
# apply invert option for better printing with white background
if options.invert:
    rgba8888 = 0xFF000000 + (((rgb565_32 & 0xF800) >> 8) + ((rgb565_32 & 0x07E0) << 5) + ((rgb565_32 & 0x001F) << 19)) ^ 0x00FFFFFF
else:
    rgba8888 = 0xFF000000 + (((rgb565_32 & 0xF800) >> 8) + ((rgb565_32 & 0x07E0) << 5) + ((rgb565_32 & 0x001F) << 19))

# make an image from pixel array, see: https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.frombuffer
image =  Image.frombuffer('RGBA', ( width, height ), rgba8888, 'raw', 'RGBA', 0, 1)

filename = options.out or datetime.now().strftime( f'{devicename}_%Y%m%d_%H%M%S.png' )

try:
    image.save( filename ) # .. and save it to file (format according extension)
except ValueError: # unknown (or missing) exension
    image.save( filename + '.png' ) # force PNG format
