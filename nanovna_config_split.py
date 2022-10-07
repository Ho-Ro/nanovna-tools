#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Tool to split the config data block of a NanoVNA-H and save them
into individual files for each calibration slot and global config data.

These files can be downloaded to the NanoVNA-H4 with the program "dfu-util"
"dfu-util --device 0483:df11 --alt 0 --dfuse-address ADDR --download SLOTFILE"

ADDR depends on the FW:

DiSlord´s originalFW
====================
SLOT    ADDR
config  0x08018000
0       0x08018800
1       0x0801A000
2       0x0801B800
3       0x0801D000
4       0x0801E800

FW modified by Ho-Ro (https://github.com/Ho-Ro/NanoVNA-D/tree/NanoVNA-noSD)
===========================================================================
SLOT    ADDR
config  0x0801F800
0       0x0801E000
1       0x0801C800
2       0x0801B000
3       0x08019800
4       0x08018000
5       0x08016800
6       0x08015000
7       0x08013800

Reason:
My FW modification omitted the SD functions, because my NanoVNA-H has no SD card slot.
The increased free flash memory can be used to store 8 calibration slots instead of 5.
I also reverted the locations of the data and put config on top of flash and the slots
below in descending order. This has the advantage that with increased program size in
future versions the highest slot(s) can be removed and config is untouched, while in
original FW the config date and the low slot(s) will be overwritten 1st.

'''

import argparse
import struct
import sys
import os

########################################################
#
# currently unused, planned for checksum calculation
#
#def rol( x, n ):
#    return int(f"{x:032b}"[n:] + f"{x:032b}"[:n], 2)
#
#def ror( x, n ):
#    return int(f"{x:032b}"[-n:] + f"{x:032b}"[:-n], 2)
#
########################################################


def decode_slot( config, typ, slot ):
# decode a prop config slot (see properties_t in nanovna.h)
# write slot data into file
    cfg = config.read( 28 )
    f1, f2, points = struct.unpack( '<4xII14xH', cfg )
    cfg += config.read( 0x1800 - len( cfg ) )
    name = f'{typ}_{slot}_{f1}_{f2}_{points}.bin'
    print( f'{name} - slot {slot}: {f1} Hz ... {f2} Hz, {points} points' )
    with open( name, 'wb' ) as f:
        f.write( cfg )


def decode_cfg( config, typ ):
    # decode the config storage (see config_t in nanovna.h)
    # write config data into file
    cfg = config.read( 100 )
    # harmonic_f, if_f, vbat_offset, bandwidth, ser_speed, xtal_f  = struct.unpack( '<4xII12xHH64xII', cfg )
    # print( 'C', harmonic_f, if_f, vbat_offset, bandwidth, ser_speed, xtal_f )
    cfg += config.read( 0x0800 - len( cfg ) )
    name = f'{typ}_config.bin'
    print( f'{name} - device configuration' )
    with open( name, 'wb' ) as f:
        f.write( cfg )


fileName='NanoVNA-H_config.bin'

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( '-c', '--config', default = fileName,
    help="read the config data from file CONFIG" )
ap.add_argument( '-p', '--prefix', default = 'NV-H',
    help='prefix for output files, default: NV-H' )

options = ap.parse_args()
CONFIG = options.config
prefix = options.prefix

size = os.path.getsize( CONFIG )

with open( CONFIG, 'rb') as config:
    if ( size == 0x8000 ):
        slot = 0
        delta = 1
    elif( size == 0xC800 ):
        slot = 7
        delta = -1
    else:
        print( f'wrong config file size, must be either {0x8000} (5 slots) or {0xC800} (8 slots)' )
        sys.exit()

    while( config.tell() < size ):
        s = config.read( 4 )
        config.seek( -4, 1 )
        magic, = struct.unpack( '<I', s )
        if magic == 0x434f4e52: # 'CONR'
            decode_slot( config, prefix, slot )
            slot += delta
        elif magic == 0x434f4e55: # 'CONU'
            decode_cfg( config, prefix )

