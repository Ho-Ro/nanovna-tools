#!/usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import sys

import skrf as rf

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec



def plot_s1p( nw ):
    fig = plt.figure( figsize=( 5, 5 ), constrained_layout=True )

    # ____0__________1____
    # 0        |  S21dB  |
    # | smith  |_________|
    # 1        |  S21ph  |
    # |________|_________|
    #
    #grid = GridSpec( 2, 2, figure=fig )
    #smith = fig.add_subplot( grid[ :, 0 ] ) # row 0-1, col 0
    #S21dB = fig.add_subplot( grid[ 0, 1 ] ) # row 0, col 1
    #S21ph = fig.add_subplot( grid[ 1, 1 ] ) # row 1, col 1

    nw.plot_s_smith(m=0,n=0,
                    r=1,
                    chart_type='z',
                    #ax=smith,
                    show_legend=True,
                    draw_labels=True,
                    # draw_vswr=True,
    )

    plt.show()



def plot_s2p( nw ):
    fig = plt.figure( figsize=( 10,5 ), constrained_layout=True )

    # ____0__________1____
    # 0        |  S21dB  |
    # | smith  |_________|
    # 1        |  S21ph  |
    # |________|_________|
    #
    grid = GridSpec( 2, 2, figure=fig )
    smith = fig.add_subplot( grid[ :, 0 ] ) # row 0-1, col 0
    S21dB = fig.add_subplot( grid[ 0, 1 ] ) # row 0, col 1
    S21ph = fig.add_subplot( grid[ 1, 1 ] ) # row 1, col 1

    nw.plot_s_smith(m=0,n=0,
                    r=1,
                    chart_type='z',
                    ax=smith,
                    show_legend=True,
                    draw_labels=True,
                    # draw_vswr=True,
    )

    nw.plot_s_db(m=1,n=0,
                 ax=S21dB,
                 title='S21 Magnitude'
    )

    nw.plot_s_deg(m=1,n=0,
                 ax=S21ph,
                 title='S21 Phase'
    )

    plt.show()



if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Plot S11 as smith chart and S22 as dB/phase' )
    parser.add_argument( '-x', '--xkcd', action='store_true',
                        help='draw the plot in xkcd style :)' );
    parser.add_argument( 'infile', type=argparse.FileType('r', encoding='UTF-8'), 
                        help='infile in touchstone format' )
    args = parser.parse_args()

    if args.xkcd:
        plt.xkcd() # :)

    nw = rf.Network( args.infile.name )

    if nw.nports == 1:
        plot_s1p( nw )
    elif nw.nports == 2:
        plot_s2p( nw )
