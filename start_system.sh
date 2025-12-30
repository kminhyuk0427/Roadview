# 시스템 통합 시작 스크립트

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# PID 파일 위치
PID_DIR="/tmp/deepstream_system"
mkdir -p "$PID_DIR"
MQTT_PID_FILE="$PID_DIR/mqtt_receiver.pid"
STREAM_PID_FILE="$PID_DIR/stream_server.pid"
DASHBOARD_PID_FILE="$PID_DIR/dashboard.pid"

# 정리 함수
cleanup() {
    echo ""
    echo "시스템 종료 중..."
    
    if [ -f "$DASHBOARD_PID_FILE" ]; then
        kill $(cat "$DASHBOARD_PID_FILE") 2>/dev/null
        rm -f "$DASHBOARD_PID_FILE"
    fi
    
    if [ -f "$STREAM_PID_FILE" ]; then
        kill $(cat "$STREAM_PID_FILE") 2>/dev/null
        rm -f "$STREAM_PID_FILE"
    fi
    
    if [ -f "$MQTT_PID_FILE" ]; then
        kill $(cat "$MQTT_PID_FILE") 2>/dev/null
        rm -f "$MQTT_PID_FILE"
    fi
    
    echo "종료 완료"
    exit 0
}

# Ctrl+C 트랩 설정
trap cleanup INT TERM

echo "시스템 시작 중..."
echo ""

# 1. MQTT Receiver 시작
python3 mqtt_receiver.py > /dev/null 2>&1 &
MQTT_PID=$!
sleep 2
if ! ps -p $MQTT_PID > /dev/null 2>&1; then
    echo "시스템 시작 실패"
    exit 1
fi
echo $MQTT_PID > "$MQTT_PID_FILE"
echo "[1/3] MQTT Receiver 시작 (PID: $MQTT_PID)"

# 2. RTSP Streaming Server 시작
python3 rtsp_stream_server.py > /dev/null 2>&1 &
STREAM_PID=$!
sleep 3
if ! ps -p $STREAM_PID > /dev/null 2>&1; then
    echo "시스템 시작 실패"
    cleanup
    exit 1
fi
echo $STREAM_PID > "$STREAM_PID_FILE"
echo "[2/3] Streaming Server 시작 (PID: $STREAM_PID) - http://localhost:5000"

# 3. Streamlit Dashboard 시작
streamlit run dashboard.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    > /dev/null 2>&1 &
DASHBOARD_PID=$!
sleep 3
if ! ps -p $DASHBOARD_PID > /dev/null 2>&1; then
    echo "시스템 시작 실패"
    cleanup
    exit 1
fi
echo $DASHBOARD_PID > "$DASHBOARD_PID_FILE"
echo "[3/3] Dashboard 시작 (PID: $DASHBOARD_PID) - http://localhost:8501"

echo ""
echo "시스템 시작 완료"
echo "Ctrl+C로 종료"
echo ""

# 무한 대기
while true; do
    sleep 3600
done