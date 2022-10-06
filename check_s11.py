#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

import os

import argparse as ap
from glob import iglob

import skrf as rf
from skrf import Network



def check_nw( nw ):

    found, frw, val = 0, 0, 0

    for f, s11 in zip( nw.f, nw.s[:,0,0] ): # frequency and S11
        a = abs( s11 )
        if a > 1:
            found += 1
            if a > abs( val ):
                frq = f
                val = s11
    if found:
        return ( found, frq, val )



def check_files( pattern, verbose ):
    for snp in [ fff for fff in iglob( pattern, recursive=True ) if os.path.isfile( fff ) ]:
        check = check_nw( Network( snp ) )
        if check:
            n, f, s = check
            if verbose:
                print( f'{snp}: {n} points with |S11| > 1, worst at {f} Hz: |{s}| = {abs(s)}' )
            else:
                print( f'{snp}' )
        elif verbose:
            print( f'{snp}: ok' )



if __name__ == '__main__':
    parser = ap.ArgumentParser( description='Check all touchstone files in current directory for values with |S11| > 1' )
    group = parser.add_mutually_exclusive_group()
    group.add_argument( '-i', '--infile', type=ap.FileType('r', encoding='UTF-8'), 
                        help='check only the touchstone file INFILE' )
    group.add_argument( '-r', '--recursive', action='store_true',
                        help='check also all touchstone files in subdirectories' );
    parser.add_argument( '-v', '--verbose', action='store_true',
                        help='display all checked files, more mismatch details' );

    args = parser.parse_args()

if args.infile:
    check_files( args.infile.name, args.verbose )
elif args.recursive:
    check_files( '**/*.s?p', args.verbose )
else:
    check_files( '*.s?p', args.verbose )

