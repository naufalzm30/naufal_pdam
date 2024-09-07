import psycopg2
import psycopg2.extensions
import time
import threading
import signal
import queue
from configparser import ConfigParser
from datetime import datetime, timedelta
import logging, sys
import pytz
from logging.handlers import RotatingFileHandler
import json
from tqdm import tqdm

# Configure root_logger to write to a rotating log file
log_file = 'logs/pdam_dump_data.log'
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




def read_last_id(file_path):
    with open(file_path) as json_file:
        data = json.load(json_file)
        return data['last_id']

def write_last_id(file_path,last_id):
    data = {'last_id': last_id}
    with open(file_path, 'w') as file:
        json.dump(data, file)

    

class SetupDB(object):
    def __init__(self):
        config = ConfigParser()
        config.read_file(open('config.ini'))
        self.db_host = config['DB']['host']
        self.db_user = config['DB']['user']
        self.db_pass= str(config['DB']['pass'])
        self.db_port = int(config['DB']['port'])
        self.db_name = str(config['DB']['dbname'])
        self.db_channel = config['DB']['channel']
       


class DBLogger:
    def __init__(self):
        self.config = SetupDB()
        self.conn = psycopg2.connect(dbname=self.config.db_name, user=self.config.db_user,
                                     password=self.config.db_pass, host=self.config.db_host, port=self.config.db_port)
        self.cursor = self.conn.cursor()

        
    def get_time_from_message(self,message):
        # message = message.split(",")
        # message = message[0]
        local_datetime_str = message.strip()
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        datetime_obj = datetime.strptime(local_datetime_str, '%Y/%m/%d %H:%M:%S')
        jakarta_time= jakarta_tz.localize(datetime_obj)
        return jakarta_time


    def log(self):
       
        try:
            print("start logging")
            # get last_id
            query = "SELECT * FROM pdam_raw_message WHERE id >= %s"
            self.cursor.execute(query, (read_last_id("last_id.json"),))
            # Fetch all rows
            rows = self.cursor.fetchall()
            print("total rows", len(rows))
            # Get the column names from the self.cursor description
            column_names = [desc[0] for desc in self.cursor.description]
            data_raw = [dict(zip(column_names, row)) for row in rows]
            # get the lasted id
            latest_id = max(data['id'] for data in data_raw)
            # lets dumpt it to sensordata
            for datas in (data_raw):
                # 2024/07/16 08:59:55,   2.00,1068.00,   0.00,   0.00,       120.02,539685,  38.00,  12.85,1085,58,2               
                data = datas['message'].split(',')
                station_id = int(datas['station_id'])
                
                # handle different logger len message todo

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

                message = {
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
                
        
                self.cursor.execute("SELECT * FROM pdam_station WHERE id=%s", (station_id,))
                station_obj = self.cursor.fetchall()
                colums_station = [desc[0] for desc in self.cursor.description]
                data_station = [dict(zip(colums_station, row)) for row in station_obj]
                # data is only one
                data_station=data_station[0]
                if float(data_station['percent_cal'])>0 and data_station['percent_cal'] is not None:

                    # try get latest ch6 in spesicif station in raw_message
                    try:
                    
                        self.cursor.execute("SELECT * FROM pdam_raw_message WHERE station_id=%s ORDER BY time DESC LIMIT 1", (station_id,))
                        raw_obj = self.cursor.fetchall()
                        column_raw_message = [desc[0] for desc in self.cursor.description]
                        data_raw_message = [dict(zip(column_raw_message, row)) for row in raw_obj]
                        
                        # data is only one
                        data_raw_message = data_raw_message[0]
                        prev_ch6 = float(data_raw_message['message'].split(",")[6])

                    # if lates ch6 is not found in raw message
                    except Exception as e:
                        print("error get latest ch6", e)
                        prev_ch6=0
                    
                    if data_station['factor_cal']:
                        modCH5 = ch5 + (ch5*float(data_station['percent_cal']))/100
                        modCH6 = modCH5*300/1000+prev_ch6
                    else:
                        modCH5 = ch5 - (ch5*float(data_station['percent_cal']))/100
                        modCH6 = modCH5*300/1000+prev_ch6
                
                else:
                    modCH5 = ch5
                    modCH6 = ch6
                
                # insert to checker
                if status ==2:
                    second = message_time.second
                    secs_cols = second//5*5  

                    # we will update data or create object
                    try:
                        query_get_time = """SELECT time FROM pdam_checker_data 
                                    WHERE station_id = %s AND secs_col = %s;"""
                        tuple_check = (station_id, secs_cols)
                        
                        try:
                            self.cursor.execute(query_get_time, tuple_check)
                            result = self.cursor.fetchone()[0]

                        except :
                            result = None

                        # print("result",result)
                        if result is not None:
                            # update this rows
                            query_update = """UPDATE pdam_checker_data 
                                        SET time = %s, "CH1"= %s, "CH2"= %s, "CH3"= %s, "CH4"= %s, 
                                        "CH5"= %s, "CH6"= %s, temperature= %s, battery= %s, 
                                        saved_data= %s, itter_flow= %s, status= %s, created_at = %s,
                                        "modCH5" =%s, "modCH6" = %s
                                        WHERE secs_col = %s and station_id = %s;"""
                            tuple_update= (message_time, ch1, ch2, ch3, ch4, ch5, ch6, temp, 
                                            batt, saved_data, itter_flow, status,created_at,modCH5,modCH6, secs_cols, station_id)
                            try:
                                with self.conn.cursor() as cur:
                                    cur.execute(query_update, tuple_update)
                                    self.conn.commit()
                                    write_last_id(last_id=int(datas['id']),file_path="last_id.json")

                            except Exception as e:
                                root_logger.error("station_id: "+ str(station_id)+"sec col: " +str(secs_cols)+" | Update Checker data ERROR on: "+str(e))

                        else :
                            # data is empty an we will create it 
                            query_checker = """
                                INSERT INTO pdam_checker_data (
                                    secs_col, time, "CH1", "CH2", "CH3", "CH4", "CH5", "CH6", temperature, battery, saved_data, itter_flow, status, station_id, "modCH5", "modCH6", created_at
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """
                            insert_data = (secs_cols, message_time, ch1, ch2, ch3, ch4, ch5, ch6, temp, batt, saved_data, itter_flow, status, station_id, modCH5, modCH6, created_at)

                            try:
                                with self.conn.cursor() as cur:
                                    cur.execute(query_checker, insert_data)
                                    self.conn.commit()
                                    write_last_id(last_id=int(datas['id']),file_path="last_id.json")
                            except Exception as e:
                                root_logger.error("Database checker "+str(e))
                                self.conn.rollback()  # Rollback the transaction on error


                    except:
                        root_logger.error("Database checker "+str(e))
                        self.conn.rollback()  # Rollback the transaction on error

                
                # insert to pdam_sensor_data
                else:
                    # insert to pdam_sensor_data
                    query_sensor_data = """INSERT INTO pdam_sensor_data (time, "CH1", "CH2", "CH3", "CH4", "CH5", "CH6", temperature, battery, saved_data, itter_flow, status, station_id, "modCH5", "modCH6", created_at)
                                        VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
                    insert_data = ( message_time, ch1, ch2, ch3, ch4, ch5, ch6,temp, batt, saved_data, itter_flow, status, station_id,modCH5,modCH6,created_at)
                    
                    try:
                        with self.conn.cursor() as cur:
                            cur.execute(query_sensor_data, insert_data)
                            self.conn.commit()
                            write_last_id(last_id=int(datas['id']),file_path="last_id.json")
                    
                    except Exception as e:
                        # root_logger.error("Database sensor data "+str(e))
                        self.conn.rollback()  # Rollback the transaction on error

                    
                    # insert to pdam_sensor_data DS
                    # get configuration between channel and sensortype
                    try:
                        self.cursor.execute("SELECT * FROM pdam_station_configuration WHERE station_id=%s", (station_id,))
                        configuration_obj = self.cursor.fetchall()
                        column_config = [desc[0] for desc in self.cursor.description]
                        configurations = [dict(zip(column_config, row)) for row in configuration_obj]

                        for config in configurations:
                            # todo create filter min max logger channel
                            # create dict from message
                            # if channel 4, if channel 6, 10
                   
                            # get channel label
                            self.cursor.execute("SELECT channel_label FROM pdam_channel where id=%s",(int(config['channel_id']),))
                            
                            value = float(message[self.cursor.fetchone()[0]])
                            
                        
                            # add filter if sensor_type is totalizer, check is curr_totalizer < prev totalizer
                         
                            self.cursor.execute("SELECT sensor_name FROM pdam_sensor_type WHERE id=%s",(int(config['sensor_type_id']),))
                            sensor_name = self.cursor.fetchone()[0]
                            # print('sensor_name', sensor_name)
                            if "Totalizer" in sensor_name:
                                
                                # get where is flow meter
                                self.cursor.execute("SELECT id FROM pdam_sensor_type WHERE sensor_name=%s",("Flow Meter",))
                                print("s")
                                flow_meter_id = int(self.cursor.fetchone()[0])
                                self.cursor.execute("SELECT channel_id FROM pdam_station_configuration WHERE station_id=%s and sensor_type_id=%s",(station_id,flow_meter_id,))
                                print("t")
                                channel_id = int(self.cursor.fetchone()[0])
                                print("w")
                                self.cursor.execute("SELECT channel_label FROM pdam_channel WHERE id=%s",(channel_id,))
                                print('u')
                                channel_label = str(self.cursor.fetchone()[0])
                                print('v')
                                current_flow = float(message[channel_label])
                                print('current_flow', current_flow)
                                
                                # get prev totalizer
                                self.cursor.execute("SELECT * FROM pdam_sensor_data_req WHERE station_id=%s and sensor_type_id=%s ORDER BY time DESC LIMIT 1",(station_id,int(config['sensor_type_id']),))
                                prev_obj = self.cursor.fetchmany()
                                if prev_obj:
                                    # print(prev_obj)
                                    print("aaa")
                                    cols = [desc[0] for desc in self.cursor.description]
                                    prev_obj = [dict(zip(cols, row)) for row in prev_obj][0]
                                    prev_data = float(prev_obj['data'])
                                    if value-prev_data<0:
                                        time_jkt = pytz.timezone('Asia/Jakarta')
                                        prev_time = prev_obj['time'].astimezone(time_jkt)
                                        time_interval = int((message_time-prev_time).total_seconds())
                                        value = prev_data+(current_flow*time_interval)*0.001
                                        print("masuk",station_id)

                                else:
                                    print("aman")
                                    value = value


                            query_sensor_data_req =  """INSERT INTO pdam_sensor_data_req (station_id, sensor_type_id, channel_id, iteration, time, status, created_at,data) 
                                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                            tuple_sensor_data = (station_id,int(config['sensor_type_id']),
                                                 int(config['channel_id']),itter_flow,message_time,status,created_at,value)
                            
                            try:
                                with self.conn.cursor() as cur:
                                    cur.execute(query_sensor_data_req, tuple_sensor_data)
                                    self.conn.commit()
                                    write_last_id(last_id=int(datas['id']),file_path="last_id.json")
                            
                            except Exception as e:
                                root_logger.error("Database sensordatareq insert "+str(e))
                                self.conn.rollback()  # Rollback the transaction on error




                    except Exception as e:
                        print("errror ",e)
                        # pass 

                    # add batt
                    self.cursor.execute("SELECT id FROM pdam_channel where channel_label=%s",("BATT",))
                    channel_batt_id = self.cursor.fetchone()[0]
                    self.cursor.execute("SELECT id FROM pdam_sensor_type where sensor_name=%s",("battery",))
                    sensor_batt_id = self.cursor.fetchone()[0]
                    value = message['batt']
                    
                    query_sensor_data_req =  """INSERT INTO pdam_sensor_data_req (station_id, sensor_type_id, channel_id, iteration, time, status, created_at,data) 
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    tuple_sensor_data = (station_id,sensor_batt_id,
                                            channel_batt_id,itter_flow,
                                            message_time,status,
                                            created_at,value)
                    
                    try:
                        with self.conn.cursor() as cur:
                            cur.execute(query_sensor_data_req, tuple_sensor_data)
                            self.conn.commit()
                            write_last_id(last_id=int(datas['id']),file_path="last_id.json")
                    
                    except Exception as e:
                        root_logger.error("Database sensordatareq insert batt "+str(e))
                        self.conn.rollback()  # Rollback the transaction on error

                    # add temp
                    self.cursor.execute("SELECT id FROM pdam_channel where channel_label=%s",("TEMP",))
                    channel_temp_id = self.cursor.fetchone()[0]
                    self.cursor.execute("SELECT id FROM pdam_sensor_type where sensor_name=%s",("temperature",))
                    sensor_temp_id = self.cursor.fetchone()[0]
                    value = message['temp']
                    
                    query_sensor_data_req =  """INSERT INTO pdam_sensor_data_req (station_id, sensor_type_id, channel_id, iteration, time, status, created_at,data) 
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    tuple_sensor_data = (station_id,sensor_temp_id,
                                            channel_temp_id,itter_flow,
                                            message_time,status,
                                            created_at,value)
                    
                    try:
                        with self.conn.cursor() as cur:
                            cur.execute(query_sensor_data_req, tuple_sensor_data)
                            self.conn.commit()
                            write_last_id(last_id=int(datas['id']),file_path="last_id.json")
                    
                    except Exception as e:
                        root_logger.error("Database sensordatareq insert temp "+str(e))
                        self.conn.rollback()  # Rollback the transaction on error

        
        except Exception as e:
            root_logger.error("Database "+str(e))
            self.conn.rollback()  # Rollback the transaction on error


    def __del__(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()



# 
def dump_data():
    if not running:
        return
    db = DBLogger()
    # check last data (id) on json
    db.log()
    # threading.Timer(60, dump_data).start()

# Global variable to control the running state
running = True

if __name__ == "__main__":
    root_logger.info("------------")
    root_logger.info("SYSTEM RESTART")
    # listener = PostgresListener()


    # def signal_handler(sig, frame):
    #     root_logger.info("Received keyboard interrupt. Disconnecting...")
    #     listener.stop()
    #     root_logger.info("Disconnected from broker and stopped listener. Exiting.")
    #     exit(0)

    def signal_handler(sig, frame):
        global running
        root_logger.info("Received keyboard interrupt. Stopping gracefully...")
        running = False
        root_logger.info("Stopped. Exiting.")
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
 
        dump_data()
        # start = 0
        # while True:
        #     time.sleep(1)
            
        #     if time.time()-start>=5:
        #         # db=DBLogger()
        #         # db.log
        #         print("a")
               
             
                # start = time.time()
            # time.sleep(1)  # Keep the main thread alive
    
    # try:
        # listener.connect()
        # t1 = threading.Thread(target=main, args=(listener,))
        # t1.start()
        # dump_data()
        # while True:
        #     try:
        #         data = listener.notification_queue.get(timeout=1)
        #         if data != initial_data:
        #             initial_data = data
        #     except queue.Empty:
        #             pass
                
      


    except Exception as e:
        
        root_logger.error(f"An error occurred: {e}")
        # listener.stop()
        root_logger.info("Disconnected from broker and stopped listener due to error.")


'''
-- CREATE OR REPLACE FUNCTION notify_insert() RETURNS trigger AS $$
-- BEGIN
--     PERFORM pg_notify('channel_collect_change', 'INSERT');
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE OR REPLACE FUNCTION notify_update() RETURNS trigger AS $$
-- BEGIN
--     PERFORM pg_notify('channel_collect_change', 'UPDATE');
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE OR REPLACE FUNCTION notify_delete() RETURNS trigger AS $$
-- BEGIN
--     PERFORM pg_notify('channel_collect_change', 'DELETE');
--     RETURN OLD;
-- END;
-- $$ LANGUAGE plpgsql;


CREATE TRIGGER insert_trigger_pdam_raw_message
AFTER INSERT ON pdam_raw_message
FOR EACH ROW
EXECUTE FUNCTION notify_insert();

CREATE TRIGGER update_trigger_pdam_raw_message
AFTER UPDATE ON pdam_raw_message
FOR EACH ROW
EXECUTE FUNCTION notify_update();

CREATE TRIGGER delete_trigger_pdam_raw_message
AFTER DELETE ON pdam_raw_message
FOR EACH ROW
EXECUTE FUNCTION notify_delete();





DROP TRIGGER IF EXISTS insert_trigger_dashboard_node ON dashboard_node;
DROP TRIGGER IF EXISTS update_trigger_dashboard_node ON dashboard_node;
DROP TRIGGER IF EXISTS delete_trigger_dashboard_node ON dashboard_node;
'''