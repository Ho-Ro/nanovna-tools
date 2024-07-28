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
    print( 'no device found on USB' )
    sys.exit()


def get_rle_bytes( size ):
    result = nano_tiny.read( size )
    if len( result ) != size:
        print( 'read error' )
        echo = nano_tiny.read_until(prompt + b'resume' + crlf + prompt) # wait for completion
        sys.exit()
    return result


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser( description=
    'Capture a screenshot from NanoVNA-H, NanoVNA-H4, tinySA, tinySA Ultra or tinyPFA. '
    'Autodetect the device when connected to USB. '
    'Optional RLE compression if available, especially useful e.g. for slow serial connections.'
)
ap.add_argument( '-b', '--baudrate', dest = 'baudrate',
    help = 'set serial baudrate' )
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to serial device' )
typ = ap.add_mutually_exclusive_group()
typ.add_argument( '-n', '--nanovna', action = 'store_true',
    help = 'use with NanoVNA-H (default)' )
typ.add_argument( '--h4', '--nanovna-h4', action = 'store_true',
    help = 'use with NanoVNA-H4' )
typ.add_argument( '-t', '--tinysa', action = 'store_true',
    help = 'use with tinySA' )
typ.add_argument( '-u', '--ultra', action = 'store_true',
    help = 'use with tinySA Ultra' )
typ.add_argument( '-p', '--tinypfa', action = 'store_true',
    help = 'use with tinyPFA' )
ap.add_argument( '-i', '--invert', action = 'store_true',
    help='invert the colors, e.g. for printing' )
ap.add_argument( '-o', '--out',
    help='write the data into file OUT' )
ap.add_argument( '-r', '--rle', action='store_true',
    help='try rle compression, useful for slow serial connections' )
ap.add_argument( "-s", "--scale",
    help="scale image", type=int, choices=range(1, 11), default=1 )
ap.add_argument( '-v', '--verbose', action = 'store_true',
    help='verbose the communication progress' )

options = ap.parse_args()
outfile = options.out
if options.device:
    device = None
    nano_tiny_device = options.device
else:
    device = getdevice()
    nano_tiny_device = device.device

# The size of the screen (default are 2.8" devices)
width = 320
height = 240

#scale = float( options.scale ) # default = 1

detect_device = ''

# set by option
if options.tinysa:
    detect_device = ' (selected by option)'
    devicename = 'tinySA'
elif options.ultra:
    detect_device = ' (selected by option)'
    devicename = 'tinySA Ultra'
    width = 480
    height = 320
elif options.nanovna:
    detect_device = ' (selected by option)'
    devicename = 'NanoVNA-H'
elif options.h4:
    detect_device = ' (selected by option)'
    devicename = 'NanoVNA-H4'
    width = 480
    height = 320
elif options.tinypfa:
    detect_device = ' (selected by option)'
    devicename = 'tinyPFA'
    width = 480
    height = 320

# get it from USB descriptor (supported by FW from DiSlord or Erik > 2022)
elif device and 'tinySA4' in device.description:
    detect_device = ' detected'
    devicename = 'tinySA Ultra'
    width = 480
    height = 320
elif device and 'tinySA' in device.description:
    detect_device = ' detected'
    devicename = 'tinySA'
elif device and 'NanoVNA-H4' in device.description:
    detect_device = ' detected'
    devicename = 'NanoVNA-H4'
    width = 480
    height = 320
elif device and 'NanoVNA-H' in device.description:
    detect_device = ' detected'
    devicename = 'NanoVNA-H'
elif device and 'tinyPFA' in device.description:
    detect_device = ' detected'
    devicename = 'tinyPFA'
    width = 480
    height = 320

# fall back to default name
else:
    detect_device = ' (default device)'
    devicename = 'NanoVNA-H'

if options.verbose:
    print( f'{devicename}{detect_device} at {nano_tiny_device}')
    print( f'screen size: {width} * {height}')

# NanoVNA sends captured image as 16 bit RGB565 pixel
size = width * height

crlf = b'\r\n'
prompt = b'ch> '

# do the communication
if(options.baudrate!=None):
  baudrate=int(options.baudrate)
  stimeout=int(size*2*2/baudrate*10)
else:
  baudrate=9600
  stimeout=5

with serial.Serial( nano_tiny_device, baudrate=baudrate, timeout=1 ) as nano_tiny: # open serial connection
    if options.verbose:
        print( 'pause screen update' )
    nano_tiny.write( b'\rpause\r' )  # stop screen update
    echo = nano_tiny.read_until( b'pause' + crlf + prompt ) # wait for completion

    if options.verbose:
        print( 'start capturing' )
    if options.rle:
        capture_cmd = b'capture rle'
    else:
        capture_cmd = b'capture'
    nano_tiny.write( capture_cmd + b'\rresume\r' )  # request screen capture, type ahead "resume"
    echo = nano_tiny.read_until( capture_cmd + crlf ) # wait for start of capture

    bytestream = nano_tiny.read( 10 ) # size of RLE header or possible error message
    if b'capture?' in bytestream: # error message, "capture" cmd not known
        bytestream += nano_tiny.read_until( crlf + prompt ) # wait for completion
        print( f'capture error ({bytestream}) - does the device support the "capture" cmd?' )
        sys.exit()

    if options.rle: # is the RLE format supported?
        if options.verbose:
            print( 'check RLE header:' )
        magic, hd_width, hd_height, bpp, compression, psize = struct.unpack('<HHHBBH', bytestream)
        options.rle = options.rle and magic == 0x4d42 and bpp == 8 and compression == 1

    if options.verbose:
        if options.rle:
            print( f'  magic: {hex(magic)}, width: {hd_width}, height: {hd_height}, bpp: {bpp}, compression: {compression}, psize: {psize}' )
        else:
            print( f'  {bytestream}' )

    if options.rle:

        if hd_width != width or hd_height != height:
            print( f'capture error - wrong requested screen size {width} * {height}?' )
            echo = nano_tiny.read_until(prompt + b'resume' + crlf + prompt) # wait for completion
            sys.exit()

        if options.verbose:
            print( 'use compressed RLE format' )

        stimeout = stimeout / height
        if stimeout < 1:
            stimeout = 1
        nano_tiny.timeout=stimeout
        if options.verbose:
            print('download timeout {0:0.1f} s'.format(stimeout))

        sptr=0xa
        size=hd_width*hd_height
        bytestream += get_rle_bytes( psize ) # read palette (psize = byte size)
        palette=struct.unpack_from( '<{:d}H'.format(psize//2), bytestream, sptr ) # uint16!
        sptr=sptr+psize
        bitmap=bytearray(size*2)
        dptr=0
        row=0
        while(row<hd_height):
            #process RLE block
            bytestream += get_rle_bytes( 2 ) # uint16
            bsize=struct.unpack_from('<H',bytestream,sptr)[0]
            sptr=sptr+2
            nptr=sptr+bsize
            while(sptr<nptr):
                bytestream += get_rle_bytes( 1 ) # uint8
                count=struct.unpack_from('<b',bytestream,sptr)[0]
                sptr+=1
                if(count<0):
                    bytestream += get_rle_bytes( 1 ) # uint8
                    color=palette[bytestream[sptr]]
                    sptr+=1
                    while(count<=0):
                        count=count+1
                        struct.pack_into('<H',bitmap,dptr,color)
                        dptr+=2
                else:
                    bytestream += get_rle_bytes( count + 1 ) # uint8
                    while(count>=0):
                        count=count-1
                        struct.pack_into('<H',bitmap,dptr,palette[bytestream[sptr]])
                        dptr+=2
                        sptr+=1
            row+=1
        echo = nano_tiny.read_until(prompt + b'resume' + crlf + prompt) # wait for completion
        if options.verbose:
            print( 'resume screen update' )
            print( f'ready: {echo}' )
        bytestream=bitmap

    else: # RGB565 format
        if options.verbose:
            print( 'use standard RGB565 format' )
        nano_tiny.timeout=stimeout
        if options.verbose:
            print('download timeout {0:0.1f} s'.format(stimeout))
        bytestream += nano_tiny.read( 2 * size - 10 )
        if options.verbose:
            print( f'received {len(bytestream)} image bytes:' )
            print( f'  {bytestream[:10]} ... {bytestream[-10:]}' )
        if len( bytestream ) != 2 * size:
            if options.verbose:
                print( len( bytestream ), 2 * size )
            print( f'capture error - wrong requested screen size {width} * {height}?' )
            sys.exit()
        echo = nano_tiny.read_until( crlf + prompt ) # wait for completion
        if options.verbose:
            print( 'resume screen update' )
            print( f'ready: {echo}' )

if options.verbose:
    print( 'create image' )
# convert bytestream to 1D word array
rgb565 = struct.unpack( f'>{size}H', bytestream )
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

if options.scale != 1:
    image=image.resize( ( options.scale * width, options.scale * height ), resample=0 )

filename = options.out or datetime.now().strftime( f'{devicename}_%Y%m%d_%H%M%S.png' )

if options.verbose:
        print( f'filename: {filename}' )

try:
    image.save( filename ) # .. and save it to file (format according extension)
except ValueError: # unknown (or missing) exension
    image.save( filename + '.png' ) # force PNG format

if options.verbose:
    print( 'done' )
