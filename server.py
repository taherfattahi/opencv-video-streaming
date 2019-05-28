#!/usr/bin/env python

# __author__ = "taher fattahi"

import threading
import os, signal
import cv2
import socket
import datetime
import struct
import argparse
import time
import sys


parser = argparse.ArgumentParser()
parser.add_argument("-v", "--video", help="Path to video to stream (default: webcam)", default=0)
parser.add_argument("host", help="Host IP address")
parser.add_argument("port", help="port number")
args = parser.parse_args()


cap = cv2.VideoCapture(args.video)

FPS = cap.get(5)
setFPS = 10
ratio = int(FPS)/setFPS

host = args.host
port = int(args.port)
addr = (host, port)
buf = 65507
service_request_msg = 'hi'
TIMEOUT = 2

class Server():
	def __init__(self):
		self.clientsUDP = []
		self.clientsTCP = []
		self.timeOuts = []
		self.sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sockUDP.bind((host, port))
		self.sockUDP.settimeout(2.0)

		self.sockTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sockTCP.bind((host, port))
		self.sockTCP.listen(5)
		self.sockTCP.settimeout(2.0)
		# self.sockTCP.setblocking(False)

		acceptUDP = threading.Thread(target=self.acceptConnUDP)
		acceptUDP.daemon = True
		acceptUDP.start()

		acceptTCP = threading.Thread(target=self.acceptConnTCP)
		acceptTCP.daemon =True
		acceptTCP.start()

		commands = threading.Thread(target = self.commands)
		commands.daemon = True
		commands.start()

		count = 0
		wait = 0
		while (cap.isOpened()):
			try:
				while wait > time.time():
					pass
				wait = time.time() + 1.00/FPS
				ret, frame = cap.read()
				if ret == True:
					cv2.imshow('ServerSide', frame)
					count = count + 1
					if count == ratio:
						img_as_text=self.imgEncode(frame)

						self.sendto_all(img_as_text) 
						count = 0
					if cv2.waitKey(True) & 0xFF == ord('q'):
						for c in self.clientsTCP:
							c.shutdown(socket.SHUT_RDWR)
						self.clientsTCP=[]
						self.clientsUDP=[]
						self.sockUDP.close()
						self.sockTCP.close()
						break
				else:
					#set to start of video
					cap.set(2, 0)
			except KeyboardInterrupt:
				for c in self.clientsTCP:
					c.shutdown(socket.SHUT_RDWR)
				self.clientsTCP=[]
				self.clientsUDP=[]
				self.sockUDP.close()
				self.sockTCP.close()
				sys.exit(0)


	def imgEncode(self, frame):
		quality =100
		retval, buff = cv2.imencode(".jpg",frame, (cv2.IMWRITE_JPEG_QUALITY,quality))
		img_as_text = buff.tostring()
		
		# check that the image size is smaller than the buffer
		while len(img_as_text)> buf: 
			quality= quality-10
			retval, buff = cv2.imencode(".jpg",frame, (cv2.IMWRITE_JPEG_QUALITY,quality))
			img_as_text = buff.tostring()
		return img_as_text



	def acceptConnUDP(self):
		while True:
			try:
				data, address = self.sockUDP.recvfrom(buf)
				if (data == service_request_msg):
					# Search client and update timeout
					try :
						i = self.clientsUDP.index(address)
						self.clientsUDP.pop(i)
						self.timeOuts.pop(i)
						self.clientsUDP.append(address)
						now = datetime.datetime.now()
						self.timeOuts.append(now)
					except:
					# Add client to client's list
						print('udp client arrives')
						self.clientsUDP.append(address)
						now = datetime.datetime.now()
						self.timeOuts.append(now)
			except:
				pass



	def acceptConnTCP(self):
		while True:
			try:
				conn, addr = self.sockTCP.accept()
				#conn.setblocking(False)
				self.clientsTCP.append(conn)
				print('tcp client arrives')
			except:
				pass


	def sendto_all(self,img):
		for c in self.clientsUDP:
			currentTime = datetime.datetime.now()
			i = self.clientsUDP.index(c)
			deltaTime = currentTime - self.timeOuts[i]
			if (deltaTime.total_seconds() > 90):
				self.clientsUDP.pop(i)
				self.timeOuts.pop(i)
				print "UDP client come out"
			else:
				try:
					self.sockUDP.sendto(img,c)
				except Exception:
					self.clientsUDP.pop(i)
					self.timeOuts.pop(i)
					print "UDP client come out"

		
		for c in self.clientsTCP:
			signal.signal(signal.SIGALRM, TimeOut.handle_timeout)
			signal.alarm(TIMEOUT)
			#try to send data, if can't, 
			#client leaves system
			try:
				packed_len = struct.pack('>L',len(img))
				c.sendall(packed_len)
				c.sendall(img)
			except Exception,e:
				c.close()
				self.clientsTCP.remove(c)
				print 'TCP client come out \n'
			finally:
				signal.alarm(0)
                

	def commands(self):
		while True:
			ins = raw_input('')
			if (ins == 'clients'):
				print('UDP clients -> %d' % len(self.clientsUDP))
				print('TCP clients -> %d' % len(self.clientsTCP))
			if (ins == 'times'):
				print(self.timeOuts)


class TimeOut(Exception):
	pass

	def handle_timeout(signum, frame):
		import errno
		raise TimeOut(os.strerror(errno.ETIME))



s = Server()

