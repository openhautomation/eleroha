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
from Queue import Queue
import json
import binascii
import traceback
import globals
import copy
import threading

try:
    from jeedom.jeedom import *
except ImportError:
    print "Error: importing module jeedom.jeedom"
    sys.exit(1)
# ----------------------------------------------------------------------------
def makeCS(frame):
    logging.debug('makeCS() Called')
    checksumNumber=0
    for elm in frame:
        logging.debug('makeCS() to int '+ str(int(elm, 16)))
        checksumNumber=checksumNumber+int(elm, 16)

    logging.debug('makeCS() total '+ str(checksumNumber))

    upperBound=256
    if checksumNumber<upperBound:
        checksumNumber=upperBound-checksumNumber
    else:
        while checksumNumber > upperBound:
            upperBound=upperBound+256
        checksumNumber=upperBound-checksumNumber

    frame.append(format(checksumNumber, '02x'))
# ----------------------------------------------------------------------------
def easyCheck(frame):
    logging.debug('easyCheck() Called')
    frame.append('aa')
    frame.append('02')
    frame.append('4a')
    makeCS(frame)
# ----------------------------------------------------------------------------
def easySend(channel, cmd, frame):
    logging.debug('easySend() Called')
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
    logging.debug('easyInfo() Called')
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
def decodeAck(rowmessage, decoded):
    logging.debug('decodeAck() Called')
    if len(rowmessage)<6:
        return False

    logging.debug('decodeAck() Called')
    frame=[]
    for elm in rowmessage:
        frame.append(str(jeedom_utils.ByteToHex(elm)).lower())

    ackcs=frame[-1]
    tmpframe=frame[:-1]
    makeCS(tmpframe)

    if frame[-1] == ackcs:
        logging.debug('decodeAck() CS ok')
        firstChannels=frame[3]
        secondChannels=frame[4]
        bytes=firstChannels+secondChannels
        print bytes
        bytes=int(bytes, 16)
        print bytes

        channel=1
        while bytes != 1 and channel <= 15:
            bytes = bytes >> 1
            channel=channel+1

        if channel<16:
            decoded.append(channel)
            decoded.append(frame[5])
            logging.debug('decodeAck() OK channel: '+str(channel) + ' status: ' + str(frame[5]))
            return True
        else:
            logging.debug('decodeAck() channel: '+str(channel) + ' unknown, unable to found device')
            return False
    else:
        logging.debug('decodeAck() FAILED')
        return False
# ----------------------------------------------------------------------------
def read_jeedom():
    logging.debug('read_jeedom() Called')
    try:
        global JEEDOM_SOCKET_MESSAGE
        if not JEEDOM_SOCKET_MESSAGE.empty():
            logging.debug("read_jeedom() New message received")
            message = json.loads(jeedom_utils.stripped(JEEDOM_SOCKET_MESSAGE.get()))

            if message['apikey'] != globals.apikey:
                logging.error("read_jeedom() Invalid apikey from socket : " + str(message))
                return

            logging.debug('read_jeedom() Device ID: '+str(message['device']['id']))
            logging.debug('read_jeedom() Device EQLOGIC_ID: '+str(message['device']['EqLogic_id']))
            logging.debug('read_jeedom() Device CMD: '+str(message['cmd']))

            frame=[]
            oktosend=False
            queue_item={}
            if message['cmd'] == 'setdown':
                oktosend=easySend(int(message['device']['id']), '40', frame)

            elif message['cmd'] == 'setup':
                oktosend=easySend(int(message['device']['id']), '20', frame)

            elif message['cmd'] == 'setstop':
                oktosend=easySend(int(message['device']['id']), '10', frame)

            elif message['cmd'] == 'settilt':
                oktosend=easySend(int(message['device']['id']), '24', frame)

            elif message['cmd'] == 'setintermediate':
                oktosend=easySend(int(message['device']['id']), '44', frame)

            elif message['cmd'] == 'getinfo':
                oktosend=easyInfo(int(message['device']['id']), frame)

            if oktosend==True:
                while TIMER_IN_PROCESS.empty() == False:
                    logging.debug("Cancelling queue timer")
                    timer=TIMER_IN_PROCESS.get()
                    timer.cancel()
                    TIMER_IN_PROCESS.task_done()

                while CMD_TO_SEND.empty() == False:
                    logging.debug("Cancelling queue cmd to send")
                    queue_item=CMD_TO_SEND.get()
                    CMD_TO_SEND.task_done()

                if CMD_IN_PROCESS.empty() == False:
                    logging.debug("CMD_IN_PROCESS queue is not empty")

                # while CMD_IN_PROCESS.empty() == False:
                #     logging.debug("Cancelling queue cmd in process")
                #     queue_item=CMD_IN_PROCESS.get()
                #     CMD_IN_PROCESS.task_done()


                frametosend="".join(frame)
                queue_item={"id":message['device']['id'], "eqlogic_id":message['device']['EqLogic_id'], "frame":frametosend}
                CMD_TO_SEND.put(queue_item)
                logging.debug("Put frame '"+str(frametosend)+"' into CMD_TO_SEND queue")
                write_stick()

                if message['cmd'] != 'getinfo':
                    frame=[]
                    oktosend=False
                    oktosend=easyInfo(int(message['device']['id']), frame)
                    if oktosend==True:
                        frametosend="".join(frame)
                        queue_item={}
                        queue_item={"id":message['device']['id'], "eqlogic_id":message['device']['EqLogic_id'], "frame":frametosend}

                        CMD_TO_SEND.put(queue_item)
                        logging.debug("Put frame '"+str(frametosend)+"' into CMD_TO_SEND queue")

                        timer = threading.Timer(10.0, write_stick)
                        timer.start()
                        logging.debug("Start 10s timer")
                        TIMER_IN_PROCESS.put(timer)
                        logging.debug("Put 10s timer into TIMER_IN_PROCESS queue")

                        CMD_TO_SEND.put(queue_item)
                        logging.debug("Put frame '"+str(frametosend)+" into CMD_TO_SEND queue")

                        timer = threading.Timer(180.0, write_stick)
                        timer.start()
                        logging.debug("Start 180s timer")

                        TIMER_IN_PROCESS.put(timer)
                        logging.debug("Put 180s timer into TIMER_IN_PROCESS queue")

    except Exception,e:
        logging.error('Error on read_jeedom : '+str(e))
# ----------------------------------------------------------------------------
def write_stick():
    logging.debug('write_stick() Called')
    if CMD_IN_PROCESS.empty() == True:
        if CMD_TO_SEND.empty() == False:
            logging.debug('Ready write frame to stick serial port')

            queue_item=CMD_TO_SEND.get()
            jeedom_serial.flushOutput()
            jeedom_serial.flushInput()
            jeedom_serial.write(binascii.a2b_hex(queue_item.get("frame")))
            logging.debug("Write frame : "+ str(queue_item.get("frame")))

            CMD_IN_PROCESS.put(queue_item)
            logging.debug("Put frame '"+str(queue_item.get("frame"))+"' into CMD_IN_PROCESS queue")
# ----------------------------------------------------------------------------
def read_stick():
    logging.debug('read_stick() Called')
    message = None
    try:
        byte = jeedom_serial.read()
    except Exception, e:
        logging.error("read_stick() error: " + str(e))
        if str(e) == '[Errno 5] Input/output error':
            logging.error("Exit 1 because this exeption is fatal")
            shutdown()
    try:
        if byte:
            message = byte + jeedom_serial.readbytes(ord(byte))
            logging.debug("read_stick() message: " + str(jeedom_utils.ByteToHex(message)))

            info=[]
            if decodeAck(message, info) == True:
                logging.debug("read_stick() Ack: OK")

                if CMD_IN_PROCESS.empty() == True:
                    logging.debug("read_stick() received Ack without item into CMD_IN_PROCESS queue")
                else:
                    queue_item=CMD_IN_PROCESS.get()
                    send_to_jeedom={"info":{"channel":str(info[0]), "value":str(info[1]), "EqLogic_id":queue_item.get("eqlogic_id")}}
                    globals.JEEDOM_COM.send_change_immediate(send_to_jeedom)
                    logging.debug('read_stick() message to Jeedom sent')

    except OSError, e:
        logging.error("read_eleroha() error on decode message : " + str(jeedom_utils.ByteToHex(message))+" => "+str(e))
# ----------------------------------------------------------------------------
def listen():
    logging.debug('listen() Called')
    jeedom_serial.open()
    jeedom_socket.open()
    jeedom_serial.flushOutput()
    jeedom_serial.flushInput()

    logging.debug('listen() -start deamon-')
    try:
        while 1:
            time.sleep(0.2)
            # From Jeedom and queueing
            read_jeedom()
            # From Elero stick to Jeedom
            read_stick()
    except KeyboardInterrupt:
        shutdown()
# ----------------------------------------------------------------------------
def handler(signum=None, frame=None):
    logging.debug('handler() Called')
    logging.debug("handler() Signal %i caught, exiting..." % int(signum))
    shutdown()
# ----------------------------------------------------------------------------
def shutdown():
    logging.debug('shutdown() Called')
    logging.debug("shutdown() -Shutdown-")
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

    CMD_TO_SEND = Queue()
    CMD_IN_PROCESS = Queue()
    TIMER_IN_PROCESS = Queue()

    listen()
except Exception,e:
    logging.error('Fatal error : '+str(e))
    logging.debug(traceback.format_exc())
    shutdown()
