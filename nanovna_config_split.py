#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Tool to split the config data block of a NanoVNA-H and save them
into individual files for each calibration slot and global config data.

These files can be downloaded to the NanoVNA-H with the program "dfu-util"
"dfu-util --device 0483:df11 --alt 0 --dfuse-address ADDR --download SLOTFILE"

ADDR depends on the FW:

DiSlord´s originalFW
====================
SLOT    ADDR
config  0x0801F800
4       0x0801E000
3       0x0801C800
2       0x0801B000
1       0x08019800
0       0x08018000

FW modified by Ho-Ro (https://github.com/Ho-Ro/NanoVNA-D/tree/NanoVNA-noSD)
===========================================================================
SLOT    ADDR
config  0x0801F800
7       0x0801E000
6       0x0801C800
5       0x0801B000
4       0x08019800
3       0x08018000
2       0x08016800
1       0x08015000
0       0x08013800

Reason:
My FW modification omitted the SD functions, because my NanoVNA-H has no SD card slot.
The increased free flash memory can be used to store 8 calibration slots instead of 5.

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


def decode_slt( config, typ, slot ):
# decode a prop config slot (see properties_t in nanovna.h)
# write slot data into file (if option -s), return the slot data
    slt = b''
    slt += config.read( 28 ) # get the slot properties
    f1, f2, points = struct.unpack( '<4xII14xH', slt )
    slt += config.read( slot_len - len( slt ) ) # read remaining slot data
    name = f'{typ}_{slot}_{f1}_{f2}_{points}.bin'
    print( f'slot {slot}: {f1} Hz ... {f2} Hz, {points} points', end='' )
    if do_split:
        print( f' -> {name}' )
        with open( name, 'wb' ) as f:
            f.write( slt )
    else:
        print()
    return slt


def decode_cfg( config, typ ):
    # decode the config storage (see config_t in nanovna.h)
    # write config data into file (if option -s), return the config data
    cfg = b''
    # cfg += config.read( 100 ) # decode some config values
    # harmonic_f, if_f, vbat_offset, bandwidth, ser_speed, xtal_f  = struct.unpack( '<4xII12xHH64xII', cfg )
    # print( 'C', harmonic_f, if_f, vbat_offset, bandwidth, ser_speed, xtal_f )
    cfg += config.read( cfg_len - len( cfg ) ) # read remaining cfg data
    name = f'{typ}_config.bin'
    print( 'device configuration', end='' )
    if do_split:
        print( f' -> {name}' )
        with open( name, 'wb' ) as f:
            f.write( cfg )
    else:
        print()
    return cfg


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( 'infile', type=argparse.FileType( 'rb' ),
    help='config file' )
ap.add_argument( '-p', '--prefix', default = 'NV-H',
    help='prefix for output files, default: NV-H' )
ap.add_argument( '-s', '--split', action='store_true',
    help='split config file into individual slot files' )
ap.add_argument( '-t', '--transfer', action='store_true',
    help='transfer 5 slot format <-> 8 slot format' )

options = ap.parse_args()
infile = options.infile # read data from this file
prefix = options.prefix # name prefix for individual slot files
do_split = options.split # split into individual slot files
do_transfer = options.transfer # 5 slot <-> 8 slot

sector_len = 0x800 # 2048 bytes
slot_len = 3 * sector_len # = 0x1800
empty = bytearray( slot_len ) # dummy slot
cfg_len = sector_len # = 0x0800

slots = [ [], [], [], [], [], [], [], [] ] # 8 calibration slots
cfg = [] # the config slot

size = os.path.getsize( infile.name )

if size == 5 * slot_len + sector_len: # orig 5 slot format
    index = 0 # start with slot 0
    delta = 1 # bottom-up storage
elif size == 8 * slot_len + sector_len: # noSD 8 slot format
    index = 0 # start with slot 0
    delta = 1 # top-down storage
else:
    print( f'wrong config file size, must be either {0x8000} (5 slots) or {0xC800} (8 slots)' )
    sys.exit()
write_empty = True
while( infile.tell() < size ): # parse and decode the infile
    s = infile.read( 4 )
    infile.seek( -4, 1 )
    magic, = struct.unpack( '<I', s )
    if magic == 0x434f4e54: # 'CONT'
        slots[ index ] = decode_slt( infile, prefix, index )
        index += delta
    elif magic == 0x434f4e56: # 'CONV'
        cfg = decode_cfg( infile, prefix )
    else:
        if write_empty:
            with open( 'empty_config.bin', 'wb' ) as f:
                f.write( b'\xff'*0x800 )
            with open( 'empty_slot.bin', 'wb' ) as f:
                f.write( b'\xff'*0x1800 )
            write_empty = False
        infile.seek( sector_len, 1 ) # skip this sector
infile.close()

if do_transfer: # transfer 5 slot format <-> 8 slot format
    root, ext = os.path.splitext( infile.name )
    if size == 0x8000: # 5 -> 8
        name = f'{root}_5_to_8{ext}'
        print( f'create 8 slot config -> {name}' )
        with open( name, 'wb' ) as f:
            for iii in range( 5 ): # 0..4
                if len( slots[ iii ] ) == slot_len:
                    f.write( slots[ iii ] )
                else:
                    f.write( empty )
            for iii in range( 3 ): # 3 empty slots
                f.write( empty )
            f.write( cfg ) # and finally the config area
    elif size == 0xC800: # 8 -> 5
        name = f'{root}_8_to_5{ext}'
        print( f'create 5 slot config -> {name}' )
        with open( name, 'wb' ) as f:
            for iii in range( 5 ): # start with slot 0..4
                if len( slots[ iii ] ) == slot_len:
                    f.write( slots[ iii ] )
                else:
                    f.write( empty )
            f.write( cfg ) # config area comes last

