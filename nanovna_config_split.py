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

max_slot_orig = 5

max_slot_noSD = 8

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


# typedef struct config {
#   uint32_t magic;
#   uint32_t _harmonic_freq_threshold;
#   int32_t  _IF_freq;
#   int16_t  _touch_cal[4];
#   uint16_t _vna_mode;
#   uint16_t _dac_value;
#   uint16_t _vbat_offset;
#   uint16_t _bandwidth;
#   uint8_t  _lever_mode;
#   uint8_t  _brightness;
#   uint16_t _lcd_palette[MAX_PALETTE=32];
#   uint32_t _serial_speed;
#   uint32_t _xtal_freq;
#   float    _measure_r;
#   uint8_t  _band_mode;
#   uint8_t  _reserved[3];
#   uint32_t checksum;
# } config_t;

def decode_cfg( config, typ ):
    # decode the config storage (see config_t in nanovna.h)
    # write config data into file (if option -s), return the config data
    cfg = b''
    # cfg += config.read( 104 ) # decode some config values
    # magic, harmonic_f, IF, vbat_offset, bw, serial_speed, xtal_freq  \
    #     = struct.unpack( '<III8x2x2xHH4x64xII', cfg )
    cfg += config.read( cfg_len - len( cfg ) ) # read remaining cfg data
    name = f'{typ}_config.bin'
    print( 'device configuration', end='' )
    if do_split:
        print( f' -> {name}' )
        with open( name, 'wb' ) as f:
            f.write( cfg )
    else:
        print()
    # print( f'CFG: harmonic f: {harmonic_f} Hz, IF: {IF} Hz, vbat_offset: {vbat_offset} mV, '
    #        f'bandwidth: {4000//(bw+1)} Hz, serial_speed: {serial_speed} bps, xtal_freq: {xtal_freq} Hz' )
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
    help=f'transfer {max_slot_orig} slot format <-> {max_slot_noSD} slot format' )

options = ap.parse_args()
infile = options.infile # read data from this file
prefix = options.prefix # name prefix for individual slot files
do_split = options.split # split into individual slot files
do_transfer = options.transfer # orig slot num <-> noSD slot num

sector_len = 0x800 # 2048 bytes
slot_len = 3 * sector_len # = 0x1800
cfg_len = sector_len # = 0x0800
empty_slot = bytearray( slot_len ) # dummy slot
empty_cfg = bytearray( cfg_len ) # dummy cfg

slots = [ [], [], [], [], [], [], [], [] ] # 8 calibration slots
cfg = [] # the config slot

size = os.path.getsize( infile.name )

file_size_orig = max_slot_orig * slot_len + sector_len
file_size_noSD = max_slot_noSD * slot_len + sector_len

if size == file_size_orig: # orig 5 slot format
    index = 0 # start with slot 0
    delta = 1 # bottom-up storage
elif size == file_size_noSD: # noSD 8 slot format
    index = 0 # start with slot 0
    delta = 1 # top-down storage
else:
    print( f'wrong config file size, must be either {file_size_orig} ({max_slot_orig} slots) '
           f'or {file_size_noSD} ({max_slot_noSD} slots)' )
    sys.exit()

while( infile.tell() < size ): # parse and decode the infile
    s = infile.read( 4 )
    infile.seek( -4, 1 )
    magic, = struct.unpack( '<I', s )
    if magic == 0x434F4E54: # 'CONT'
        slots[ index ] = decode_slt( infile, prefix, index )
        index += delta
    elif magic == 0x434F4E56: # 'CONV'
        cfg = decode_cfg( infile, prefix )
    else:
        infile.seek( sector_len, 1 ) # skip this sector
infile.close()

with open( 'empty_config.bin', 'wb' ) as f:
    f.write( empty_cfg )
with open( 'empty_1_slot.bin', 'wb' ) as f:
    f.write( empty_slot )
with open( 'empty_2_slots.bin', 'wb' ) as f:
    f.write( empty_slot * 2 )
with open( 'empty_4_slots.bin', 'wb' ) as f:
    f.write( empty_slot * 4 )

if do_transfer: # transfer 5 slot format <-> 8 slot format
    root, ext = os.path.splitext( infile.name )
    if size == file_size_orig: # 5 -> 8
        name = f'{root}_{max_slot_orig}_to_{max_slot_noSD}{ext}'
        print( f'create {max_slot_noSD} slot config -> {name}' )
        with open( name, 'wb' ) as f:
            for iii in range( max_slot_orig ): # 0..4
                if len( slots[ iii ] ) == slot_len:
                    f.write( slots[ iii ] )
                else:
                    f.write( empty_slot )
            for iii in range( max_slot_noSD - max_slot_orig ): # 3 empty slots
                f.write( empty_slot )
            f.write( cfg ) # and finally the config area
    elif size == file_size_noSD: # 8 -> 5
        name = f'{root}_{max_slot_noSD}_to_{max_slot_orig}{ext}'
        print( f'create {max_slot_orig} slot config -> {name}' )
        with open( name, 'wb' ) as f:
            for iii in range( max_slot_orig ): # start with slot 0..4
                if len( slots[ iii ] ) == slot_len:
                    f.write( slots[ iii ] )
                else:
                    f.write( empty_slot )
            f.write( cfg ) # config area comes last

