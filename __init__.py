import string

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.dialog import DialogLoader
from mycroft.util.log import getLogger

import yeelight
from yeelight import Bulb

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
  if there is at least one light, use the first one found
  else fail
'''


LOGGER = getLogger(__name__)

class YeelightSkill(MycroftSkill):
    def __init__(self):
        super(YeelightSkill, self).__init__(name="YeelightSkill")

    def initialize(self):
        self.light_wrapper = LightWrapper()
    
    @intent_handler(IntentBuilder("OnIntent").\
                    optionally("location").\
                    require("OnKeywords").build())
    def on_activity_intent(self, message):
        """Turn on Yeelight
        """
        
        LOGGER.debug("Yeelight: start activity" + message.data.get('utterance'))

        location = message.data.get("location")
        if location != None:
            LOGGER.info('Room is ' + location)
        else:
            LOGGER.info('No room given')
            
        light, name = self.select_light(location)
        if light != None:
            light.turn_on()
            
            if name == None:
                report = {"location": "unknown"}
            else:
                report = {"location": name}
                
            self.speak_dialog("on.activity", report)
        else:
            self.speak_dialog("fail")
            
            

    @intent_handler(IntentBuilder("OffIntent").\
                    optionally("location").\
                    require("OffKeywords").build())
    def off_activity_intent(self, message):
        """Turn off Yeelight
        """
        
        LOGGER.debug("Yeelight: start activity" + message.data.get('utterance'))

        location = message.data.get("location")

        light, name = self.select_light(location)
        if light != None:
            light.turn_off()
 
            if name == None:
                report = {"location": "unknown"}
            else:
                report = {"location": name}
                
            self.speak_dialog("off.activity", report)
        else:
            self.speak_dialog("fail")
 

    def select_light(self, location):
        #yeelights = yeelight.discover_bulbs()
        yeelights = self.light_wrapper.discover_bulbs()
        LOGGER.info("Num Yeelights {}".format(len(yeelights)))
        LOGGER.info(str(yeelights))
        
        if location != None:
            for light_info in yeelights:
                name = light_info['capabilities']['name']
                if name == location:
                    ip = light_info['ip']
                    #light = Bulb(ip)
                    light = self.light_wrapper.new_light(ip)
                    
                    LOGGER.info("Yeelight ip {}".format(ip))
                    
                    return light, name
                
            LOGGER.info('No light matching ' + location)
            return None, None
            
        if len(yeelights) >= 1:
            light_info = yeelights[0]
            ip = light_info['ip']
            name = light_info['capabilities']['name']
            
            LOGGER.info("Yeelight ip {}".format(ip))
            
            light = Bulb(ip)
            return light, name
        
        return None, None
    

    def stop(self):
        pass


class LightWrapper:
    """ Wrapper around yeelight package so it
    can be overriden for testing
    """

    @staticmethod
    def discover_bulbs():
        return yeelight.discover_bulbs(timeout=5)

    @staticmethod
    def new_light(ip):
        return yeelight.Bulb(ip)
    
def create_skill():
    return YeelightSkill()


