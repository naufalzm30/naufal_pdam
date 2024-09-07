
from django.core.management.base import BaseCommand
from pdam_app.models import (StationModel, ThresholdSensorModel,
                              PublishThresholdModel)
import pytz
import paho.mqtt.client as mqtt
from configparser import ConfigParser
from django.utils import timezone


# setiap jam di menit ke 58 script ini akan terpanggil untuk mengirim threshold

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
    help = 'Publish Threshold every hour on minute 58 '

    def handle(self, *args, **kwargs):
        stations = StationModel.objects.all()
        mqtt = MQTTPublisher()
           
        DAYS_OF_WEEK = {
            "Monday": 1,
            "Tuesday": 2,
            "Wednesday": 3,
            "Thursday": 4,
            "Friday": 5,
            "Saturday": 6,
            "Sunday": 7,
        }

        # Get the current time
        time = timezone.localtime()
        print(time)
        hour = time.hour+1
        # Get the current day name
        day_name = time.strftime('%A')  # This will give you "Monday", "Tuesday", etc.

        # Get the integer value for the day
        day_int = DAYS_OF_WEEK.get(day_name)

        if hour==24:
            hour =0
            day_int=day_int+1

            if day_int>7:
                day_int=1

        str_hour = str(hour)
        if len(str_hour)==1:
            str_hour="0"+str_hour

        

        for station in stations:
            thresholds = ThresholdSensorModel.objects.filter(station=station,hour=hour,day=day_int).order_by("minute")
            topic = station.topic
            topic = topic+"/th"
            str_message = str_hour
            
            for index,threshold in enumerate(thresholds):
                # "hh/1_min1_max1/2_min2_max2/........./11_min11_max11/12_min12_max12
                str_message+="/"+str(index+1)+"_"+str(int(threshold.min))+"_"+str(int(threshold.max))
           
            mqtt.publish(topic, message=str_message)

            PublishThresholdModel.objects.update_or_create(
                station=station, hour=hour,day=day_int,
                defaults={
                    "created_at":timezone.localtime(),
                    "message":str_message,
                    "is_sent":False
                }
            )
            # Disconnect from the broker
            mqtt.disconnect()