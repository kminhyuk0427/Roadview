# config.py
# RTSP 카메라 및 시스템 설정

RTSP_ENABLED = True
RTSP_URL = "RTSP_address"

# 다중 카메라 설정
RTSP_CAMERAS = [
    {
        "name": "Camera 1",
        "url": "RTSP_address",
        "location": "Main Entrance"
    }
]

# RTSP 스트림 성능 설정
RTSP_RECONNECT_INTERVAL = 5  # 재연결 시도 간격 초
RTSP_FRAME_SKIP = 1  # N 프레임마다 1개 읽기, 숫자가 클수록 CPU 부하 감소 (1=실시간, 3=균형)
RTSP_TIMEOUT = 10  # 연결 타임아웃 초
RTSP_BUFFER_SIZE = 1  # 버퍼 크기, 1이 가장 낮은 지연
RTSP_MAX_RECONNECT_ATTEMPTS = 5  # 최대 재연결 시도 횟수

# MQTT 브로커 설정
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "deepstream/count"

# 데이터베이스 설정
DB_PATH = "deepstream_analytics.db"

# 대시보드 설정
DASHBOARD_REFRESH_INTERVAL = 1.0  # 대시보드 새로고침 간격 초
VIDEO_DISPLAY_WIDTH = 800  # 영상 표시 너비
VIDEO_DISPLAY_HEIGHT = 450  # 영상 표시 높이

# 프레임 저장 설정
SAVE_FRAMES = False
FRAME_SAVE_DIR = "./deepstream_frames"
FRAME_SAVE_INTERVAL = 30  # 몇 프레임마다 저장할지