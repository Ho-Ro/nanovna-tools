#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line tool to read the RTC of NanoVNA-H or NanoVNA-H4 and sync it with the system time
'''

import argparse
from datetime import datetime
import serial
from serial.tools import list_ports
import sys
import platform
from pathlib import Path


# ChibiOS/RT Virtual COM Port
VID = 0x0483 #1155
PID = 0x5740 #22336

# Get nanovna device automatically
def getdevice() -> str:
    device_list = list_ports.comports()
    for device in device_list:
        if device.vid == VID and device.pid == PID:
            return device
    raise OSError( 'device not found' )


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser( description='Show and sync the RTC time of NanoVNA-H or NanoVNA-H4' )
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to device' )
ap.add_argument( '-s', '--sync', action = 'store_true',
    help = 'sync the NanoVNA time to the system time' )
ap.add_argument( '-p', '--ppm', action = 'store_true',
    help = 'calculate RTC ppm deviation since last sync' )
options = ap.parse_args()

if options.device:
    device = None
    nano_tiny_device = options.device
else:
    device = getdevice()
    nano_tiny_device = device.device

cr = b'\r'
crlf = b'\r\n'
prompt = b'ch> '


def get_config_name( progname, filename ):
    # check the os of pc
    MACOS, LINUX, WINDOWS = (platform.system() == x for x in ['Darwin', 'Linux', 'Windows'])   

    # Return the appropriate config directory for each operating system
    if WINDOWS:
        path = Path.home() / 'AppData' / 'Local' / progname
    elif MACOS:  # macOS
        path = Path.home() / 'Library' / 'Application Support' / progname
    elif LINUX:
        path = Path.home() / '.config' / progname
    else:
        raise ValueError(f'unsupported operating system: {platform.system()}')

    # Create the subdirectory if it does not exist
    path.mkdir(parents=True, exist_ok=True)
    # path for config storage
    return path / filename


def get_system_time():
    now = datetime.now()
    second = now.second
    while True:
        now = datetime.now()
        if now.second != second:
            break
    print( f'System time: {now.strftime( "%Y-%m-%d %H:%M:%S" )}' )
    return now # datetime object


def show_device_time( nano_tiny ):
    time_cmd = 'time'.encode()
    nano_tiny.write( time_cmd + cr )  # get date and time
    echo = nano_tiny.read_until( time_cmd + crlf ) # wait for start of cmd
    nano_time = nano_tiny.read_until( crlf ) # get 1st part of answer
    echo = nano_tiny.read_until( crlf ) # skip 2nd part (usage)
    echo = nano_tiny.read_until( prompt ) # wait for cmd completion
    if echo != prompt: # error
        print( 'timesync error - does the device support the "time" cmd?' )
        sys.exit()
    nano_time = nano_time.decode().strip().replace( "/", "-") # convert to string
    print( f'Device time: {nano_time}' )
    return datetime.strptime( nano_time , '%Y-%m-%d %H:%M:%S' ) # datetime object


def sync_device_time( nano_tiny, now ):
    time_b_cmd = now.strftime( 'time b 0x%y%m%d 0x%H%M%S' ).encode()
    nano_tiny.write( time_b_cmd + cr )  # set date and time
    echo = nano_tiny.read_until( time_b_cmd + crlf ) # wait for start of cmd
    echo = nano_tiny.read_until( prompt ) # wait for cmd completion

    if echo != prompt: # error
        print( 'timesync error - does the device support the "time b ..." cmd?' )
        sys.exit()
    return True


# do the communication
with serial.Serial( nano_tiny_device, timeout=1 ) as nano_tiny: # open serial connection
    nano_tiny.write( cr )
    echo = nano_tiny.read_until( prompt ) # remove spurious bytes
    if options.sync or options.ppm:
        lsync_name = get_config_name( 'nanovna_time', 'lastsync' )
    now = get_system_time()
    if options.sync:
        sync_device_time( nano_tiny, now )
        with open( lsync_name, 'w' ) as lsync_file:
            lsync_file.write( now.strftime( "%Y-%m-%d %H:%M:%S" ) )
    else:
        devtime = show_device_time( nano_tiny )
        difference = int( 0.5 + ( devtime - now ).total_seconds() )
        print( f'Difference:  {difference} s' )
        if options.ppm:
            try:
                with open( lsync_name, 'r' ) as lsync_file:
                    lastsync = lsync_file.readline()
                lastsync = datetime.strptime( lastsync , '%Y-%m-%d %H:%M:%S' ) # datetime object
                seconds = int( 0.5 + ( now - lastsync ).total_seconds() )
                hours = int( 0.5 + seconds / 60 / 60 )
                days = int( 0.5 + seconds / 60 / 60 / 24 )
                if days >= 10:
                    print( f'Last sync:   {lastsync}, {days} days ago' )
                elif hours >= 6:
                    print( f'Last sync:   {lastsync}, {hours} h ago' )
                else:
                    print( f'Last sync:   {lastsync}, {seconds} s ago' )
                print( f'Deviation:   {int( 0.5 + 1e6 * difference / seconds )} ppm' )
            except FileNotFoundError:
                print( 'Last sync date not known' )
