# This file is part of Jeedom.
#
# Jeedom is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Jeedom is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Jeedom. If not, see <http://www.gnu.org/licenses/>.

import logging
import string
import sys
import os
import time
import datetime
import re
import signal
from optparse import OptionParser
from os.path import join
import json

try:
	from jeedom.jeedom import *
except ImportError:
	print "Error: importing module jeedom.jeedom"
	sys.exit(1)

# ----------------------------------------------------------------------------

def read_socket():
	try:
		global JEEDOM_SOCKET_MESSAGE
		if not JEEDOM_SOCKET_MESSAGE.empty():
			logging.debug("Message received in socket JEEDOM_SOCKET_MESSAGE")
			message = json.loads(jeedom_utils.stripped(JEEDOM_SOCKET_MESSAGE.get()))
			if message['apikey'] != _apikey:
				logging.error("Invalid apikey from socket : " + str(message))
				return

			if message['cmd'] == 'send':
				if isinstance(message['data'], list):
					for data in message['data']:
						try:
							send_eleroha(data)
						except Exception, e:
							logging.error('Send command to rfxcom error : '+str(e))
				else:
					try:
						send_eleroha(message['data'])
					except Exception, e:
						logging.error('Send command to rfxcom error : '+str(e))
	except Exception,e:
		logging.error('Error on read socket : '+str(e))
# ----------------------------------------------------------------------------

def send_eleroha(message):
	if test_rfxcom(message):
		jeedom_serial.flushOutput()
		jeedom_serial.flushInput()
		logging.debug("Write message to serial port")
		jeedom_serial.write(message.decode('hex') )
		logging.debug("Write message ok : "+ jeedom_utils.ByteToHex(message.decode('hex')))
		try:
			logging.debug("Decode message")
			decodePacket(message.decode('hex'))
		except Exception, e:
			logging.error('Unrecognizable packet : '+str(e))
	else:
		logging.error("Invalid message from socket.")
# ----------------------------------------------------------------------------

def read_eleroha():
	message = None
	try:
		byte = jeedom_serial.read()
	except Exception, e:
		logging.error("Error in read_eleroha: " + str(e))
		if str(e) == '[Errno 5] Input/output error':
			logging.error("Exit 1 because this exeption is fatal")
			shutdown()
	try:
		if byte:
			message = byte + jeedom_serial.readbytes(ord(byte))
			logging.debug("Message: " + str(jeedom_utils.ByteToHex(message)))
			if jeedom_utils.ByteToHex(message[0]) <> "00":
				if (len(message) - 1) == ord(message[0]):
					try:
						decodePacket(message)
					except Exception, e:
						logging.error("Error: unrecognizable packet (" + jeedom_utils.ByteToHex(message) + ")"+' : '+str(e))
					rawcmd = jeedom_utils.ByteToHex(message).replace(' ', '')
					return rawcmd
				else:
					logging.error("Error: Incoming packet not valid length (" + jeedom_utils.ByteToHex(message) + ")." )
	except OSError, e:
		logging.error("Error in read_rfxcom on decode message : " + str(jeedom_utils.ByteToHex(message))+" => "+str(e))
# ----------------------------------------------------------------------------

def listen():
	logging.debug("Start listening...")
	jeedom_serial.open()
	jeedom_socket.open()
	jeedom_serial.flushOutput()
	jeedom_serial.flushInput()

	logging.debug("Start deamon")
	try:
		while 1:
			time.sleep(0.2)
			// Elero stick
			read_eleroha()
			// Jeedom
			read_socket()
	except KeyboardInterrupt:
		shutdown()
# ----------------------------------------------------------------------------

def handler(signum=None, frame=None):
	logging.debug("Signal %i caught, exiting..." % int(signum))
	shutdown()
# ----------------------------------------------------------------------------

def shutdown():
	logging.debug("Shutdown")
	logging.debug("Removing PID file " + str(_pidfile))
	try:
		os.remove(_pidfile)
	except:
		pass
	try:
		jeedom_socket.close()
	except:
		pass
	try:
		jeedom_serial.close()
	except:
		pass
	logging.debug("Exit 0")
	sys.stdout.flush()
	os._exit(0)
# ----------------------------------------------------------------------------

_log_level = "error"
_socket_port = 55030
_socket_host = '127.0.0.1'
_device = ''
_pidfile = '/tmp/elerohad.pid'
_apikey = ''
_callback = ''
_serial_rate = 38400
_serial_timeout = 9
_cycle = 0.3
_protocol = None

parser = argparse.ArgumentParser(description='eleroha Daemon for Jeedom plugin')
parser.add_argument("--device", help="Device", type=str)
parser.add_argument("--socketport", help="Socketport for server", type=str)
parser.add_argument("--loglevel", help="Log Level for the daemon", type=str)
parser.add_argument("--callback", help="Callback", type=str)
parser.add_argument("--apikey", help="Apikey", type=str)
parser.add_argument("--protocol", help="Protocol to enable", type=str)
parser.add_argument("--serialrate", help="Device serial rate", type=str)
parser.add_argument("--pid", help="Pid file", type=str)
args = parser.parse_args

if args.device:
	_device = args.device
if args.socketport:
	_socket_port = int(args.socketport)
if args.loglevel:
	_log_level = args.loglevel
if args.callback:
	_callback = args.callback
if args.apikey:
	_apikey = args.apikey
if args.pid:
	_pidfile = args.pid
if args.protocol:
	_protocol = args.protocol
if args.serialrate:
	_serial_rate = int(args.serialrate)

jeedom_utils.set_log_level(_log_level)

logging.info('Start elerohad')
logging.info('Log level : '+str(_log_level))
logging.info('Socket port : '+str(_socket_port))
logging.info('Socket host : '+str(_socket_host))
logging.info('PID file : '+str(_pidfile))
logging.info('Device : '+str(_device))
logging.info('Apikey : '+str(_apikey))
logging.info('Callback : '+str(_callback))
logging.info('Serial rate : '+str(_serial_rate))
logging.info('Serial timeout : '+str(_serial_timeout))
logging.info('Cycle : '+str(_cycle))
logging.info('Protocol : '+str(_protocol))

if _device is None:
	logging.error('No device found')
	shutdown()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

try:
	jeedom_utils.write_pid(str(_pidfile))
	globals.JEEDOM_COM = jeedom_com(apikey = _apikey,url = _callback)
	if not globals.JEEDOM_COM.test():
		logging.error('Network communication issues. Please fixe your Jeedom network configuration.')
		shutdown()
	jeedom_serial = jeedom_serial(device=_device,rate=_serial_rate,timeout=_serial_timeout)
	jeedom_socket = jeedom_socket(port=_socket_port,address=_socket_host)
	listen()
except Exception,e:
	logging.error('Fatal error : '+str(e))
	logging.debug(traceback.format_exc())
	shutdown()
