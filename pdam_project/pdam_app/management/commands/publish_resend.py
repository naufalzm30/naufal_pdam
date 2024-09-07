
from django.core.management.base import BaseCommand
from pdam_app.models import (StationModel, PublishResendModel)
import pytz
import paho.mqtt.client as mqtt
from configparser import ConfigParser
from django.utils import timezone

class SetupMQTT(object):
    def __init__(self):
        config = ConfigParser()
        config.read_file(open('pdam_app/management/commands/config.ini'))
        self.mqtt_broker = config['Server']['Broker']
        self.mqtt_port = int(config['Server']['Port'])  # Convert port to int
        self.mqtt_userid = config['Server']['UserID']
        self.mqtt_pass = config['Server']['Pass']


class MQTTPublisher:
    def __init__(self):
        self.config = SetupMQTT()
        self.broker_address = self.config.mqtt_broker
        self.port = self.config.mqtt_port
        self.username = self.config.mqtt_userid
        self.password = self.config.mqtt_pass
        self.client = mqtt.Client()
        self.client.username_pw_set(self.username, self.password)

    def connect(self):
        # Connect to the MQTT broker
        self.client.connect(self.broker_address, self.port)

    def publish(self, topic, message, retain=True):
        # Publish a message to a specific topic with the retain flag
        self.client.publish(topic, message, retain=retain)

    def disconnect(self):
        # Disconnect from the MQTT broker
        self.client.disconnect()


class Command(BaseCommand):
    help = 'Publish resend '

    def handle(self, *args, **kwargs):
        data_resend =PublishResendModel.objects.filter(is_sent=False)
        mqtt = MQTTPublisher()

        for data in data_resend:
            topic = data.station.topic
            topic +="/resend"
            date = data.date
            year = date.year
            month = str(date.month)
            day = str(date.day)
            if len(day)<2:
                day = "0"+day
            
            if len(month)<2:
                month = "0"+month
            
            message = "/"+str(year)+"/"+str(month)+'/'+str(day)
  
            mqtt.connect()
            mqtt.publish(topic, message=message)

            # set is_sent to True
            data.is_sent = True
            data.save()
            # Disconnect from the broker
            mqtt.disconnect()