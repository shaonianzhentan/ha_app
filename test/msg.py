import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc):
    print(rc)
    client.subscribe('123/app')

def on_disconnect(client, userdata, rc):
    print(rc)

def on_subscribe(client, userdata, mid, granted_qos):
    print(granted_qos)

def on_message(client, userdata, msg):
    payload = str(msg.payload.decode('utf-8'))
    print(payload)

HOST = 'test.mosquitto.org'
PORT = 1883
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe
client.on_disconnect = on_disconnect
client.connect(HOST, PORT, 60)
client.loop_forever()