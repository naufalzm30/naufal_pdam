import csv
from django.core.management.base import BaseCommand
from pdam_app.models import (SensorDataModel, SensorDataReqModel,
                              StationConfigurationModel, StationModel,
                            RawMessagemodel,SensorTypeModel,
                            ChannelModel, CheckerDataModel)
import json
from datetime import datetime
import pytz
from tqdm import tqdm
import logging,sys
from logging.handlers import RotatingFileHandler
import os

# Configure root_logger to write to a rotating log file
log_file = 'pdam_app/management/commands/logs/message2checkersensordata.log'
max_log_size = 50 * 1024 * 1024  # 50 MB
backup_count = 50  # Keep up to 50 backup log files
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# Create a RotatingFileHandler
file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count)
file_handler.setFormatter(formatter)

# Create a StreamHandler to log to stdout
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# Get the root logger
root_logger = logging.getLogger()

# Set the root_logger level
root_logger.setLevel(logging.INFO)

# Add the handlers to the root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)


# Lock file path
LOCK_FILE = "pdam_app/management/commands/task.lock"



class Command(BaseCommand):
    help = 'Logging message to checker, sensordata'

    def read_last_id(self,file_path):
        with open(file_path) as json_file:
            data = json.load(json_file)
            return data['last_id']

    def write_last_id(self,file_path,last_id):
        data = {'last_id': last_id}
        with open(file_path, 'w') as file:
            json.dump(data, file)

    def get_time_from_message(self,message):
        # message = message.split(",")
        # message = message[0]
        local_datetime_str = message.strip()
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        datetime_obj = datetime.strptime(local_datetime_str, '%Y/%m/%d %H:%M:%S')
        jakarta_time= jakarta_tz.localize(datetime_obj)
        return jakarta_time

    def handle(self, *args, **kwargs):
        # Check if lock file exists
        if os.path.exists(LOCK_FILE):
            root_logger.info("Task is already running. Exiting.")
            return
        
        # Create lock file
        with open(LOCK_FILE, 'w') as lock_file:
            lock_file.write("Locked")

        try:
            root_logger.info("============START TO DUMPS DATA===============")
            last_id = self.read_last_id('pdam_app/management/commands/last_id.json')
            print(last_id)
            messages = list(RawMessagemodel.objects.filter(id__gte=last_id).exclude(status=-1).values())
            print(len(messages))
            for message in tqdm(messages):
                data = message['message'].split(',')
                ch1 = float(data[1])
                ch2 = float(data[2])
                ch3 = float(data[3])
                ch4 = float(data[4])
                ch5 = float(data[5])
                ch6 = float(data[6])        
                temp = float(data[7])
                batt = float(data[8])
                saved_data = int(data[9])
                itter_flow = int(data[10])
                status = int(data[11][0]) 
                created_at = datetime.now()
                created_at = pytz.timezone('Asia/Jakarta').localize(created_at)
                message_time = self.get_time_from_message(data[0])

                station_topic = message['topic']
                station = StationModel.objects.get(topic=station_topic)
                station_id = station.id
                modCH5=ch5
                modCH6 = ch6
                percent_cal = station.percent_cal
                # print(percent_cal)
                if percent_cal is not None and percent_cal>0:
                    try:
                        factor_cal = station.factor_cal
                    
                        # Get the previous ch6 value and handle None by setting it to 0
                        prev_ch6 = None
                        prev_data = SensorDataModel.objects.filter(station__id=station_id).order_by('-time').values().first()
                        prev_ch6 = float(prev_data['CH6']) 
                        
                      
                        if factor_cal:
                            modCH5 = ch5 + (ch5*float(percent_cal))/100
                            modCH6 = modCH5*300/1000+prev_ch6
                        else:
                            modCH5 = ch5 - (ch5*float(percent_cal))/100
                            modCH6 = modCH5*300/1000+prev_ch6
                    except Exception as e :
                        print(e)
                        # first data that has percent cal but doesnt has prev ch6
                        modCH5=ch5
                        modCH6=ch6

                # check status
                if status==2:  #checker data
                    second = message_time.second
                    secs_cols = second//5*5  
                    CheckerDataModel.objects.update_or_create(
                        secs_col = secs_cols,
                        station= station,
                        defaults={
                            "status":status,
                            "time" : message_time,
                            "created_at" : created_at,
                            "CH1":ch1,
                            "CH2":ch2,
                            "CH3":ch3,
                            "CH4":ch4,
                            "CH5":ch5,
                            "CH6":ch6,
                            "modCH5":modCH5,
                            "modCH6":modCH6,
                            "battery":batt,
                            "temperature":temp,
                            "itter_flow" : itter_flow,
                            "saved_data" : saved_data,
                        }
        
                    )
                    self.write_last_id('pdam_app/management/commands/last_id.json', message['id'])

                # status 0 or 1 we shall insert it to sensor data and sensordatareq
                else:
                    try:
                        # save to sensordata
                        SensorDataModel.objects.create(
                            created_at=created_at,
                            time = message_time,
                            CH1=ch1,
                            CH2=ch2,
                            CH3=ch3,
                            CH4=ch4,
                            CH5=ch5,
                            CH6=ch6,
                            battery= batt,
                            temperature= temp,
                            itter_flow = itter_flow,
                            saved_data=saved_data,
                            modCH5=modCH5,
                            modCH6=modCH6,
                            status=status,
                            station=station,
                        )
                        self.write_last_id('pdam_app/management/commands/last_id.json', message['id'])
                    except Exception as e:
                        print("error insert to sensordata",e )

                    # save to sensordatareq
                    # get stationconfiguration first
                    configurations = StationConfigurationModel.objects.filter(station=station).values()
                    
                    
                    # if(len(configurations))>0:
                    for config in configurations:
                        channel_id = config['channel_id']
                        sensor_type_id = config['sensor_type_id']
                        channel_label = ChannelModel.objects.get(id=channel_id).channel_label
                        sensor_type_name = SensorTypeModel.objects.get(id=sensor_type_id).sensor_name
                        # print('sensor_type_name', sensor_type_name)

                        message_dict = {
                            "CH1":ch1,
                            "CH2":ch2,
                            "CH3":ch3,
                            "CH4":ch4,
                            "CH5":ch5,
                            "CH6":ch6,
                            "temp":temp,
                            "batt":batt,
                            "itter_flow":itter_flow,
                            "message_time": message_time
                        }
                        value = message_dict[channel_label]

                        totalizers_list= ['Totalizer',"totalizer","TOTALIZER"]
                        flow_meter_list = ['Flow Meter',"flowmeter","FLOWMETER" "FLOW METER","flow meter"]

                        if sensor_type_name in totalizers_list:
                            prev_data = SensorDataReqModel.objects.filter(station=station, channel__id=channel_id,sensor_type__id = sensor_type_id).order_by('-time').values().first()
                            # prev_value = prev_value['data']
                            if prev_data is not None:
                                
                                prev_value = prev_data['data']
                                prev_time = prev_data['time']   
                                time_jkt = pytz.timezone('Asia/Jakarta')
                                prev_time = prev_time.astimezone(time_jkt) 
                                if value-prev_value<0:
                                    
                                    # check where is flowmeter
                                    sensor_obj = SensorTypeModel.objects.filter(sensor_name__in=flow_meter_list).values().first()
                                    flow_channel = StationConfigurationModel.objects.filter(station=station, sensor_type__id = sensor_obj['id']).values().first()
                                    # print(flow_channel, station_id)


                                    flow_channel = flow_channel['channel_id']
                                    flow_channel = ChannelModel.objects.filter(id=flow_channel).values().first()
                                    flow_channel = flow_channel['channel_label']
                                    flow = message_dict[flow_channel]

                                    time_interval = int((message_time-prev_time).total_seconds())
                                    value = prev_value+(flow*time_interval)*0.001
                                else:
                                    value = value
                
                            else:
                                value= value                                
                        try:
                            SensorDataReqModel.objects.create(
                                status=status,
                                created_at=created_at,
                                time = message_time,
                                data=value,
                                sensor_type = SensorTypeModel.objects.get(id=sensor_type_id),
                                channel = ChannelModel.objects.get(id=channel_id),
                                iteration = itter_flow,
                                station =station   
                            )
                            self.write_last_id('pdam_app/management/commands/last_id.json', message['id'])
                        except Exception as e:
                            print("error insert sensordatareq", message, e)

                    # save batt and temperature event this station hasn't configuration
                    # save battery and temperature
                    batt_channel_id = ChannelModel.objects.filter(channel_label="BATT").values().first()
                    batt_channel_id = batt_channel_id['id']
                    batt_sensor_id = SensorTypeModel.objects.filter(sensor_name="battery").values().first()
                    batt_sensor_id = batt_sensor_id['id']
                    try:
                        SensorDataReqModel.objects.create(
                            status=status,
                            created_at=created_at,
                            time = message_time,
                            data=batt,
                            sensor_type = SensorTypeModel.objects.get(id=batt_sensor_id),
                            channel = ChannelModel.objects.get(id=batt_channel_id),
                            iteration = itter_flow,
                            station =station   
                        )
                        self.write_last_id('pdam_app/management/commands/last_id.json', message['id'])
                    except Exception as e:
                        print("error insert batt", message, e)
                    
                    temp_channel_id = ChannelModel.objects.filter(channel_label="TEMP").values().first()
                    temp_channel_id = temp_channel_id['id']
                    temp_sensor_id = SensorTypeModel.objects.filter(sensor_name="temperature").values().first()
                    temp_sensor_id = temp_sensor_id['id']
                    try:
                        SensorDataReqModel.objects.create(
                            status=status,
                            created_at=created_at,
                            time = message_time,
                            data=temp,
                            sensor_type = SensorTypeModel.objects.get(id=temp_sensor_id),
                            channel = ChannelModel.objects.get(id=temp_channel_id),
                            iteration = itter_flow,
                            station =station   
                        )
                        self.write_last_id('pdam_app/management/commands/last_id.json', message['id'])
                    except Exception as e:
                        print("error insert temp",message,e)
            
        except Exception as e:
            print("error exception", e)  

        
        finally:
            # Remove the lock file once processing is complete
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)