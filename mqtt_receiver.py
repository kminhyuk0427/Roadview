# 데이터 수신
# python3 mqtt_receiver.py

import paho.mqtt.client as mqtt
from datetime import datetime
from db_manager import DeepStreamDB
from data_parser import parse_deepstream_json, format_data_summary

# MQTT 설정
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "deepstream/count"

# DB 초기화
db = DeepStreamDB("deepstream_analytics.db")

print("="*70)
print("  mqtt 수신 후 저장 클라이언트")
print("="*70)

# 통계 출력
def print_statistics():
    try:
        stats = db.get_statistics()
        if not stats:
            print("\n   아직 데이터가 없습니다")
            return
        
        print("\n" + "-"*70)
        print(f"   DB 통계: 총 {stats['total_count']:,}개 데이터")
        print(f"   기간: {stats['time_range'][0]} ~ {stats['time_range'][1]}")
        
        max_vals = stats['max_values']
        print(f"   누적 최대: Car={max_vals[0]}, Bicycle={max_vals[1]}, Person={max_vals[2]}")
        print(f"   LC1: Entry={max_vals[3]}, Exit={max_vals[4]}")
        print(f"   LC2: Entry={max_vals[5]}, Exit={max_vals[6]}")
        print(f"   ROI: Car={max_vals[7]}, Bicycle={max_vals[8]}, Person={max_vals[9]}")
        print("-"*70)
    
    except Exception as e:
        print(f"   통계 조회 오류: {e}")

# 연결 성공 콜백
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"\n  MQTT 브로커 연결 성공")
        print(f"  주소: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"  토픽: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
        print(f"\n  메시지 수신 및 DB 저장 대기 중...\n")
    else:
        print(f"  연결 실패 (코드: {rc})")

# 메시지 수신 콜백
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        
        # JSON 파싱
        timestamp, data = parse_deepstream_json(payload)
        
        if timestamp and data:
            # DB 저장
            record_id = db.insert_data(timestamp, data, payload)
            
            if record_id:
                # 터미널 출력
                print("\n" + "="*70)
                print(f"    메시지 수신 /저장 [DB ID: {record_id}]")
                print(f"  시각: {timestamp}")
                print("-"*70)
                print(format_data_summary(data))
                print("="*70)
                
                # 주기적 통계 출력 (10개마다)
                if record_id % 10 == 0:
                    print_statistics()
            else:
                print(f"  DB 저장 실패")
                print(f"  데이터: {data}")
        else:
            print(f"  JSON 파싱 실패")
            print(f"  받은 메시지: {payload[:100]}...")
    
    except Exception as e:
        print(f"  메시지 처리 오류: {e}")
        import traceback
        traceback.print_exc()

# 연결 끊김 콜백
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"\n  연결 끊김 (코드: {rc}). 재연결 시도 중...")

# 메인 실행
def main():
    try:
        # DB 초기화
        if not db.exists():
            print("  DB 생성 중...")
            db.init_database()
        else:
            print(f"  기존 DB 사용: {db.db_path}")
            info = db.get_db_info()
            print(f"  현재 데이터: {info['count']:,}개\n")
        
        # MQTT 클라이언트 설정
        client = mqtt.Client(client_id="DeepStreamReceiver")
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        
        print(f"  브로커 연결 시도 중...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n  사용자가 종료했습니다")
        print_statistics()
        client.disconnect()
        
    except Exception as e:
        print(f"\n  오류 발생: {e}")

if __name__ == "__main__":
    main()