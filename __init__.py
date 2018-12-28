import string

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.dialog import DialogLoader
from mycroft.util.log import getLogger

import socket
import struct
import re
import json

MCAST_GRP = '239.255.255.250'
MCAST_PORT = 1982
SRC_PORT = 5159 # my random port, may get changed if in use
TIMEOUT = 2     # 2 secnd timeout to get all lights
CR_LF = "\r\n"

# ensure byte format for Python3
SEARCH_CMD = b"M-SEARCH * HTTP/1.1\r\n\
  HOST: 239.255.255.250:1982\r\n\
  MAN: \"ssdp:discover\"\r\n\
  ST: wifi_bulb\r\n"

__author__ = 'Jan Newmarch jan@newmarch.name'

'''
This skill manipulates a Yeelight

and accepts the commands

  * [location] light on
  * [location] light off

if the location is given
  if there is a light with name of that location, use it
  else fail
else
  if there is only one light, use it
  else
    if Mycroft knows its own location and there is a light 
        with that name, use it
    else fail
'''


LOGGER = getLogger(__name__)

class YeelightSkill(MycroftSkill):
    def __init__(self):
        super(YeelightSkill, self).__init__(name="YeelightSkill")

    def initialize(self):
        pass


    
    @intent_handler(IntentBuilder("OnIntent").\
                    optionally("location").\
                    require("OnKeywords").build())
    def on_activity_intent(self, message):
        """Turn on Yeelight
        """
        
        LOGGER.debug("Yeelight: starting on activity")
        LOGGER.debug("Yeelight: start activity" + message.data.get('utterance'))

        location = message.data.get("location")
        LOGGER.info('Room is ' + location)

        light = select_light(location)
        if light != None:
            ip = light.ip
            port = light.port
            
            # success = set_power("on", ip, port)
            command = '{"id":1,"method":"set_power", "params":["on", "smooth", 500]}'
            success = sendto(ip, port, command)
            LOGGER.debug('Power set is' + success[0])

            if light.name == None:
                report = {"location": "unknown"}
            else:
                report = {"location": light.name}
                
            self.speak_dialog("on.activity", report)
        


    @intent_handler(IntentBuilder("OffIntent").\
                    optionally("location").\
                    require("OffKeywords").build())
    def off_activity_intent(self, message):
        """Turn off Yeelight
        """
        
        LOGGER.debug("Yeelight: starting off activity")
        LOGGER.debug("Yeelight: start activity" + message.data.get('utterance'))

        location = message.data.get("Location")

        light = select_light(location)
        if light != None:
            ip = light.ip
            port = light.port
            # success = set_power("off", ip, port)
            command = '{"id":1,"method":"set_power", "params":["off", "smooth", 500]}'
            success = sendto(ip, port, command)
            LOGGER.debug('Power set is' + success[0])

            if light.name == None:
                report = {"location": "unknown"}
            else:
                report = {"location": light.name}
                
            self.speak_dialog("off.activity", report)

    def stop(self):
        pass

class Yeelight:
    name = None
    ip = None
    port = None
    
    
def create_skill():
    return YeelightSkill()

def select_light(location):
    lights = get_lights()
    if len(lights) >= 1:
        light = Yeelight()
        LOGGER.info('Turning first light on')
        response = lights[0]
        (ip, port) = get_ip_port(response)
        name = get_name(response)
        model = get_model(response)

        light.ip = ip
        light.port = port
        light.model = model
        light.name = name
        
        LOGGER.info('Name is ' + name + ', model ' + model)
        return light
    return None
    
def get_lights():
    global SRC_PORT
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # keep trying one port after another until success
    bound = False
    while not bound:
        try:
            sock.bind(('', SRC_PORT))
            bound = True
        except socket.error as e:
            LOGGER.debug('Couldnt bind to ' +
                         str(SRC_PORT) +
                         ' trying next port')
            SRC_PORT += 1
        except OSError as e:
            LOGGER.debug('Couldnt bind to ' +
                         str(SRC_PORT) +
                         ' trying next port')
            SRC_PORT += 1

            
    sock.sendto(SEARCH_CMD, (MCAST_GRP, MCAST_PORT))
    # sock.shutdown(socket.SHUT_RDWR)
    sock.close()
    
    sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                              socket.IPPROTO_UDP)
    sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_recv.settimeout(TIMEOUT)

    lights = []
    # ensure this socket is listening on the same
    # port as the multicast went on
    sock_recv.bind(('', SRC_PORT))
    while True:
        try:
            response = sock_recv.recv(10240)
            # convert from bytes to str for Python3
            response = response.decode('utf-8')
            lights.append(response)
            LOGGER.info(response)
        except socket.timeout as e:
            LOGGER.info('recv timedout')
            break
        
    sock_recv.close()
    return lights

def get_name(response):
    # match on a line like "name: bedroom"
    # to pull name out of group(1)
    prog = re.compile("name: (.*)")
    for line in response.splitlines():
        result = prog.match(line)
        if result != None:
            name = result.group(1)
            return name
    return None

def get_model(response):
    # match on a line like "model: color"
    # to pull modle out of group(1)
    prog = re.compile("model: (.*)")
    for line in response.splitlines():
        result = prog.match(line)
        if result != None:
            model = result.group(1)
            return model
    return None

def get_ip_port(response):
    # get the name of a light
    prog = re.compile("Location: yeelight://(\d*\.\d*\.\d*\.\d*):(\d*).*")
    for line in response.splitlines():
        result = prog.match(line)
        if result != None:
            ip = result.group(1)
            port = result.group(2)
            return (ip, int(port))
    return (None, None)


    
def sendto(ip, port, command):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    sock.connect((ip, port))
    sock.send(bytes(command + CR_LF, 'utf-8'))
    response = sock.recv(10240)
    # convert from bytes to str for Python3
    response = response.decode('utf-8')
    
    # the response is a JSON string, parse it and return
    # the "result" field
    dict = json.loads(response)
    sock.close()
    #print "Response was ", response
    return(dict["result"])

def set_prop(prop, params, ip, port):
    # hard code the JSON string
    command = '{"id":1,"method":"set_' + prop +\
              '", "params":' + params +\
              '}'
    #print(command)
    response = sendto(ip, port, command)
    return response

def set_power(state, ip, port):
    params = '["' + state + '", "smooth", 500]'
    response = set_prop('power', params, ip, port)
    return response

