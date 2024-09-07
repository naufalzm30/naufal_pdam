# -*- coding: utf-8 -*-
"""
Edited on 10/04/2024 01:00
@author: Agus Raharja
V.1.1
"""

# import random
# import re
# from time import time as tm
import time
import paho.mqtt.client as mqtt
from configparser import ConfigParser
import mysql.connector
import pdam_sql_connector as log
# import psycopg2

class setup(object):
    def __init__(self):     
        config = ConfigParser()
        config.read_file(open('config.ini'))    
        self.mqtt_broker = config['Server']['Broker']
        self.mqtt_port = int(config['Server']['Port'])  # Convert port to int
        self.mqtt_userid = config['Server']['UserID']
        self.mqtt_pass = config['Server']['Pass']
        self.mqtt_KAI = config['Server']['KAI']              
        
class mqttobj(object):
    def __init__(self):
        self.start = setup()
        self.mqtt_broker = self.start.mqtt_broker
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.username_pw_set(self.start.mqtt_userid, self.start.mqtt_pass)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.mqtt_topic = []
        self.dummy_stat = {'No': {'float': None, 'active': None}}

        self.client.connect(self.mqtt_broker, self.start.mqtt_port)  # Connect with broker
    
    def get_topic(self):
        self.mqtt_topic = []
        config = ConfigParser()
        config.read_file(open('config.ini'))

        self.mydb = mysql.connector.connect(
            host=config['DB']['host'],
            user=config['DB']['user'],
            password=config['DB']['pass'],
            auth_plugin='mysql_native_password',
            database = config['DB']['dbid']
        )        

        self.mycursor = self.mydb.cursor()
        self.mycursor.execute("SELECT topic_MQTT FROM pdam_app_station")
        result = self.mycursor.fetchall()
        self.mycursor.close()
        self.mydb.close()

        if isinstance(result, list):
            for i in range(len(result)):
                self.mqtt_topic.append(result[i][0])

    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            pass
            print ("Unable to connect to MQTT Broker...")
        else: 
            print ("Connected with MQTT Broker: " + str(self.mqtt_broker))
            try:
                self.get_topic()
            except Exception as e:
                print(e)
            for i in range(len(self.mqtt_topic)):
                try:
                    client.subscribe(self.mqtt_topic[i],qos=1)
                    print(self.mqtt_topic[i])
                except Exception as e:
                    print('Client subscribe Error : ', e)
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        pass
    
    def on_message(self, client, userdata, msg):
        message = msg.payload
        self.topic = msg.topic
        print("*****************DATA************************")
        print(self.topic, " | ", message)
        print("*********************************************")
        try:
            self.decmess = message.decode("utf-8")
        except UnicodeDecodeError as e:
            print(f"UnicodeDecodeError: {e}")
            try:
                clean_message = ''.join(chr(byte) for byte in message if byte < 128)
                self.decmess = clean_message
            except:
                print(f"Clean_UnicodeDecodeError: {e}")

        DB = log.Database(self.topic)
        if self.decmess != "Logger OK!":
            try:
                DB.LoggerParse(self.decmess)
            except Exception as e:
                print('LoggerParse Error : ', e)

def main():
    mqttcon = mqttobj()
    mqttcon.client.loop_forever()

if __name__ == '__main__':
    main()
