# -*- coding: utf-8 -*-
"""
Edited on 10/04/2024 01:00
@author: Agus Raharja
V.1.1
"""

from datetime import datetime, timedelta
import mysql.connector
from configparser import ConfigParser
import random
# import psycopg2

from contextlib import contextmanager

@contextmanager
def create_db_connection(config):
    db_connection = mysql.connector.connect(
        host=config['DB']['host'],
        user=config['DB']['user'],
        password=config['DB']['pass'],
        auth_plugin='mysql_native_password',
        database=config['DB']['dbid']
    )
    # db_connection = psycopg2.connect(
    #     host=config['DB']['host'],
    #     user=config['DB']['user'],
    #     password=config['DB']['pass'],
    #     auth_plugin='mysql_native_password',
    #     database=config['DB']['dbid']
    # )
    yield db_connection
    db_connection.close()

class Database(object):
    def __init__(self,topic):
        self.topic = topic
        self.config = ConfigParser()
        self.config.read_file(open('config.ini'))

        print("================================")
        print("topic: ", self.topic)
        query = """SELECT id FROM pdam_app_station WHERE topic_MQTT = %s;"""
        data_tuple = (self.topic,)
        try:
            result = self.execute_sql(query, data_tuple)
            if result:
                self.station_id = result[0]
        except Exception as e:
            self.station_id = None
            print("BD log error : ", e)
        print("station : ", self.station_id)

    def execute_sql(self, query, data_tuple=None):
        with create_db_connection(self.config) as db_connection:
            cursor = db_connection.cursor()
            cursor.execute(query, data_tuple)
            if query.startswith("SELECT"):
                result = cursor.fetchone()
                # print("ex_result: ", result)
            else:
                db_connection.commit()
                result = None
                # print("ex_commit Done")
        return result

    def LoggerParse(self,data_raw):
        print(self.topic," | ", "raw data: ", data_raw)
        data = data_raw.split(',')
        date_time = data[0]
        date_time = date_time.replace('/','-')
        # print(date_time)
        yeardate = date_time.split(' ')[0]

        year = int(yeardate.split('-')[0])
        month = int(yeardate.split('-')[1])
        date = (yeardate.split('-')[2])
        timehour = date_time.split(' ')[1]
        hour = int(timehour.split(':')[0])

        minute = int(timehour.split(':')[1])
        second = int(timehour.split(':')[2])

        current_year = datetime.now().year

        if year == 0:
            year = 2024
            date_time = "{:d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(year, month, int(date), hour, minute, second)
        elif year == current_year + 43:
            # print("Change year : ", self.topic, year)
            year = current_year
            date_time = "{:d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(year, month, int(date), hour, minute, second)

        date_time_obj = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')

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
        
        checktablequery = """SELECT date_time FROM (SELECT date_time FROM pdam_app_sensor_data WHERE station_id = %s 
                            ORDER BY id DESC LIMIT 3825) AS ATX WHERE date_time = %s;"""
        data_tuple_check = (self.station_id, date_time)
        try:
            result = self.execute_sql(checktablequery, data_tuple_check)
            check = result
            print(self.topic," | ", "result check date_time: ", check)
        except Exception as e:
            check = None
            print(self.topic," | ", "checktablequery error : ", e)        
        
        ''' Checker data'''
        if status==2:
            print(self.topic," | ", "--------------Checker Data---------------")
            secs_cols = second//5*5           

            try:                
                query_hour_res = """SELECT date_time FROM pdam_app_checker_data 
                                    WHERE station_id = %s AND secs_col = %s;"""
                data_tuple_res = (self.station_id, secs_cols)
                try:
                    result = self.execute_sql(query_hour_res, data_tuple_res)
                    secs_res = result
                    print(self.topic," | ", "result check checker data: ", secs_res)
                except Exception as e:
                    secs_res = None
                    print(self.topic," | ", "Get result check checker data error : ", e)

                if secs_res is not None:
                    if secs_res[0] < date_time_obj:
                        query_checker = """UPDATE pdam_app_checker_data 
                                        SET date_time = %s, CH1= %s, CH2= %s, CH3= %s, CH4= %s, 
                                        CH5= %s, CH6= %s, temperature= %s, battery= %s, 
                                        saved_data= %s, itter_flow= %s, status= %s
                                        WHERE secs_col = %s and station_id = %s;"""
                        data_tuple_hourly= (date_time, ch1, ch2, ch3, ch4, ch5, ch6, temp, 
                                            batt, saved_data, itter_flow, status, secs_cols, self.station_id)
                        try:
                            secs_result = self.execute_sql(query_checker, data_tuple_hourly)
                            print(self.topic," | ", "Update Checker data on: ", data_raw)
                        except Exception as e:
                            print(self.topic," | ", "Update Checker data ERROR on: ", e)
                    else:
                        pass
                else:
                    query_checker = """INSERT INTO pdam_app_checker_data 
                                    (secs_col, date_time, CH1, CH2, CH3, CH4, CH5, CH6, 
                                    temperature, battery, saved_data, itter_flow, status, station_id) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
                    data_tuple_hourly= (secs_cols, date_time, ch1, ch2, ch3, ch4, ch5, ch6,
                                        temp, batt, saved_data, itter_flow, status, self.station_id)
                    try:
                        secs_result = self.execute_sql(query_checker, data_tuple_hourly)
                        print(self.topic," | ", "Insert Checker data on: ", data_raw)
                    except Exception as e:
                        print(self.topic," | ", "Insert Checker data ERROR on: ", e)

            except Exception as e:
                print(self.topic," | ", "Checker_data error : ", e)
            
            print(self.topic," | ", "----------------------------------------")
        
        else:
            print(self.topic," | ", "--------------Sensor Data---------------")
            if check is not None:
                if check[0] == date_time_obj:
                    pass
                else:
                    query = """INSERT INTO pdam_app_sensor_data (date_time, CH1, CH2, CH3, CH4, CH5, CH6, 
                            temperature, battery, saved_data, itter_flow, status, station_id) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
                    data_tuple=(date_time, ch1, ch2, ch3, ch4, ch5, ch6, 
                                temp, batt, saved_data, itter_flow, status, self.station_id)

                    try:
                        data_result = self.execute_sql(query, data_tuple)
                        print(self.topic," | ", "Insert Sensor data (check not None) on: ", data_raw)
                    except Exception as e:
                        print(self.topic," | ", "Insert Sensor data (check not None) ERROR on: ", e)
                    
            elif check is None:
                query = """INSERT INTO pdam_app_sensor_data 
                        (date_time, CH1, CH2, CH3, CH4, CH5, CH6, temperature, battery, 
                        saved_data, itter_flow, status, station_id) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
                data_tuple=(date_time, ch1, ch2, ch3, ch4, ch5, ch6, 
                            temp, batt, saved_data, itter_flow, status, self.station_id)

                try:
                    data_result = self.execute_sql(query, data_tuple)
                    print(self.topic," | ", "Insert Sensor data (check is None) on: ", data_raw)
                except Exception as e:
                    print(self.topic," | ", "Insert Sensor data (check is None) ERROR on: ", e)
            print(self.topic," | ", "----------------------------------------")

            print(self.topic," | ", "--------------Hourly Data---------------")
            try:                
                hourly = hour + 1 if minute >= 35 else hour
                if hourly == 24:
                    hourly = 0

                query_hour_res = """SELECT date_time FROM pdam_app_hourly_data 
                                    WHERE station_id = %s AND hour_col = %s;"""
                data_tuple_res = (self.station_id, hourly)
                try:
                    result = self.execute_sql(query_hour_res, data_tuple_res)
                    hour_res = result
                    print(self.topic," | ", "result check Hourly data: ", hour_res)
                except Exception as e:
                    hour_res = None
                    print(self.topic," | ", "Get result check Hourly data error : ", e)

                if hour_res is not None:
                    if hour_res[0] < date_time_obj:
                        query_hourly = """UPDATE pdam_app_hourly_data SET 
                                        date_time = %s, CH1= %s, CH2= %s, CH3= %s, CH4= %s, 
                                        CH5= %s, CH6= %s, temperature= %s, battery= %s, 
                                        saved_data= %s, itter_flow= %s, status= %s
                                        WHERE hour_col = %s and station_id = %s;"""
                        
                        data_tuple_hourly = (date_time, ch1, ch2, ch3, ch4, ch5, ch6, temp, 
                                            batt, saved_data, itter_flow, status, hourly, self.station_id)
                        try:
                            hour_result = self.execute_sql(query_hourly, data_tuple_hourly)
                            print(self.topic," | ", "Update Hourly data on: ", data_raw)
                        except Exception as e:
                            print(self.topic," | ", "Update Hourly data ERROR on: ", e)
                    else:
                        print(self.topic," | ", "(hour_res on else) Hourly data not update because data is up to date")
                        pass
                else:
                    query_hourly = """INSERT INTO pdam_app_hourly_data 
                                    (hour_col, date_time, CH1, CH2, CH3, CH4, CH5, CH6, 
                                    temperature, battery, saved_data, itter_flow, status, station_id)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
                    data_tuple_hourly = (hourly, date_time, ch1, ch2, ch3, ch4, ch5, ch6,
                                        temp, batt, saved_data, itter_flow, status, self.station_id)
                    try:
                        hour_result = self.execute_sql(query_hourly, data_tuple_hourly)
                        print(self.topic," | ", "Insert Hourly data on: ", data_raw)
                    except Exception as e:
                        print(self.topic," | ", "Insert Hourly data ERROR on: ", e)

            except Exception as e:
                print(self.topic," | ", "Hourly error : ", e)
            print(self.topic," | ", "----------------------------------------")
