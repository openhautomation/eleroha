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
import copy

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
def decodeAck(rowmessage, decoded):
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
def addQueue(cmd, device, steptime, maxretry, targetcmd=None):
    logging.debug('addQueue() Called')
    toqueue={'cmd' : str(cmd), 'device' : str(device), 'del':0, 'steptime':steptime, 'maxretry':maxretry, 'targetcmd':str(targetcmd), 'timer':(int(time.time())+steptime)}
    globals.QUEUED.append(copy.deepcopy(toqueue))

def readQueue():
    logging.debug('readQueue() Called')
    for elm in globals.QUEUED:
        if elm['del']==0:
            if elm['maxretry']>0:
                if elm['timer'] <= int(time.time()):
                    elm['maxretry']=elm['maxretry']-1
                    elm['timer']=(int(time.time()+elm['steptime']))

                    logging.debug('readQueue() send cmd to prepare_send_eleroha()')
                    logQueue()
                    prepare_send_eleroha(elm['cmd'], elm['device'], 0)
            else:
                elm['del']=1

    delQueue()

def todelQueue(device):
    logging.debug('todelQueue() Called')
    for elm in globals.QUEUED:
        logging.debug('todelQueue() Queue Device: '+ elm['device'] + ' Search Device: ' + str(device))
        if elm['device']==str(device):
            elm['del']=1
            logging.debug('todelQueue() to del  device: '+ device)

    delQueue()

def delQueue():
    logging.debug('delQueue() Called')
    cleanlist = []
    for elm in globals.QUEUED:
        if elm['del']==0:
            cleanlist.append(elm)


    globals.QUEUED=[]
    if len(cleanlist) >0:
        globals.QUEUED=copy.deepcopy(cleanlist)

def targetQueue(device, targetcmd):
    logging.debug('targetQueue() Called')
    for elm in globals.QUEUED:
        if elm['targetcmd'] is not None:
            logging.debug('targetQueue() Queue Device: '+ elm['device'] + ' Queue Target: ' + elm['targetcmd'])
            logging.debug('targetQueue() Search Device: '+ str(device) + ' Search Target: ' + str(targetcmd))
            if elm['device']==str(device) and elm['targetcmd']==str(targetcmd):
                logging.debug('targetQueue() del from queue target found')
                elm['del']=1

    delQueue()

def logQueue():
    logging.debug('logQueue() Called')
    i=0
    for elm in globals.QUEUED:
        logging.debug('logQueue() nbr: ' + str(i))
        logging.debug('logQueue()    cmd   : ' + elm['cmd'] + ' device: ' + elm['device'] + ' steptime: ' + str(elm['steptime']) + ' targetcmd: ' + elm['targetcmd'])
        logging.debug('logQueue()    timer : ' + str(elm['timer']) + '(current: '+str(int(time.time()))+') maxretry: ' + str(elm['maxretry']) + ' del: ' + str(elm['del']) )

        i=i+1

# ----------------------------------------------------------------------------
# read from Jeedom
def read_socket():
    #logging.debug('read_socket() Called (Jeedom=>deamon)')
    try:
        global JEEDOM_SOCKET_MESSAGE
        if not JEEDOM_SOCKET_MESSAGE.empty():
            logging.debug("read_socket() New message received")
            message = json.loads(jeedom_utils.stripped(JEEDOM_SOCKET_MESSAGE.get()))

            if message['apikey'] != globals.apikey:
                logging.error("read_socket() Invalid apikey from socket : " + str(message))
                return

            logging.debug('read_socket() Device ID: '+str(message['device']['id']))
            logging.debug('read_socket() Device EQLOGIC_ID: '+str(message['device']['EqLogic_id']))
            logging.debug('read_socket() Device CMD: '+str(message['cmd']))

            globals.KNOWN_DEVICES[str(message['device']['id'])] = message['device']

            todelQueue(message['device']['id'])
            prepare_send_eleroha(message['cmd'], int(message['device']['id']), 1)

    except Exception,e:
        logging.error('Error on read socket : '+str(e))
# ----------------------------------------------------------------------------
def prepare_send_eleroha(cmd, device, toqueue):
    logging.debug('prepare_send_eleroha() Called')
    frame=[]
    send=False
    if cmd == 'setdown':
        send=easySend(int(device), '40', frame)

    elif cmd == 'setup':
        send=easySend(int(device), '20', frame)

    elif cmd == 'setstop':
        send=easySend(int(device), '10', frame)

    elif cmd == 'settilt':
        send=easySend(int(device), '24', frame)

    elif cmd == 'setintermediate':
        send=easySend(int(device), '44', frame)

    elif cmd == 'getinfo':
        send=easyInfo(int(device), frame)

    if send==True:
        logging.debug('prepare_send_eleroha() BILT frame : '+str(frame))

        try:
            send_eleroha(frame)
            if toqueue==1:
                if cmd=='setup':
                    addQueue('getinfo', device, 3, 1, None)
                    addQueue('getinfo', device, 5, 12, '01')
                elif cmd=='setdown':
                    addQueue('getinfo', device, 3, 1, None)
                    addQueue('getinfo', device, 5, 12, '02')
                elif cmd=='settilt':
                    addQueue('getinfo', device, 3, 2, None)
                elif cmd=='setintermediate':
                    addQueue('getinfo', device, 3, 2, None)
                elif cmd=='setstop':
                    addQueue('getinfo', device, 3, 2, None)

        except Exception, e:
           logging.error('prepare_send_eleroha() error : '+str(e))

# ----------------------------------------------------------------------------
def send_eleroha(frame):
    logging.debug('send_eleroha() Called (deamon=>Elero stick)')
    tosend="".join(frame)
    jeedom_serial.flushOutput()
    jeedom_serial.flushInput()

    logging.debug("send_eleroha() Write frame to serial port")
    jeedom_serial.write(binascii.a2b_hex(tosend))
    logging.debug("send_eleroha() Send frame : "+ tosend)
# ----------------------------------------------------------------------------
# Read from Stick
def read_eleroha():
    #logging.debug('read_eleroha() Called (Elero stick=>deamon)')
    message = None
    try:
        byte = jeedom_serial.read()
    except Exception, e:
        logging.error("read_eleroha() error: " + str(e))
        if str(e) == '[Errno 5] Input/output error':
            logging.error("Exit 1 because this exeption is fatal")
            shutdown()
    try:
        if byte:
            message = byte + jeedom_serial.readbytes(ord(byte))
            logging.debug("read_eleroha() message: " + str(jeedom_utils.ByteToHex(message)))

            info=[]
            if decodeAck(message, info) == True:
                logging.debug("read_eleroha() message: OK")

                if str(info[0]) in globals.KNOWN_DEVICES:
                    if globals.KNOWN_DEVICES[str(info[0])]['cmd']=='settilt':
                        if str(info[1])=='0d':
                            info[1]='04'
                    elif globals.KNOWN_DEVICES[str(info[0])]['cmd']=='setintermediate':
                        if str(info[1])=='0d' or str(info[1])=='02':
                            info[1]='03'

                    targetQueue(info[0], info[1])

                    action={}
                    action['value']=str(info[1])
                    action['channel'] = str(info[0])
                    action['EqLogic_id'] = globals.KNOWN_DEVICES[str(info[0])]['EqLogic_id']
                    time.sleep(1)
                    globals.JEEDOM_COM.add_changes('info',action)
                    logging.debug('read_eleroha() message to Jeedom sent')
                else:
                    logging.error("read_eleroha() No key found in KNOWN_DEVICES")

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
            #Elero stick
            read_eleroha()
            #Jeedom
            read_socket()
            #QUEUE
            #logQueue()
            readQueue()
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
    listen()
except Exception,e:
    logging.error('Fatal error : '+str(e))
    logging.debug(traceback.format_exc())
    shutdown()
