#!/usr/bin/python

# SPDX-License-Identifier: GPL-2.0+

'''
Command line tool to send a serial shell command to NanoVNA:
Connect via USB serial, issue the command and get the response.
Write the response (without the following prompt) to stdout or a file.
NanoVNA serial commands:
scan scan_bin data frequencies freq sweep power bandwidth saveconfig clearconfig touchcal
touchtest pause resume cal save recall trace marker edelay capture vbat tcxo reset smooth
vbat_offset transform threshold help info version color
'''

import argparse
import serial
import sys

# define default value
nanoPort = '/dev/ttyACM0'

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument( '-o', '--out', nargs = '?', type=argparse.FileType( 'wb' ),
    help = 'write output to FILE, default = sys.stdout', metavar = 'FILE', default = sys.stdout )
ap.add_argument( '-p', '--port', nargs = '?', default = nanoPort,
    help = 'connect to serial port PORT, default = ' + nanoPort )
ap.add_argument( 'command', metavar = 'CMD', nargs = '+', action = 'append',
    help = 'command and arguments' )

options = ap.parse_args()
outfile = options.out
nanoPort = options.port
command = options.command[ 0 ]

cmdline = ''

for cmd in command:
    cmdline = cmdline + cmd + ' '

cmdline = cmdline[ : -1 ].encode() # convert string to bytearray

cr = b'\r'
crlf = b'\r\n'
prompt = b'ch> '

with serial.Serial( nanoPort, timeout=1 ) as NanoVNA: # open serial connection
    NanoVNA.write( cmdline + cr )                     # send command and options terminated by CR
    echo = NanoVNA.read_until( cmdline + crlf )       # wait for command echo terminated by CR LF
    echo = NanoVNA.read_until( prompt )               # get command response until prompt

response = echo[ :-len( prompt ) ]                    # remove 'ch> '

if outfile == sys.stdout:
    print( response.decode(), end='' )                # write string to stdout
else:
    outfile.write( response )                         # write bytes to outfile
