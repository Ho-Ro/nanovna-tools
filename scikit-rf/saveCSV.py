#!/usr/bin/env python3

"""
tinysa Receive data from tinysa for a certain period of time and save it as a file.
"""
import serial
import numpy as np
import pylab as pl
import struct
from serial.tools import list_ports
from datetime import datetime, timedelta
import time

VID = 0x0483 #1155
PID = 0x5740 #22336

def getport() -> str:
	device_list = list_ports.comports()
	for device in device_list:
		if device.vid == VID and device.pid == PID:
			return device.device
	raise OSError("device not found")

REF_LEVEL = (1<<9)

class tinySA:
	def __init__(self, dev = None):
		self.dev = dev or getport()
		self.serial = None
		self._frequencies = None
		self.points = 450
		
	@property
	def frequencies(self):
		return self._frequencies

	def open(self):
		if self.serial is None:
			self.serial = serial.Serial(self.dev)

	def close(self):
		if self.serial:
			self.serial.close()
		self.serial = None

	def send_command(self, cmd):
		self.open()
		self.serial.write(cmd.encode())
		self.serial.readline() # discard empty line
		
	def fetch_data(self):
		result = ''
		line = ''
		while True:
			c = self.serial.read().decode('utf-8')
			if c == chr(13):
				next # ignore CR
			line += c
			if c == chr(10):
				result += line
				line = ''
				next
			if line.endswith('ch>'):
				# stop on prompt
				break
		return result

	def data(self, array = 2):
		self.send_command("data %d\r" % array)
		data = self.fetch_data()
		x = []
		for line in data.split('\n'):
			if line:
				d = line.strip().split(' ')
				x.append(float(line))
		return np.array(x)

	def fetch_frequencies(self):
		self.send_command("frequencies\r")
		data = self.fetch_data()
		x = []
		for line in data.split('\n'):
			if line:
				x.append(float(line))
		self._frequencies = np.array(x)

	def writeCSV(self, x, name):
		f = open(name, "w")
		for i in range(len(x)):
			print("%d, "%self.frequencies[i], "%2.2f"%x[i], file=f)
		f.close()

if __name__ == '__main__':
	nv = tinySA(getport())
	p = 0
	until = datetime.now() + timedelta(seconds=60)
	while True:
		nv.fetch_frequencies()
		s = nv.data(p)
		now = datetime.now()
		filename = f'{now.isoformat().replace(":", "-")}.csv'
		nv.writeCSV(s, filename)
		if until < now:
			break
		time.sleep(15)
