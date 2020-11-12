import shared
import logging
import string
import sys
import os
import time
import argparse
import datetime
import binascii
import re
import signal
import traceback
from optparse import OptionParser
from os.path import join
import json
import uuid

from Queue import Queue

try:
    from jeedom.jeedom import *
except ImportError:
    print("Error: importing module jeedom.jeedom")
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
def read_stick(name):
    while 1:
        time.sleep(0.02)
        message = None
        try:
            byte = shared.JEEDOM_SERIAL.read()
        except Exception as e:
            logging.error("read_stick() error: " + str(e))
            if str(e) == '[Errno 5] Input/output error':
                logging.error("Exit 1 because this exeption is fatal")
                shutdown()

        try:
            if byte != 0 and  byte != None :
                message = byte + shared.JEEDOM_SERIAL.readbytes(ord(byte))
                logging.debug("read_stick() message: " + str(jeedom_utils.ByteToHex(message)))

                info=[]
                if decodeAck(message, info) == True:
                    logging.debug("read_stick() Ack: OK")

                    if CMD_IN_PROCESS.empty() == True:
                        logging.debug("read_stick() received Ack without item into CMD_IN_PROCESS queue")
                    else:
                        queue_item=CMD_IN_PROCESS.get()
                        send_to_jeedom={"info":{"channel":str(info[0]), "value":str(info[1]), "EqLogic_id":queue_item.get("eqlogic_id")}}
                        shared.JEEDOM_COM.send_change_immediate(send_to_jeedom)
                        logging.debug('read_stick() message to Jeedom sent')

        except OSError, e:
            logging.error("read_eleroha() error on decode message : " + str(jeedom_utils.ByteToHex(message))+" => "+str(e))
# ----------------------------------------------------------------------------
def write_stick(id, eqlogic_id, frame, timer_id):
    logging.debug('write_stick() Called')

    if CMD_IN_PROCESS.empty() == True:
        shared.JEEDOM_SERIAL.flushOutput()
        shared.JEEDOM_SERIAL.flushInput()
        shared.JEEDOM_SERIAL.write(binascii.a2b_hex(frame))
        logging.debug("Write frame : "+ str(frame))

        device_item={"id":id, "eqlogic_id":eqlogic_id, "frame":frame, "timer_id":timer_id}
        CMD_IN_PROCESS.put(device_item)
        logging.debug("Add cmd in process in CMD_IN_PROCESS queue")

        if timer_id:
            del shared.TIMER_LISTE[timer_id]
            logging.debug("Del timer from the TIMER_LISTE")
    else:
        logging.debug("Cmd already in CMD_IN_PROCESS queue")
# ----------------------------------------------------------------------------
def read_jeedom(name):
    while 1:
        time.sleep(0.02)
        try:
            global JEEDOM_SOCKET_MESSAGE
            if not JEEDOM_SOCKET_MESSAGE.empty():
                logging.debug("read_jeedom() New message received")
                # message = json.loads(jeedom_utils.stripped(JEEDOM_SOCKET_MESSAGE.get()))
                message = json.loads(JEEDOM_SOCKET_MESSAGE.get().decode("utf-8") )

                if message['apikey'] != _apikey:
                    logging.error("read_jeedom() Invalid apikey from socket : " + str(message))
                    return

                if message.has_key('queueing')==False:
                    message['queueing']=0

                logging.debug('read_jeedom() Device ID: '+str(message['device']['id']))
                logging.debug('read_jeedom() Device EQLOGIC_ID: '+str(message['device']['EqLogic_id']))
                logging.debug('read_jeedom() Device CMD: '+str(message['cmd']))
                logging.debug('read_jeedom() Device QUEUED: '+str(message['queueing']))

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
                    frametosend="".join(frame)
                    device_item={"id":message['device']['id'], "eqlogic_id":message['device']['EqLogic_id'], "frame":frametosend, "timer_id":False}
                    request_info=False
                    if message['cmd'] != 'getinfo':
                        oktosend=easyInfo(int(message['device']['id']), frame)
                        if oktosend==True:
                            frametosend="".join(frame)
                            device_item_info={"id":message['device']['id'], "eqlogic_id":message['device']['EqLogic_id'], "frame":frametosend, "timer_id":False}
                            request_info=True

                    if message['queueing']==0:
                        logging.debug("No queued message send directly to the stick")
                        write_stick(**device_item)
                        if request_info:
                            timer = threading.Timer(10, write_stick, [], device_item_info)
                            timer.start()

                            timer = threading.Timer(180, write_stick, [], device_item_info)
                            timer.start()
                    else:
                        logging.debug("Queue activated for the device")
                        queue_delay=15
                        now=int(time.time())

                        if len(shared.TIMER_LISTE) < 31 :
                            logging.debug("Less then 30 items in TIMER_LISTE: queueing ok")

                            timer_id=str(uuid.uuid4())
                            device_item["timer_id"]=timer_id

                            if len(shared.TIMER_LISTE)==0:
                                logging.debug("First item in TIMER_LISTE")
                                shared.ACTION_TIME=now-10

                            # le prochain timer est-il passe
                            if shared.ACTION_TIME < now:
                                # prochain timer dans 2s
                                new_timer_time=2
                            else:
                                # dans combien de temps a lieu le prochain timer
                                next_timer_time=shared.ACTION_TIME-now
                                # Timer suivant dans next_timer+15s
                                new_timer_time=next_timer_time+queue_delay

                            logging.debug("New timer in "+str(new_timer_time))
                            shared.ACTION_TIME=now+new_timer_time

                            timer = threading.Timer(new_timer_time, write_stick, [], device_item)
                            timer.start()
                            shared.TIMER_LISTE[timer_id]=timer

                            if request_info:
                                timer = threading.Timer((new_timer_time+10), write_stick, [], device_item_info)
                                timer.start()

                                timer = threading.Timer((new_timer_time+180), write_stick, [], device_item_info)
                                timer.start()

                        else:
                            logging.debug("More than 30 items in TIMER_LISTE")

        except Exception as e:
        			logging.error('Error on read socket: '+str(e))
# ----------------------------------------------------------------------------
def listen():
    logging.debug("Start listening...")
    jeedom_socket.open()
    shared.JEEDOM_SERIAL.open()
    shared.JEEDOM_SERIAL.flushOutput()
    shared.JEEDOM_SERIAL.flushInput()
    try:
        threading.Thread(target=read_jeedom,args=('socket',)).start()
        logging.debug('Read from Jeedom Thread Launched')
        threading.Thread(target=read_stick,args=('read',)).start()
        logging.debug('Read from Elero stick Thread Launched')
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt, shutdown")
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
		shared.JEEDOM_SERIAL.close()
	except:
		pass
	logging.debug("Exit 0")
	sys.stdout.flush()
	os._exit(0)
# ----------------------------------------------------------------------------
def clearqueue():
    shared.ACTION_TIME = 0
    shared.TIMER_LISTE = {}
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
_log_level = "debug"
_socket_port = 55030
_socket_host = '127.0.0.1'
_device = ''
_pidfile = '/tmp/elerohad.pid'
_apikey = ''
_callback = ''
_serial_rate = 38400
_serial_timeout = 0
_cycle = 0.3
_protocol = None

parser = argparse.ArgumentParser(description='elerohad Daemon for Jeedom plugin')
parser.add_argument("--device", help="Device", type=str)
parser.add_argument("--socketport", help="Socketport for server", type=str)
parser.add_argument("--sockethost", help="Sockethost for server", type=str)
parser.add_argument("--loglevel", help="Log Level for the daemon", type=str)
parser.add_argument("--callback", help="Callback", type=str)
parser.add_argument("--apikey", help="Apikey", type=str)
parser.add_argument("--cycle", help="Cycle to send event", type=str)
parser.add_argument("--protocol", help="Protocol to enable", type=str)
parser.add_argument("--serialrate", help="Device serial rate", type=str)
parser.add_argument("--pid", help="Pid file", type=str)
args = parser.parse_args()

if args.device:
    _device = args.device
if args.socketport:
    _socket_port = int(args.socketport)
if args.sockethost:
    _socket_host = args.sockethost
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
if args.cycle:
    _cycle = float(args.cycle)

jeedom_utils.set_log_level(_log_level)

logging.info('Start elerohad')
logging.info('Log level : '+str(_log_level))
logging.info('Socket port : '+str(_socket_port))
logging.info('Socket host : '+str(_socket_host))
logging.info('PID file : '+str(_pidfile))
logging.info('Device : '+str(_device))
logging.info('Apikey : '+str(_apikey))
logging.info('Callback : '+str(_callback))
logging.info('Cycle : '+str(_cycle))
logging.info('Serial rate : '+str(_serial_rate))
logging.info('Serial timeout : '+str(_serial_timeout))
logging.info('Protocol : '+str(_protocol))

if _device is None:
	logging.error('No device found')
	shutdown()

logging.info('Find device : '+str(_device))

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

try:
    jeedom_utils.write_pid(str(_pidfile))
    shared.JEEDOM_COM = jeedom_com(apikey = _apikey,url = _callback,cycle=_cycle)
    if not shared.JEEDOM_COM.test():
        logging.error('Network communication issues. Please fixe your Jeedom network configuration.')
        shutdown()
    shared.JEEDOM_SERIAL = jeedom_serial(device=_device,rate=_serial_rate,timeout=_serial_timeout)
    jeedom_socket = jeedom_socket(port=_socket_port,address=_socket_host)

    CMD_IN_PROCESS = Queue()

    listen()
except Exception as e:
    logging.error('Fatal error : '+str(e))
    logging.debug(traceback.format_exc())
    shutdown()
