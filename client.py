#!/usr/bin/env python

# __author__ = "taher fattahi"

from socket import *
import numpy as np
import cv2
import threading
import os, signal
import time
import argparse
import sys
import pickle
import struct


parser = argparse.ArgumentParser()
parser.add_argument("-tcp", "--TCP", help="Protocol TCP", action = "store_true")
parser.add_argument("host", help="host")
parser.add_argument("port", help="port")
args = parser.parse_args()


host = args.host
port = int(args.port)
buf = 65507
addr = (host, port)
alive_time = 30
service_request_msg = 'hi'

BYTES_SIZE = 4  

class Client(object):
	def __init__(self, tcp):
		try:
			TIMEOUT =2
			if not tcp:
				self.s = socket(AF_INET, SOCK_DGRAM)
				self.s.sendto(service_request_msg,addr)
			    
				alive = threading.Thread(target = self.send_alive_msg)
				alive.daemon = True
				alive.start()

				while True:
					signal.signal(signal.SIGALRM, TimeOut.handle_timeout)
					signal.alarm(TIMEOUT)
					try:
						data = self.s.recv(buf)
						printError=True
					except Exception:
						self.s.sendto(service_request_msg,addr)
						if printError:
							print 'Trying reconnect. Please, check your network connection'
							printError = False
					finally:
						signal.alarm(0)
					
					jpg_original = np.fromstring(data, np.uint8)
					image = cv2.imdecode(jpg_original,1)
					cv2.imshow('recv UDP', image)
					if cv2.waitKey(True) & 0xFF == ord('q'):
						self.s.close()
						break
			else:
				exit = False
				while not exit:
					self.s = socket(AF_INET, SOCK_STREAM)
					self.s.connect(addr)
					connected = True
					while connected:
						signal.signal(signal.SIGALRM, TimeOut.handle_timeout)
						signal.alarm(TIMEOUT)
						try:

							# receive first 4 bytes to get size of image
							length_size_rcv = BYTES_SIZE
							compress_length =  self.s.recv(length_size_rcv)
							printError=True
							if not compress_length:
								exit = True
								break
							length_size_rcv -= len(compress_length)
							while  length_size_rcv > 0:
								compress_length_aux = self.s.recv(length_size_rcv)
								if not compress_length_aux:
									exit = True
									break
								compress_length += compress_length_aux
								length_size_rcv -= len(compress_length_aux)
							length = struct.unpack('>L', compress_length)[0]
							data_length = long(length)


							# receive until get all img
							data = self.s.recv(data_length)
							if not data:
								exit=True
								break
							data_length -= len(data)
							while data_length > 0:
								data_aux = self.s.recv(data_length)
								if not data_aux:
									exit = True
									break
								data += data_aux
								data_length -= len(data_aux)

							#procces image
							jpg_original = np.fromstring(data, np.uint8)
							image = cv2.imdecode(jpg_original,1) 
							cv2.imshow('recv TCP', image)
							if cv2.waitKey(True) & 0xFF == ord('q'):
								self.s.close()
								exit = True
								break
						except Exception:
							if printError:
								print 'Trying reconnect. Please, check your network connection'
								printError = False
							self.s.close()
							connected= False
						finally:
							signal.alarm(0)
		except KeyboardInterrupt:
			sys.exit(0)


	def send_alive_msg(self):
		while True:
			time.sleep(alive_time)
			self.s.sendto(service_request_msg,addr)

	
class TimeOut(Exception):
	pass

	def handle_timeout(signum, frame):
		import errno
		raise TimeOut(os.strerror(errno.ETIME))



c = Client(args.TCP)

