#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

'''
Command line tool to fetch S11 or S11 & S21 parameter from NanoVNA-H
Connect via USB serial, issue the command and format the response as "touchstone"
'''

import argparse
import serial
from serial.tools import list_ports
import sys

import numpy as np
from skrf import Network, Frequency


# define default serial port
nanodevice = '/dev/ttyACM0'

# ChibiOS/RT Virtual COM Port
VID = 0x0483
PID = 0x5740

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
n = ap.add_mutually_exclusive_group()
n.add_argument( '-1', '--s1p', action = 'store_true',
    help = 'store S-parameter for 1-port device' )
n.add_argument( '-2', '--s2p', action = 'store_true',
    help = 'store S-parameter for 2-port device' )
form = ap.add_mutually_exclusive_group()
form.add_argument( '--db', action = 'store_true',
    help = 'store as dB/angle' )
form.add_argument( '--ma', action = 'store_true',
    help = 'store as magnitude/angle' )
form.add_argument( '--ri', action = 'store_true',
    help = 'store as real/imag (default)' )

options = ap.parse_args()
nanodevice = options.device or getdevice()
outfile = options.out

s1p = options.s1p
s2p = options.s2p

if options.db:
    form='db'
elif options.ma:
    form='ma'
else:
    form='ri'

cr = '\r'
lf = '\n'
crlf = cr + lf
prompt = 'ch> '

Z0 = 50 # nominal impedance
f_start = 0
f_stop = 0
n_points = 0

with serial.Serial( nanodevice, timeout=1 ) as NanoVNA: # open serial connection

    def execute( cmd ):
        NanoVNA.write( (cmd + cr).encode() )                # send command and options terminated by CR
        echo = NanoVNA.read_until( (cmd + crlf).encode() )  # wait for command echo terminated by CR LF
        echo = NanoVNA.read_until( prompt.encode() )        # get command response until prompt
        return echo[ :-len( prompt ) ].decode().split( crlf )[:-1] # remove 'ch> ', split in lines

    execute( 'pause' ) # stop display

    f_start, f_stop, n_points = execute( 'sweep' )[0].split()

    if s2p: # fetch s11 & s21
        outmask = 7 # freq, S11.re, S11.im, S21.re, S21.im
    else: # fetch s11
        outmask = 3 # freq, S11.re, S11.im

    cmd = f'scan {f_start} {f_stop} {n_points} {outmask}' # prepare command

    scan_result = execute( cmd ) # scan and receive S-parameter

    execute( 'resume' ) # resume display


def parse_s_parameter( line ):
    if s2p:
        # parse a line with freq, S11, S21 (Sxx as re/im pair)
        # and prepare the network components according to
        # https://scikit-rf.readthedocs.io/en/latest/tutorials/Networks.html
        # Creating-Network-from-s-parameters
        f, s11r, s11i, s21r, s21i = line.split()
        f = float( f )
        s11 = complex( float( s11r ), float( s11i ) )
        s21 = complex( float( s21r ), float( s21i ) )
        F.append( f  ) # append to frequency array
        S11.append( s11 ) # and to the separate Sxx-parameter arrays
        S21.append( s21 )
        S12.append( complex( 0 ) ) # not provided by NanoVNA
        S22.append( complex( 0 ) )
    else:
        # fetch a line with freq, S11 (Sxx as re/im pair)
        f, s11r, s11i = line.split()
        f = float( f )
        s11 = complex( float( s11r ), float( s11i ) )
        F.append( f )
        S11.append( s11 )


def output_string( line ):
    if outfile == sys.stdout:
        print( line )
    else:
        outfile.write( ( line + lf ).encode() )


# frequency and S parameter arrays
F = []
S11 = []
S21 = []
S12 = []
S22 = []

# parse all lines and fill arrays
for line in scan_result:
    parse_s_parameter( line )

# build the frequency object
frequency = Frequency.from_f( F, unit='Hz' )

if len( S21 ): # two-port data
    # build the S-matrix from 4 separate arrays
    S = np.zeros( ( len( F ), 2, 2 ), dtype=complex )
    S[:,0,0] = S11
    S[:,1,0] = S21
    S[:,0,1] = S12
    S[:,1,1] = S22
else: # one-port data
    S = S11 # this array contains the S-matrix

# build the Network object from frequency object and S-matrix
# https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.html
ntwk = Network( frequency=frequency, s=S, name='NanoVNA-H' )

# write the touchstone data using the function from scikit-rf:
# https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.write_touchstone.html
output_string( ntwk.write_touchstone( form=form, return_string=True ) )


