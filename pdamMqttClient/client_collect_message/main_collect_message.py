import psycopg2
import psycopg2.extensions
import time
import threading
import signal
import paho.mqtt.client as mqtt
import queue
from configparser import ConfigParser
from datetime import datetime
import logging, sys
import pytz
from logging.handlers import RotatingFileHandler



# Configure root_logger to write to a rotating log file
log_file = 'logs/pdam_collect.log'
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


class SetupMQTT(object):
    def __init__(self):
        config = ConfigParser()
        config.read_file(open('config.ini'))
        self.mqtt_broker = config['Server']['Broker']
        self.mqtt_port = int(config['Server']['Port'])  # Convert port to int
        self.mqtt_userid = config['Server']['UserID']
        self.mqtt_pass = config['Server']['Pass']

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

class PostgresListener:
    def __init__(self):
        self.config = SetupDB()
        self.conn = None
        self.data = None  # Variable to store the fetched data
        self.stop_event = threading.Event()
        self.notification_queue = queue.Queue()

    def connect(self):
        self.conn = psycopg2.connect(dbname=self.config.db_name, user=self.config.db_user,
                                      password=self.config.db_pass, host=self.config.db_host, port=self.config.db_port, application_name="braja_mqtt")
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.conn.cursor()
        self.cursor.execute(f"LISTEN {self.config.db_channel};")
        root_logger.info(f"Listening to channel '{self.config.db_channel}' for notifications...")

    def check(self):
        return self.conn is not None

    def listen(self):
        while not self.stop_event.is_set():
            self.conn.poll()
            while self.conn.notifies:
                notify = self.conn.notifies.pop(0)
                self.handle_notification(notify)
            time.sleep(1)  # Add a small sleep to avoid busy-waiting

    def handle_notification(self, notify):
        root_logger.info(f"Received notification: {notify.payload}")

        print(f"Received notification: {notify.payload}")
        data = self.read_data()
        self.notification_queue.put(data)

    def read_data(self):
        self.cursor.execute("SELECT * FROM pdam_station;")
        self.data = self.cursor.fetchall()
        return self.data_as_dict()

    def data_as_dict(self):
        columns = [desc[0] for desc in self.cursor.description]
        data_dict_list = [dict(zip(columns, row)) for row in self.data]
        return data_dict_list

    def run(self):
        self.connect()
        if self.check():
            self.listen()

    def stop(self):
        root_logger.error("Disconnect from DB")
        self.stop_event.set()
        if self.conn:
            self.conn.close()


class DBLogger:
    def __init__(self):
        self.config = SetupDB()
        self.conn = psycopg2.connect(dbname=self.config.db_name, user=self.config.db_user,
                                     password=self.config.db_pass, host=self.config.db_host, port=self.config.db_port)
        self.cursor = self.conn.cursor()

    def data_as_dict(self):
        columns = [desc[0] for desc in self.cursor.description]
        data_dict_list = [dict(zip(columns, row)) for row in self.data]
        return data_dict_list
        
    def get_time_from_message(self,message):
        try:
            message = message.split(",")
            message = message[0]
            local_datetime_str = message.strip()
            jakarta_tz = pytz.timezone('Asia/Jakarta')
            datetime_obj = datetime.strptime(local_datetime_str, '%Y/%m/%d %H:%M:%S')
            jakarta_time= jakarta_tz.localize(datetime_obj)
            return jakarta_time
        except :
            return None


    def log(self, message, topic):
        start = time.time()
        try:
            sql_get_node = "SELECT id FROM pdam_station WHERE topic=%s"
            self.cursor.execute(sql_get_node, (topic,))
            station = self.cursor.fetchone()

            message_time = self.get_time_from_message(message)
            
            if message_time is not None:
                status = message.split(',')[11][0]
                
                if status==1: #threshold
                    # create table is_Sent false to telegeramnotif table type threshold
                    pass
                if len(station)>0:
                    created_at = datetime.now()
                    created_at = pytz.timezone('Asia/Jakarta').localize(created_at)

                    insert_collect_message_query = """INSERT INTO pdam_raw_message (message, created_at,time, topic,status) 
                                                VALUES (%s, %s, %s,%s,%s)
                                                ON CONFLICT (id)
                                                DO UPDATE SET message = EXCLUDED.message"""
                    data = (message, created_at,message_time, topic, status)
                    root_logger.info(data)
                    self.cursor.execute(insert_collect_message_query, data)
                    self.conn.commit()
                    root_logger.info("saved to db "+str(time.time()-start))

            else:
                created_at = datetime.now()
                created_at = pytz.timezone('Asia/Jakarta').localize(created_at)
                status = -1
                insert_collect_message_query = """INSERT INTO pdam_raw_message (message, created_at,time, topic,status) 
                                            VALUES (%s, %s, %s,%s,%s)
                                            ON CONFLICT (id)
                                            DO UPDATE SET message = EXCLUDED.message"""
                data = (message, created_at,created_at, topic, status)
                root_logger.info(data)
                self.cursor.execute(insert_collect_message_query, data)
                self.conn.commit()

        except Exception as e:
            # print(f"Database error: {e}")
            root_logger.error("Database "+str(e))
            self.conn.rollback()  # Rollback the transaction on error


    def __del__(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()

        
class MQTTClient:
    def __init__(self):
        self.config = SetupMQTT()
        self.logger = DBLogger()
        self.broker_address = self.config.mqtt_broker
        self.broker_port = self.config.mqtt_port
        self.username = self.config.mqtt_userid
        self.password = self.config.mqtt_pass
        self.client = mqtt.Client()
        self.client.username_pw_set(self.username, self.password)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.topic =[]

        # Set the auto-reconnect settings
        self.client.reconnect_delay_set(min_delay=1, max_delay=240)

    def on_message(self, client, userdata, message):
        topic = str(message.topic)
        root_logger.info("")
        try:
            received_message = str(message.payload.decode())
            # print(received_message,topic)
            
            root_logger.info(f"Message received: {received_message} on topic {topic}")  
            self.logger.log(received_message,topic)
        except Exception as e:
            root_logger.error("error message "+str(topic)+" "+str(e))
            clean_message = ''.join(chr(byte) for byte in message.payload if byte < 128)
            received_message = clean_message
            root_logger.info(f"Message received: {received_message} on topic {topic}")  
            self.logger.log(received_message,topic)

    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            root_logger.error(f"Connection failed with code {rc}")
        else:
            root_logger.info("Connected to broker")

            if len(self.topic) >0:
                for topic in self.topic:
                    self.client.subscribe(topic)
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            root_logger.error("Unexpected disconnection. Reconnecting...")
            try:
                self.client.reconnect()
            except Exception as e:
                root_logger.error(f"Reconnection failed: {e}")
        else:
            root_logger.info("Disconnected from broker")

    def connect(self):
        self.client.connect(self.broker_address, self.broker_port)
        self.client.loop_start()

    def disconnect(self):
        root_logger.error("Disconnect from MQTT broker")
        self.client.loop_stop()
        self.client.disconnect()


def main(listener):
    listener.run()

if __name__ == "__main__":
    root_logger.info("------------")
    root_logger.info("SYSTEM RESTART")
    listener = PostgresListener()
    mqtt_client = MQTTClient()

    def signal_handler(sig, frame):
        root_logger.info("Received keyboard interrupt. Disconnecting...")
        listener.stop()
        mqtt_client.disconnect()
        root_logger.info("Disconnected from broker and stopped listener. Exiting.")
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:

        mqtt_client.connect()
        listener.connect()
        initial_data = listener.read_data()
        mqtt_client.topic=[]
        for ins in initial_data:
            topic = ins['topic']
            if topic:
                mqtt_client.topic.append(topic)
                mqtt_client.client.subscribe(topic)
                root_logger.info(f"Subscribing to initial topic: {topic}")

        t1 = threading.Thread(target=main, args=(listener,))
        t1.start()
        while True:
            try:
                data = listener.notification_queue.get(timeout=1)
                if data != initial_data:
                    mqtt_client.topic=[]
                    # Unsubscribe
                    for ins in initial_data:
                        topic = ins['topic']
                        if topic:
                            mqtt_client.client.unsubscribe(topic)
                            root_logger.info(f"Unsubscribed from topic: {topic}")
                            print(f"Unsubscribed from topic: {topic}")
                    # Subscribe new topic
                    for ins in data:
                        topic = ins['topic']
                        mqtt_client.topic.append(topic)
                        if topic:
                            mqtt_client.client.subscribe(topic)
                            root_logger.info(f"Subscribing to topic: {topic}")
                            print(f"Subscribing to topic: {topic}")
                    initial_data = data
                

            except queue.Empty:
                pass

    except Exception as e:
        root_logger.error(f"An error occurred: {e}")
        listener.stop()
        mqtt_client.disconnect()
        root_logger.info("Disconnected from broker and stopped listener due to error.")


'''
-- CREATE OR REPLACE FUNCTION notify_insert() RETURNS trigger AS $$
-- BEGIN
--     PERFORM pg_notify('channel_station', 'INSERT');
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE OR REPLACE FUNCTION notify_update() RETURNS trigger AS $$
-- BEGIN
--     PERFORM pg_notify('channel_station', 'UPDATE');
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE OR REPLACE FUNCTION notify_delete() RETURNS trigger AS $$
-- BEGIN
--     PERFORM pg_notify('channel_station', 'DELETE');
--     RETURN OLD;
-- END;
-- $$ LANGUAGE plpgsql;


CREATE TRIGGER insert_trigger_pdam_station
AFTER INSERT ON pdam_station
FOR EACH ROW
EXECUTE FUNCTION notify_insert();

CREATE TRIGGER update_trigger_pdam_station
AFTER UPDATE ON pdam_station
FOR EACH ROW
EXECUTE FUNCTION notify_update();

CREATE TRIGGER delete_trigger_pdam_station
AFTER DELETE ON pdam_station
FOR EACH ROW
EXECUTE FUNCTION notify_delete();





DROP TRIGGER IF EXISTS insert_trigger_dashboard_node ON dashboard_node;
DROP TRIGGER IF EXISTS update_trigger_dashboard_node ON dashboard_node;
DROP TRIGGER IF EXISTS delete_trigger_dashboard_node ON dashboard_node;
'''