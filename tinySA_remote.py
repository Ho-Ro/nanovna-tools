#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Tool to remote control tinySA
Display the screen
Translate mouse click to touch events
TODO: click is still unreliable
TODO: check why NanoVNA behaves differently (timing?)
'''

import argparse
from datetime import datetime
import serial
from serial.tools import list_ports
import struct
import time

import numpy as np
from PIL import Image
import cv2

# ChibiOS/RT Virtual COM Port
VID = 0x0483 #1155
PID = 0x5740 #22336


# Get tinySA device automatically
def getdevice() -> str:
    device_list = list_ports.comports()
    for device in device_list:
        if device.vid == VID and device.pid == PID:
            #print( device )
            return device.device
    raise OSError("device not found")


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to serial usb device' )
group = ap.add_mutually_exclusive_group()
group.add_argument( '-t', '--tinySA', action = 'store_true',
    help = 'use with tinySA (default)' )
group.add_argument( '-n', '--NanoVNA', action = 'store_true',
    help = 'use with NanoVNA (not yet implemented)' )
ap.add_argument( '-z', '--zoom', dest = 'zoom',
    type = int, action = 'store', choices = (2,3,4), default = 1,
    help = 'zoom the screen image' )

options = ap.parse_args()
tinydevice = options.device or getdevice()
zoom = options.zoom

if options.NanoVNA:
    devicename = 'NanoVNA'
else:
    devicename = 'tinySA'


# The size of the screen
width = 320
height = 240

crlf = b'\r\n'
prompt = b'ch> '


# do the communication
with serial.Serial( tinydevice, timeout=0.1 ) as tinySA: # open serial connection

    def do_region( what ):
        where = tinySA.read( 8 )
        x, y, w, h = struct.unpack( '<HHHH', where )
        if x >= width or y >= height or x+w > width or y+h > height: # dimension too big
            return
        if what == b'bulk':
            #print( f'bulk, x: {x}, y: {y}, w: {w}, h: {h}' )
            size = 2 * w * h
            bytestream = tinySA.read( size ) # read a bytestream
            if len( bytestream ) < size:
                #print( bytestream )
                return
            aow = struct.unpack( f">{w*h}H", bytestream ) # convert to array of words
            rectangle = np.reshape( aow, ( h, w ) ) # make a rectangle
        elif what == b'fill':
            color = tinySA.read( 2 )
            color, = struct.unpack( '>H', color )
            #print( f'fill {hex(color)}, x: {x}, y: {y}, w: {w}, h: {h}' )
            rectangle = np.full( ( h, w ), color, dtype=np.uint16 )
        else:
            return
        rgb565[ y:y+h, x:x+w ] = rectangle # copy into the image at position (y,x)


    def make_image():
        # convert rgb565 array to rgba8888 array
        # Rrrr.rGgg.gggB.bbbb -> Aaaa.aaaa.Rrrr.rrrr.Gggg.gggg.Bbbb.bbbb
        rgba8888 = 0xFF000000 | ((rgb565 & 0xF800) << 8) | ((rgb565 & 0x07E0) << 5) | ((rgb565 & 0x001F) << 3)
        pil_image = Image.fromarray( rgba8888, 'RGBA' ) # create an PIL image
        pil_image = pil_image.resize( ( zoom * width, zoom * height ) ) # scale
        image = np.array( pil_image ) # convert from PIL array to np array
        return image


    # mouse callback function
    def mouse_event( event, x, y, flags, param ):
        global click_pos
        # print( event, x, y, flags, param )
        if event == cv2.EVENT_LBUTTONDOWN:
            click_pos = ( x//zoom, y//zoom ) # remenber click position
        elif event == cv2.EVENT_LBUTTONUP: #
            x, y = click_pos # get position of click
            tinySA.write( f'touch {x} {y}\r'.encode() )
            time.sleep( 0.1 )
            tinySA.write( b'release\r')
            click_pos = ( -1, -1 ) # done


    # save the current image as png with timestamp
    def screenshot( image ):
        fileName = datetime.now().strftime( f'{devicename}_%Y%m%d_%H%M%S.png' )
        cv2.imwrite(fileName, image)


    # Prepare black 2D RGB565 data array
    # IMPORTANT: define as uint32 to allow conversion to rgba8888
    rgb565 = np.zeros( ( height, width ), dtype=np.uint32 )


    # open menu to force screen refresh
    tinySA.write( b'\rtouch 100 100\r' )
    time.sleep( 0.2 )
    tinySA.write( b'release\r')
    time.sleep( 0.2 )

    tinySA.write( b'refresh on\r' )  # request screen remote
    time.sleep( 0.2 )

    # close menu (this redraws the complete screen)
    tinySA.write( b'touch 100 100\r' )
    time.sleep( 0.2 )
    tinySA.write( b'release\r')
    time.sleep( 0.2 )


    cv2.namedWindow( devicename )
    cv2.setMouseCallback( devicename, mouse_event )
    click_pos = None

    NO = 0
    ACTIVE = 1
    YES = 2
    FORCE = 10

    refresh_image = FORCE
    while refresh_image:  # run forever, stop with ^C on commad line or ESC on image
        try:
            if refresh_image >= FORCE:
                # print( 'refresh_image', refresh_image )
                image = make_image() # convert internal data structure into image
                cv2.imshow( devicename, image ) # show it
                key = cv2.waitKey(1)
                if key == 27: # ESC pressed
                    break # exit
                if key == ord( 's' ):
                    screenshot( image )
                elif key == ord( '+' ) and zoom < 4:
                    zoom += 1
                elif key == ord( '-' ) and zoom > 1:
                    zoom -= 1
                refresh_image = ACTIVE

            if tinySA.inWaiting(): # serial data available
                serial_data = tinySA.read_until( b'\r\n' )
                what = serial_data[-6:-2]
                #print( serial_data, what )
                if what == b'bulk' or what == b'fill':
                    do_region( what )
                    refresh_image = YES # image has changed
                else: # no more bulk or fill, device is scanning
                    refresh_image = FORCE # force refresh
                    # print( serial_data, what )
            else: # no serial data, idle, force refresh after 1 s
                time.sleep( 0.1 )
                refresh_image += 1

            if click_pos:
                # print( f'click_pos {click_pos}' )
                if click_pos == ( -1, -1 ): # mouse button was released
                    click_pos = None
                    refresh_image = FORCE # force refresh

        except KeyboardInterrupt:         # ^C pressed, stop measurement
            refresh_image = NO            # exit

    cv2.destroyAllWindows()
    tinySA.write( b'refresh off\r' )  # stop screen remote

