#!/usr/bin/python

# SPDX-License-Identifier: GPL-2.0+

'''
Command line tool to fetch S11, S21 or S11 & S21 parameter from NanoVNA-H
and save as S-parameter or Z-parameter
Connect via USB serial, issue the command and format the response as "touchstone"
'''

import argparse
import serial
import sys
from datetime import datetime

# define default serial port
nanoPort = '/dev/ttyACM0'

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( '-o', '--out', nargs = '?', type=argparse.FileType( 'wb' ),
    help = 'write output to FILE, default = sys.stdout', metavar = 'FILE', default = sys.stdout )
ap.add_argument( '-p', '--port', nargs = '?', default = nanoPort,
    help = 'connect to serial port PORT, default = ' + nanoPort )
ap.add_argument( '--s2p', action = 'store_true',
    help = 'fetch also s21 parameter in addition to s11' )
ap.add_argument( '-z', '--format_z', action = 'store_true',
    help = 'fetch s11 and calculate R +jX' )

options = ap.parse_args()
outfile = options.out
nanoPort = options.port
format_z = options.format_z

s2p = options.s2p


cr = '\r'
lf = '\n'
crlf = cr + lf
prompt = 'ch> '

Z0 = 50 # nominal impedance

with serial.Serial( nanoPort, timeout=1 ) as NanoVNA: # open serial connection

    def execute( cmd ):
        NanoVNA.write( (cmd + cr).encode() )                # send command and options terminated by CR
        echo = NanoVNA.read_until( (cmd + crlf).encode() )  # wait for command echo terminated by CR LF
        echo = NanoVNA.read_until( prompt.encode() )        # get command response until prompt
        return echo[ :-len( prompt ) ].decode().split( crlf )[:-1] # remove 'ch> ', split in lines

    execute( 'pause' ) # stop display

    frequencies = execute( 'frequencies' ) # get frequencies
    f_start = frequencies[ 0 ] # start frequency
    f_stop = frequencies[ -1 ] # stop frequency
    n = len( frequencies )     # number of frequencies


    if format_z or not s2p: # s1p is default
        outmask = 3 # freq, S11.re, S11.im
    else: # create s2p format
        outmask = 7 # freq, S11.re, S11.im, S21.re, S21.im

    cmd = f'scan {f_start} {f_stop} {n} {outmask}' # prepare command

    comment = datetime.now().strftime('! NanoVNA %Y%m%d_%H%M%S\n! ' + cmd )
    if format_z:
        comment += '\n! 1 port Z-parameter (R/Z0 + jX/Z0)'
    elif s2p:
        comment += '\n! 2 port S-parameter (S11.re S11.im S21.re S21.im 0 0 0 0)'
    else:
        comment += '\n! 1 port S-parameter (S11.re S11.im)'

    scan_result = execute( cmd ) # scan and receive S-parameter

    execute( 'resume' ) # resume display


def format_line( line ):
    if format_z:
        # calculate normalized impedance as Rn + jXn = R/Z0 + jX/Z0 according to this doc
        # https://pa3a.nl/wp-content/uploads/2022/07/Math-for-nanoVNA-S2Z-and-Z2S-Jul-2021.pdf
        freq, Sr, Si = line[:-1].split( ' ' )
        freq = float( freq )
        Sr = float( Sr )
        Si = float( Si )
        Sr2 = Sr * Sr
        Si2 = Si * Si
        Sr_2 = ( 1 - Sr ) * ( 1 - Sr )
        Rn = ( 1 - ( Si2 + Sr2 ) ) / ( Sr_2 + Si2 )
        Xn = ( 2 * Si ) / ( Sr_2 + Si2 )
        return f'{freq:10.0f} {Rn:15.9f} {Xn:15.9f}'
    elif s2p:
        # format a line with freq, S11, S21, S12, S22 (Sxx as re/im pair)
        freq, S11r, S11i, S21r, S21i = line[:-1].split( ' ' )
        line = f'{float(freq):10.0f} {float(S11r):12.9f} {float(S11i):12.9f}'
        line += f' {float(S21r):12.9f} {float(S21i):12.9f}'
        line += '  0  0  0  0' # S12 and S22 are 0+j0
        return line
    else:
        # format a line with freq, S11.re, S11.im
        freq, S11r, S11i = line[:-1].split( ' ' )
        return f'{float( freq ):10.0f} {float( S11r ):12.9f} {float( S11i ):12.9f}'


def write_line( line ):
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

if format_z:
    parameter = 'Z'
else:
    parameter = 'S'

header = f'# {frequency_unit} {parameter} {format} R {Z0}'

write_line( header )
write_line( comment )

for line in scan_result:
    write_line( format_line( line ) )
