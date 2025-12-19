# 실행: python3 mqtt_receiver.py

import paho.mqtt.client as mqtt
from datetime import datetime

# MQTT 설정
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "deepstream/count"

print("="*70)

# 연결 성공
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"   -연결 됨")
        print(f"   주소: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"   토픽: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
        print(f"\n   메시지 수신 대기 중...\n")
    else:
        print(f"   -연결 실패 (코드: {rc})")

# 메시지 수신 콜백
def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    payload = msg.payload.decode('utf-8')
    
    print("\n" + "="*70)
    print(f"   -메시지 수신 [{timestamp}]")
    print("-"*70)
    print(f"토픽: {msg.topic}")
    print(f"내용:\n{payload}")
    print("="*70 + "\n")

# 연결 끊김 콜백
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"    연결 끊김 (코드: {rc}) 재연결 시도 중...")

# 메인 실행
def main():
    client = mqtt.Client(client_id="PythonReceiver")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        print(f"   브로커 연결 시도 중...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n   종료 함")
        client.disconnect()
    except Exception as e:
        print(f"\n   오류 발생: {e}")

if __name__ == "__main__":
    main()