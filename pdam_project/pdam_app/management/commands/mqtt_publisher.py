import paho.mqtt.client as mqtt
from configparser import ConfigParser

class SetupMQTT(object):
    def __init__(self):
        config = ConfigParser()
        config.read_file(open('config.ini'))
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


# Example usage:
if __name__ == "__main__":
    topic = "your/topic"
    message = "Your retained message"

    # Create an instance of the MQTTPublisher class
    mqtt_publisher = MQTTPublisher()

    # Connect to the broker
    mqtt_publisher.connect()

    # Publish a message
    mqtt_publisher.publish(topic, message)

    # Disconnect from the broker
    mqtt_publisher.disconnect()
