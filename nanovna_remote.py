#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Tool to remote control NanoVNA-H or tinySA
Display the screen with zoom 1x, 2x, 3x, 4x
Translate mouse click to touch events
Save a screenshot with timestamp name
'''

import argparse
from datetime import datetime
import serial
from serial.tools import list_ports
import struct
import sys
import time

import numpy as np
from PIL import Image
import cv2

# ChibiOS/RT Virtual COM Port
VID = 0x0483 #1155
PID = 0x5740 #22336


# Get NanoVNA-H or tinySA device automatically
def getdevice() -> str:
    device_list = list_ports.comports()
    for device in device_list:
        if device.vid == VID and device.pid == PID:
            return device
    raise OSError("device not found")


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to serial usb device' )
typ = ap.add_mutually_exclusive_group()
typ.add_argument( '-n', '--nanovna', action = 'store_true',
    help = 'use with NanoVNA-H (default)' )
typ.add_argument( '--h4', action = 'store_true',
    help = 'use with NanoVNA-H4' )
typ.add_argument( '-t', '--tinysa', action = 'store_true',
    help = 'use with tinySA' )
typ.add_argument( '--ultra', action = 'store_true',
    help = 'use with tinySA Ultra' )
ap.add_argument( '-z', '--zoom', dest = 'zoom',
    type = int, action = 'store', choices = (2,3,4), default = 1,
    help = 'zoom the screen image' )

options = ap.parse_args()
if options.device:
    device = None
    nano_tiny_device = options.device
else:
    device = getdevice()
    nano_tiny_device = device.device

zoom = options.zoom

# The size of the screen
width = 320
height = 240

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
elif device and 'tinysa' in device.description.lower():
    devicename = 'tinySA'
else: # set default name
    devicename = 'NanoVNA-H'

crlf = b'\r\n'
prompt = b'ch> '

# do the communication
with serial.Serial( nano_tiny_device, timeout=0.5) as nano_tiny: # open serial connection

    def do_region( what ):
        where = nano_tiny.read( 8 )
        x, y, w, h = struct.unpack( '<HHHH', where )
        if x >= width or y >= height or x+w > width or y+h > height: # dimension too big
            print( 'dimension error:', x, y, x+w, y+h )
            return
        if what == b'bulk':
            #print( f'bulk, x: {x}, y: {y}, w: {w}, h: {h}' )
            size = w * h
            bytestream = nano_tiny.read( 2 * size ) # read a bytestream
            if len( bytestream ) < 2 * size:
                #print( bytestream )
                return
            words = struct.unpack( f">{size}H", bytestream ) # convert to array of words
            rectangle = np.reshape( words, ( h, w ) ) # make a rectangle
        elif what == b'fill':
            color = nano_tiny.read( 2 )
            color, = struct.unpack( '>H', color )
            # print( f'fill {hex(color)}, x: {x}, y: {y}, w: {w}, h: {h}' )
            rectangle = np.full( ( h, w ), color, dtype=np.uint16 )
        else:
            return
        RGB565[ y:y+h, x:x+w ] = rectangle # broadcast into the image at position (y,x)
        return


    def make_image():
        # convert RGB565 array to RGBA8888 array
        # Rrrr.rGgg.gggB.bbbb -> Aaaa.aaaa.Rrrr.rrrr.Gggg.gggg.Bbbb.bbbb
        rgba8888 = 0xFF000000 | ((RGB565 & 0xF800) << 8) | ((RGB565 & 0x07E0) << 5) | ((RGB565 & 0x001F) << 3)
        pil_image = Image.fromarray( rgba8888, 'RGBA' ) # create a PIL image
        image = np.array( pil_image ) # convert from PIL array to np array
        if zoom != 1:
            image = cv2.resize( image, (zoom * width, zoom * height) ) # resize
        return image


    # mouse callback function
    def mouse_event( event, x, y, flags, param ):
        # print( event, x, y, flags, param )
        if event == cv2.EVENT_LBUTTONDOWN:
            nano_tiny.write( f'touch {x // zoom} {y // zoom}\r'.encode() )
        elif event == cv2.EVENT_LBUTTONUP: #
            time.sleep( 0.1 )
            nano_tiny.write( b'release\r')


    # save the current image as png with timestamp
    def screenshot( image ):
        fileName = datetime.now().strftime( f'{devicename}_%Y%m%d_%H%M%S.png' )
        cv2.imwrite(fileName, image)



    while nano_tiny.inWaiting(): # clear serial buffer
        nano_tiny.read( nano_tiny.inWaiting() )
        time.sleep( 0.1)

    cmd = b'capture'
    nano_tiny.write( cmd + b'\r' )
    nano_tiny.read_until( cmd + b'\r\n' )
    size = width * height
    bytestream = nano_tiny.read( 2 * size ) # read a bytestream
    if len( bytestream ) != 2 * size:
        if bytestream == cmd + b'?\r\nch> ': # error message
            print( 'capture error - does the device support the "capture" cmd?' )
        else:
            print( 'capture error - wrong screen size?' )
        sys.exit()



    words = struct.unpack( f'>{size}H', bytestream ) # convert to array of words
    rectangle = np.reshape( words, ( height, width ) ) # make a rectangle

    # Prepare black 2D RGB565 data array
    # IMPORTANT: define as uint32 to allow conversion to RGBA8888
    RGB565 = np.zeros( ( height, width ), dtype=np.uint32 )
    RGB565[ 0:height, 0:width ] = rectangle # broadcast the captured screen

    nano_tiny.write( b'refresh on\r' )  # request screen remote
    nano_tiny.read_until( b'refresh on\r\n' )
    time.sleep( 0.2 )

    cv2.namedWindow( devicename )
    cv2.setMouseCallback( devicename, mouse_event )
    click_pos = None

    NO = 0
    YES = 1
    FORCE = 10

    refresh_image = FORCE
    while refresh_image:  # run forever, stop with ^C on commad line or ESC on image
        try:
            next_action = nano_tiny.read_until( b'\r\n')
            if b'bulk' in next_action:
                do_region( b'bulk' )
                refresh_image +=1 # image has changed
            elif b'fill' in next_action:
                do_region( b'fill' )
                refresh_image +=1 # image has changed
            elif b'ch> ' in next_action: # scanning, currently no more regions, image ready
                #print( next_action )
                refresh_image = FORCE
            else: # no serial data, idle, force refresh after some time
                #print( next_action )
                time.sleep( 0.1 )
                refresh_image += 5

            if refresh_image >= FORCE:
                #print( 'refresh_image', refresh_image )
                image = make_image() # convert internal data structure into image
                cv2.imshow( devicename, image ) # show it
                key = cv2.waitKey(1)
                if key < 0: # no key pressed
                    refresh_image = YES
                elif key == 27: # ESC pressed
                    refresh_image = NO
                elif key == ord( 's' ):
                    screenshot( image )
                elif key == ord( '+' ) and zoom < 4:
                    zoom += 1
                elif key == ord( '-' ) and zoom > 1:
                    zoom -= 1
                else: # ignore all other keys
                    refresh_image = YES

        except KeyboardInterrupt:         # ^C pressed, stop measurement
            refresh_image = NO            # exit

    print( 'cleaning up ...' )

    nano_tiny.write( b'refresh off\r' )  # stop screen remote
    time.sleep( 1  )

    cv2.destroyAllWindows()

    while nano_tiny.inWaiting(): # clear serial buffer
        nano_tiny.read( nano_tiny.inWaiting() )
        time.sleep( 0.02 )

