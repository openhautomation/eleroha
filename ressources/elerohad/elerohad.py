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
import argparse
from os.path import join
import json
import binascii
import traceback
import globals

try:
    from jeedom.jeedom import *
except ImportError:
    print "Error: importing module jeedom.jeedom"
    sys.exit(1)

# ----------------------------------------------------------------------------
def makeCS(frame):
    checksumNumber=0
    for elm in frame:
        logging.debug('MAKECS------ to int '+ str(int(elm, 16)))
        checksumNumber=checksumNumber+int(elm, 16)

    logging.debug('MAKECS------ total '+ str(checksumNumber))

    upperBound=256
    if checksumNumber<upperBound:
        checksumNumber=upperBound-checksumNumber
    else:
        while checksumNumber > upperBound:
            upperBound=upperBound+256
            checksumNumber=upperBound-checksumNumber

    frame.append(format(checksumNumber, '02x'))
# ----------------------------------------------------------------------------
def decodeAck(rowmessage, decoded):
    frame=[]
    for elm in rowmessage:
        logging.debug('DECODEACK------ frame to decode '+ str(jeedom_utils.ByteToHex(elm)))
        frame.append(str(jeedom_utils.ByteToHex(elm)).lower())

    logging.debug('DECODEACK------ frame : '+str(frame))
    ackcs=frame[-1]
    tmpframe=frame[:-1]
    logging.debug('DECODEACK------ frame without CS: '+str(tmpframe))
    makeCS(tmpframe)
    logging.debug('DECODEACK------ frame calculated CS: '+str(tmpframe))

    if frame[-1] == ackcs:
        if frame[3]=='00':
            decoded.append(int(frame[4], 16))
        else:
            decoded.append(int(frame[3], 16))
        decoded.append(frame[5])
        return True
    else:
        return False
# ----------------------------------------------------------------------------
def easyCheck(frame):
    frame.append('aa')
    frame.append('02')
    frame.append('4a')
    makeCS(frame)
# ----------------------------------------------------------------------------
def easySend(channel, cmd, frame):
    frame.append('aa')
    frame.append('05')
    frame.append('4c')
    if channel<=8:
        frame.append('00')
        frame.append(format(2 ** (channel-1), '02x'))
    else:
        frame.append(format(2 ** (channel-1-8), '02x'))
        frame.append('00')

    frame.append(cmd)
    makeCS(frame)
    return True
# ----------------------------------------------------------------------------
def easyInfo(channel, frame):
    frame.append('aa')
    frame.append('04')
    frame.append('4e')
    if channel<=8:
        frame.append('00')
        frame.append(format(2 ** (channel-1), '02x'))
    else:
        frame.append(format(2 ** (channel-1-8), '02x'))
        frame.append('00')

    makeCS(frame)
    return True
# ----------------------------------------------------------------------------
# read from Jeedom
def read_socket():
    try:
        global JEEDOM_SOCKET_MESSAGE
        if not JEEDOM_SOCKET_MESSAGE.empty():
            logging.debug("Message received in socket JEEDOM_SOCKET_MESSAGE")
            message = json.loads(jeedom_utils.stripped(JEEDOM_SOCKET_MESSAGE.get()))
            logging.debug("Message decoded")
            if message['apikey'] != globals.apikey:
                logging.error("Invalid apikey from socket : " + str(message))
                return

            logging.debug('SOCKET-READ------Device ID: '+str(message['device']['id']))
            logging.debug('SOCKET-READ------Device EQLOGIC_ID: '+str(message['device']['EqLogic_id']))
            logging.debug('SOCKET-READ------Device CMD: '+str(message['cmd']))

            globals.KNOWN_DEVICES[str(message['device']['id'])] = message['device']

            frame=[]
            send=False
            if message['cmd'] == 'setdown':
                send=easySend(int(message['device']['id']), '40', frame)

            elif message['cmd'] == 'setup':
                send=easySend(int(message['device']['id']), '20', frame)

            elif message['cmd'] == 'setstop':
                send=easySend(int(message['device']['id']), '10', frame)

            elif message['cmd'] == 'settilt':
                send=easySend(int(message['device']['id']), '24', frame)

            elif message['cmd'] == 'setintermediate':
                send=easySend(int(message['device']['id']), '44', frame)

            if send==True:
                logging.debug('SOCKET-READ------BILT frame : '+str(frame))

                try:
                    send_eleroha(frame)
                except Exception, e:
                    logging.error('Send command to eleroha error : '+str(e))

    except Exception,e:
        logging.error('Error on read socket : '+str(e))
# ----------------------------------------------------------------------------
def send_eleroha(frame):
	tosend="".join(frame)
	jeedom_serial.flushOutput()
	jeedom_serial.flushInput()

	logging.debug("Write frame to serial port")
	jeedom_serial.write(binascii.a2b_hex(tosend))
	logging.debug("Send frame : "+ tosend)
# ----------------------------------------------------------------------------
# Read from Stick
def read_eleroha():
    message = None
    try:
        byte = jeedom_serial.read()
    except Exception, e:
        logging.error("Error in read_rfxcom: " + str(e))
        if str(e) == '[Errno 5] Input/output error':
            logging.error("Exit 1 because this exeption is fatal")
            shutdown()
    try:
        if byte:
            message = byte + jeedom_serial.readbytes(ord(byte))
            logging.debug("Message: " + str(jeedom_utils.ByteToHex(message)))

            info=[]
            if decodeAck(message, info) == True:
                logging.debug("Message: OK")
                logging.error("READ_ELEROHA OK call Jeedom")

                if str(info[0]) in globals.KNOWN_DEVICES:
                    action={}
                    action['value']=str(info[1])
                    action['channel'] = str(info[0])
                    action['EqLogic_id'] = globals.KNOWN_DEVICES[str(info[0])]['EqLogic_id']

                    globals.JEEDOM_COM.add_changes('info',action)
                else:
                    logging.error("No key found in KNOWN_DEVICES")

    except OSError, e:
        logging.error("Error in read_rfxcom on decode message : " + str(jeedom_utils.ByteToHex(message))+" => "+str(e))

def old_read_eleroha():
    try:
        byte = jeedom_serial.read()
    except Exception, e:
        logging.error("Error in read_eleroha: " + str(e))
        if str(e) == '[Errno 5] Input/output error':
            logging.error("Exit 1 because this exeption is fatal")
            shutdown()

    if byte:
        logging.error("READ_ELEROHA starting to read")
        rowframe=[]
        rowframe.append(byte)

        endTimer=int(time.time())+5
        while endTimer>int(time.time()):
            byte = jeedom_serial.read()
            if byte:
                rowframe.append(rowframe)

        logging.error("READ_ELEROHA rowframe: "+str(rowframe))
        #info=[]
        #if decodeAck(rowframe, info) == True:
        #    logging.error("READ_ELEROHA ACK ok")
        #    if info[0] in list(globals.KNOWN_DEVICES):
        #        logging.error("READ_ELEROHA OK call Jeedom")
        #        globals.JEEDOM_COM.add_changes('devices::'+info[0],info[1])
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
			#Elero stick
			read_eleroha()
			#Jeedom
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
	logging.debug("Removing PID file " + str(globals.pidfile))
	try:
		os.remove(globals.pidfile)
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

parser = argparse.ArgumentParser(description='elerohad Daemon for Jeedom plugin')
parser.add_argument("--device", help="Device", type=str)
parser.add_argument("--serialrate", help="Device serial rate", type=str)
parser.add_argument("--serialtimeout", help="Device serial timeout", type=str)
parser.add_argument("--socketport", help="Socket port for server", type=str)
parser.add_argument("--sockethost", help="Socket Host", type=str)
parser.add_argument("--protocol", help="Protocol to enable", type=str)
parser.add_argument("--pidfile", help="PID file", type=str)
parser.add_argument("--callback", help="Callback", type=str)
parser.add_argument("--cycle", help="Cycle to send event", type=str)
parser.add_argument("--apikey", help="Apikey", type=str)
parser.add_argument("--loglevel", help="Log Level for the daemon", type=str)
parser.add_argument("--daemonname", help="Daemon Name", type=str)
args = parser.parse_args()

if args.device:
    globals.device = args.device
if args.serialrate:
    globals.serial_rate = int(args.serialrate)
if args.serialtimeout:
    globals.serial_timeout = int(args.serialtimeout)
if args.socketport:
    globals.socket_port=int(args.socketport)
if args.sockethost:
    globals.socket_host=args.sockethost
if args.protocol:
    globals.protocol=args.protocol
if args.pidfile:
    globals.pidfile=args.pidfile
if args.callback:
    globals.callback=args.callback
if args.cycle:
    globals.cycle=float(args.cycle)
if args.apikey:
    globals.apikey=args.apikey
if args.loglevel:
    globals.log_level=args.loglevel
if args.daemonname:
    globals.daemonname=args.daemonname

jeedom_utils.set_log_level(globals.log_level)

logging.info('Start elerohad')
logging.info('device : '+str(globals.device))
logging.info('serial_rate : '+str(globals.serial_rate))
logging.info('serial_timeout : '+str(globals.serial_timeout))
logging.info('socket_port : '+str(globals.socket_port))
logging.info('socket_host : '+str(globals.socket_host))
logging.info('protocol : '+str(globals.protocol))
logging.info('pidfile : '+str(globals.pidfile))
logging.info('callback : '+str(globals.callback))
logging.info('cycle : '+str(globals.cycle))
logging.info('apikey : '+str(globals.apikey))
logging.info('log_level : '+str(globals.log_level))
logging.info('daemonname : '+str(globals.daemonname))

if globals.device is None:
	logging.error('No device found')
	shutdown()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

try:
	jeedom_utils.write_pid(str(globals.pidfile))
	globals.JEEDOM_COM = jeedom_com(apikey = globals.apikey,url = globals.callback)
	if not globals.JEEDOM_COM.test():
		logging.error('Network communication issues. Please fixe your Jeedom network configuration.')
		shutdown()
	jeedom_serial = jeedom_serial(device=globals.device,rate=globals.serial_rate,timeout=globals.serial_timeout)
	jeedom_socket = jeedom_socket(port=globals.socket_port,address=globals.socket_host)
	listen()
except Exception,e:
	logging.error('Fatal error : '+str(e))
	logging.debug(traceback.format_exc())
	shutdown()
