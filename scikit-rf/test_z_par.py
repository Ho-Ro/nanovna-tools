#!/usr/bin/python

import sys

import skrf as rf
from skrf import Network, Frequency

s11 = Network( 's11.s1p' )
#print( s11 )


Z0 = s11.z0[0][0].real

F = s11.f
ZR = s11.z[:,0,0].real / Z0
ZI = s11.z[:,0,0].imag / Z0

print( f'# HZ Z RI R {Z0}' )

for f, sr, si in zip( F, ZR, ZI ):
    print( f, sr, si )


