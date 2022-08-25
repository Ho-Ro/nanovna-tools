#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line tool to fetch S11, S21 or S11 & S21 parameter from NanoVNA-H
and save as S-parameter or Z-parameter in "touchstone" format (rev 1.1).
Connect via USB serial, issue the command, calculate, and format the response.
Do it as an exercise - step by step - without using tools like scikit-rf.
'''

import argparse
import serial
from serial.tools import list_ports
import sys
from datetime import datetime


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

# default output
outfile = sys.stdout

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( '-d', '--device', dest = 'device',
    help = 'connect to device' )
ap.add_argument( '-o', '--out', nargs = '?', type=argparse.FileType( 'wb' ),
    help = f'write output to FILE, default = {outfile.name}', metavar = 'FILE', default = outfile )
# ap.add_argument( '-v', '--verbose', dest = 'verbose', default = False, action= 'store_true',
#     help = 'be verbose' )
fmt = ap.add_mutually_exclusive_group()
fmt.add_argument( '-1', '--s1p', action = 'store_true',
    help = 'store S-parameter for 1-port device (default)' )
fmt.add_argument( '-2', '--s2p', action = 'store_true',
    help = 'store S-parameter for 2-port device' )
fmt.add_argument( '-z', '--z1p', action = 'store_true',
    help = 'store Z-parameter for 1-port device' )

options = ap.parse_args()
nanodevice = options.device or getdevice()
outfile = options.out
s1p = options.s1p
s2p = options.s2p
z1p = options.z1p


cr = '\r'
lf = '\n'
crlf = cr + lf
prompt = 'ch> '

Z0 = 50 # nominal impedance


with serial.Serial( nanodevice, timeout=1 ) as NanoVNA: # open serial connection

    def execute( cmd ):
        NanoVNA.write( (cmd + cr).encode() )                  # send command and options terminated by CR
        echo = NanoVNA.read_until( (cmd + crlf).encode() )    # wait for command echo terminated by CR LF
        echo = NanoVNA.read_until( prompt.encode() )          # get command response until prompt
        return echo[ :-len( crlf + prompt ) ].decode().split( crlf ) # remove trailing '\r\nch> ', split in lines

    execute( 'pause' ) # stop display

    # get start and stop frequency as well as number of points
    f_start, f_stop, n_points = execute( 'sweep' )[0].split()

    if s2p: # fetch S11 and S21
        outmask = 7 # freq, S11.re, S11.im, S21.re, S21.im
    else: # fetch only S11
        outmask = 3 # freq, S11.re, S11.im

    cmd = f'scan {f_start} {f_stop} {n_points} {outmask}' # prepare command

    comment = datetime.now().strftime( f'! NanoVNA %Y%m%d_%H%M%S\n! {cmd}' )
    if z1p:
        comment += '\n! 1-port normalized Z-parameter (R/Z0 + jX/Z0)'
    elif s2p:
        comment += '\n! 2-port S-parameter (S11.re S11.im S21.re S21.im 0 0 0 0)'
    else:
        comment += '\n! 1-port S-parameter (S11.re S11.im)'

    scan_result = execute( cmd ) # scan and receive S-parameter

    execute( 'resume' ) # resume display


def format_parameter_line( line ):
    if z1p:
        # calculate normalized impedance as Rn + jXn = R/Z0 + jX/Z0 according to this doc
        # https://pa3a.nl/wp-content/uploads/2022/07/Math-for-nanoVNA-S2Z-and-Z2S-Jul-2021.pdf
        freq, S11r, S11i = line.split()
        freq = float( freq )
        S11r = float( S11r )
        S11i = float( S11i )
        Sr2 = S11r * S11r
        Si2 = S11i * S11i
        Denom = ( 1 - S11r ) * ( 1 - S11r ) + Si2
        Rn = ( 1 - Sr2 - Si2 ) / Denom
        Xn = ( 2 * S11i ) / Denom
        return f'{freq:10.0f} {Rn:15.9f} {Xn:15.9f}'
    elif s2p:
        # format a line with freq, S11, S21, S12, S22 (Sxx as re/im pair)
        freq, S11r, S11i, S21r, S21i = line.split()
        freq = float( freq )
        S11r = float( S11r )
        S11i = float( S11i )
        S21r = float( S21r )
        S21i = float( S21i )
        line = f'{freq:10.0f} {S11r:12.9f} {S11i:12.9f}'
        line += f' {S21r:12.9f} {S21i:12.9f}'
        line += '  0  0  0  0' # S12 and S22 are 0+j0
        return line
    else: # s1p
        # format a line with freq, S11.re, S11.im
        freq, S11r, S11i = line.split()
        freq = float( freq )
        S11r = float( S11r )
        S11i = float( S11i )
        return f'{freq:10.0f} {S11r:12.9f} {S11i:12.9f}'


def output_string( line ):
    if outfile == sys.stdout:
        print( line )
    else:
        outfile.write( ( line + lf ).encode() )


# write data as touchstone file (Rev. 1.1)
# Frequency unit: Hz
# Parameter: S = scattering or Z = impedance
# Format: RI = real-imag
# Reference impedance: 50 Ohm

frequency_unit = 'HZ'

format = 'RI'

if z1p:
    parameter = 'Z'
else:
    parameter = 'S'

output_string( comment )

# option header
output_string( f'# {frequency_unit} {parameter} {format} R {Z0}' )

for line in scan_result:
    output_string( format_parameter_line( line ) )
