import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import time
import requests

current_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
sys.path.insert(0, str(current_dir))

try:
    from db_manager import DeepStreamDB
    DB_AVAILABLE = True
except ImportError as e:
    st.error(f"db_manager.py를 찾을 수 없음: {e}")
    DB_AVAILABLE = False

try:
    from config import RTSP_ENABLED, DB_PATH, VIDEO_DISPLAY_WIDTH, VIDEO_DISPLAY_HEIGHT

    CONFIG_AVAILABLE = True
    STREAM_SERVER_URL = getattr(
        sys.modules["config"], "STREAM_SERVER_URL", "http://localhost:5000"
    )
    STREAM_SERVER_ENABLED = getattr(
        sys.modules["config"], "STREAM_SERVER_ENABLED", True
    )
except ImportError:
    st.warning("config.py를 찾을 수 없음")
    CONFIG_AVAILABLE = False
    RTSP_ENABLED = False
    DB_PATH = "deepstream_analytics.db"
    VIDEO_DISPLAY_WIDTH = 800
    VIDEO_DISPLAY_HEIGHT = 450
    STREAM_SERVER_URL = "http://localhost:5000"
    STREAM_SERVER_ENABLED = True

st.set_page_config(
    page_title="Roadview Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 일림 경고 오류때문에 추가함
st.markdown(
    """
<style>
.alert-danger {
    animation: fadeSmooth 0.2s ease-in-out;
}

@keyframes fadeSmooth {
    from { opacity: 0; }
    to { opacity: 1; }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1f1f1f;
        padding: 10px 0;
        margin-bottom: 10px;
    }
    .stat-box-left {
        background-color: #4ECDC4;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-box-right {
        background-color: #FF6B35;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-label {
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .stat-number {
        font-size: 3rem;
        font-weight: bold;
    }
    .section-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 20px;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 2px solid #ecf0f1;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .rtsp-badge {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        margin-left: 10px;
    }
    .rtsp-badge-connected {
        background-color: #28a745;
        color: white;
    }
    .rtsp-badge-disconnected {
        background-color: #dc3545;
        color: white;
    }
    .alert-info {
        background-color: #d1ecf1;
        border-left: 4px solid #0c5460;
        padding: 12px;
        margin: 8px 0;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    .alert-warning {
        background-color: #fff3cd;
        border-left: 4px solid #856404;
        padding: 12px;
        margin: 8px 0;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    .alert-danger {
        background-color: #f8d7da;
        border-left: 4px solid #721c24;
        padding: 12px;
        margin: 8px 0;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    .stApp {
        background-color: #f8f9fa;
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .stat-card-header {
        font-size: 0.9rem;
        color: #6c757d;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .stat-card-value {
        font-size: 2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 5px;
    }
    .stat-card-label {
        font-size: 0.85rem;
        color: #6c757d;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #ecf0f1;
    }
    .metric-row:last-child {
        border-bottom: none;
    }
    .metric-label {
        font-weight: 600;
        color: #495057;
    }
    .metric-value {
        font-weight: bold;
        color: #2c3e50;
        font-size: 1.1rem;
    }
    .progress-bar {
        width: 100%;
        height: 8px;
        background-color: #e9ecef;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 5px;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #4ECDC4 0%, #44A08D 100%);
        transition: width 0.3s ease;
    }
    .rtsp-container {
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        background: #000;
        margin: 10px 0;
    }
    .rtsp-container img {
        display: block;
        width: 100%;
        height: auto;
        max-width: 100%;
        object-fit: contain;
    }
</style>
""", unsafe_allow_html=True)

# 스트리밍 서버 상태 확인
def check_stream_server():
    if not STREAM_SERVER_ENABLED:
        return False, "스트리밍 서버가 비활성화되어 있습니다"

    try:
        health_response = requests.get(f"{STREAM_SERVER_URL}/health", timeout=0.5)
        if health_response.status_code == 200:
            return True, "연결됨"
    except:
        pass

    try:
        response = requests.get(f"{STREAM_SERVER_URL}/status", timeout=1)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict):
                return True, "연결됨"
        return False, f"서버 응답 오류 ({response.status_code})"
    except:
        pass

    return False, "서버에 연결할 수 없습니다"

@st.cache_resource
def init_database():
    if not DB_AVAILABLE:
        return None, "db_manager.py 모듈을 찾을 수 없음"
    
    try:
        db = DeepStreamDB(DB_PATH)
        if not db.exists():
            return None, "DB 파일이 존재하지 않습니다"
        return db, None
    except Exception as e:
        return None, f"DB 연결 오류: {str(e)}"

# DeepStream 실행 상태 확인
def check_deepstream_status(db):
    if db is None:
        return False, "데이터베이스에 연결할 수 없습니다"
    
    try:
        latest = db.get_latest(1)
        if not latest or len(latest) == 0:
            return False, "수신된 데이터가 없습니다"
        
        timestamp_str = latest[0][1]
        try:
            if '.' in timestamp_str:
                last_time = datetime.strptime(timestamp_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            else:
                last_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
            
            time_diff = (datetime.now() - last_time).total_seconds()
            
            if time_diff > 30:
                return False, f"마지막 데이터 수신: {int(time_diff)}초 전"
            else:
                return True, f"정상 작동 중 (최근: {int(time_diff)}초 전)"
                
        except Exception as e:
            return False, f"타임스탬프 파싱 오류: {str(e)}"
            
    except Exception as e:
        return False, f"상태 확인 실패: {str(e)}"

# 사용 가능한 날짜 목록 조회
def get_available_dates(db):
    try:
        stats = db.get_statistics()
        if not stats or stats['total_count'] == 0:
            return []
        
        min_str = stats['time_range'][0]
        max_str = stats['time_range'][1]
        
        try:
            if "." in min_str:
                min_time = datetime.strptime(min_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            else:
                min_time = datetime.strptime(min_str, "%Y-%m-%dT%H:%M:%S")
        except:
            min_time = datetime.strptime(min_str[:19], "%Y-%m-%dT%H:%M:%S")

        try:
            if "." in max_str:
                max_time = datetime.strptime(max_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            else:
                max_time = datetime.strptime(max_str, "%Y-%m-%dT%H:%M:%S")
        except:
            max_time = datetime.strptime(max_str[:19], "%Y-%m-%dT%H:%M:%S")

        dates = []
        current = min_time.date()
        end = max_time.date()
        
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
        
        dates.reverse()
        return dates
    except Exception as e:
        print(f"날짜 조회 오류: {e}")
        return []

# 최신 통계 데이터 조회
def get_latest_stats(db):
    try:
        latest = db.get_latest(1)
        if latest and len(latest) > 0:
            row = latest[0]
            return {
                'timestamp': row[1],
                'car_total': row[2] or 0,
                'bicycle_total': row[3] or 0,
                'person_total': row[4] or 0,
                'lc1_entry': row[5] or 0,
                'lc1_exit': row[6] or 0,
                'lc2_entry': row[7] or 0,
                'lc2_exit': row[8] or 0,
                'roi_car': row[9] or 0,
                'roi_bicycle': row[10] or 0,
                'roi_person': row[11] or 0
            }
    except Exception as e:
        print(f"최신 통계 조회 오류: {e}")
    return None
# 역주행 감지
def check_wrong_direction(db):
    try:
        latest = db.get_latest(1)  # 최신 1개만 조회
        if not latest:
            return []

        row = latest[0]
        timestamp = row[1]

        lc1_exit = row[6] or 0
        lc2_exit = row[8] or 0

        # 세션 초기값 설정
        if "prev_lc1_exit" not in st.session_state:
            st.session_state.prev_lc1_exit = lc1_exit
        if "prev_lc2_exit" not in st.session_state:
            st.session_state.prev_lc2_exit = lc2_exit

        alerts = []

        # LC1 증가 감지
        if lc1_exit > st.session_state.prev_lc1_exit:
            increased = lc1_exit - st.session_state.prev_lc1_exit
            alerts.append(
                {
                    "lane": "LC1",
                    "lane_name": "좌측 차로",
                    "count": increased,
                    "timestamp": timestamp,
                }
            )

        # LC2 증가 감지
        if lc2_exit > st.session_state.prev_lc2_exit:
            increased = lc2_exit - st.session_state.prev_lc2_exit
            alerts.append(
                {
                    "lane": "LC2",
                    "lane_name": "우측 차로",
                    "count": increased,
                    "timestamp": timestamp,
                }
            )

        # 최신 값을 세션에 저장 (다음 비교 기준)
        st.session_state.prev_lc1_exit = lc1_exit
        st.session_state.prev_lc2_exit = lc2_exit

        return alerts[:5]
    except Exception as e:
        print(f"역주행 체크 오류: {e}")
        return []

# 시간대별 데이터 조회
def get_hourly_data(db, date_str, target_filter="전체"):
    try:
        # 날짜 범위 설정
        if date_str == "current":
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_str = today_start.strftime("%Y-%m-%dT%H:%M:%S")
            end_str = now.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            start_str = f"{date_str}T00:00:00"
            end_str = f"{date_str}T23:59:59"

        print(f"쿼리 범위: {start_str} ~ {end_str}")

        rows = db.get_time_range(start_str, end_str)

        if not rows or len(rows) == 0:
            print(f"데이터 없음: {date_str}")
            return None

        print(f"조회된 데이터 수: {len(rows)}")

        # 시간대별 데이터 수집
        hourly_data = {}

        for row in rows:
            timestamp_str = row[1]

            try:
                if "." in timestamp_str:
                    dt = datetime.strptime(
                        timestamp_str.split(".")[0], "%Y-%m-%dT%H:%M:%S"
                    )
                else:
                    dt = datetime.strptime(
                        timestamp_str.split(".")[0], "%Y-%m-%dT%H:%M:%S"
                    )
                    dt = dt + timedelta(hours=9)

                hour = dt.hour

                if hour not in hourly_data:
                    hourly_data[hour] = {
                        "first_car": row[9] or 0,
                        "last_car": row[9] or 0,
                        "first_bicycle": row[10] or 0,
                        "last_bicycle": row[10] or 0,
                        "first_person": row[11] or 0,
                        "last_person": row[11] or 0,
                    }
                else:
                    hourly_data[hour]["last_car"] = row[9] or 0
                    hourly_data[hour]["last_bicycle"] = row[10] or 0
                    hourly_data[hour]["last_person"] = row[11] or 0

            except Exception as e:
                print(f"Timestamp 파싱 오류: {timestamp_str}, {e}")
                continue

        # 0~23시 데이터 생성
        hours = list(range(24))
        car_data = []
        bicycle_data = []
        person_data = []

        for hour in hours:
            if hour in hourly_data:
                car_increase = max(
                    0, hourly_data[hour]["last_car"] - hourly_data[hour]["first_car"]
                )
                bicycle_increase = max(
                    0,
                    hourly_data[hour]["last_bicycle"]
                    - hourly_data[hour]["first_bicycle"],
                )
                person_increase = max(
                    0,
                    hourly_data[hour]["last_person"]
                    - hourly_data[hour]["first_person"],
                )

                car_data.append(car_increase)
                bicycle_data.append(bicycle_increase)
                person_data.append(person_increase)
            else:
                car_data.append(0)
                bicycle_data.append(0)
                person_data.append(0)

        # 필터링 적용
        if target_filter == "차량":
            bicycle_data = [0] * 24
            person_data = [0] * 24
        elif target_filter == "자전거":
            car_data = [0] * 24
            person_data = [0] * 24
        elif target_filter == "사람":
            car_data = [0] * 24
            bicycle_data = [0] * 24

        return hours, car_data, bicycle_data, person_data
        
    except Exception as e:
        print(f"시간대별 데이터 조회 오류: {e}")
        import traceback

        traceback.print_exc()
        return None

# DeepStream 재시작과 무관하게 하루 전체 누적 traffic 계산
def get_daily_lane_totals(db, date_str):
    if date_str == "current":
        today = datetime.now().strftime("%Y-%m-%d")
    else:
        today = date_str

    start = f"{today}T00:00:00"
    end = f"{today}T23:59:59"

    rows = db.get_time_range(start, end)
    if not rows:
        return 0, 0

    prev_lc1 = None
    prev_lc2 = None
    total_lc1 = 0
    total_lc2 = 0

    for r in rows:
        lc1 = r[5] or 0
        lc2 = r[7] or 0

        if prev_lc1 is not None:
            # 증가한 경우만 합산 (감소는 DeepStream 재시작으로 판단)
            if lc1 > prev_lc1:
                total_lc1 += lc1 - prev_lc1

        if prev_lc2 is not None:
            if lc2 > prev_lc2:
                total_lc2 += lc2 - prev_lc2

        # 이전 값 갱신
        prev_lc1 = lc1
        prev_lc2 = lc2

    return total_lc1, total_lc2


# 데이터베이스 초기화
db, error = init_database()

# DeepStream 상태 확인
deepstream_running, deepstream_msg = check_deepstream_status(db)

# 스트리밍 서버 상태 확인
stream_connected, stream_msg = check_stream_server()

# 사이드바 구성
with st.sidebar:
    st.markdown('<div class="main-header">Roadview Dashboard</div>', 
                unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("### 관제 기간 선택")
    
    if db is None:
        st.error(f"DB 연결 실패: {error}")
        period_mode = "현재"
        selected_date = "current"
    else:
        available_dates = get_available_dates(db)
        
        if available_dates:
            period_options = ["현재"] + [
                d.strftime("%Y-%m-%d") for d in available_dates
            ]
            period_mode = st.selectbox(
                "기간", period_options, index=0, label_visibility="collapsed"
            )

            if period_mode == "현재":
                selected_date = "current"
            else:
                selected_date = period_mode
        else:
            st.info("저장된 데이터가 없음")
            period_mode = "현재"
            selected_date = "current"

    st.markdown("### 관제 대상 선택")
    target_filter = st.selectbox(
        "대상",
        ["전체", "사람", "차량", "자전거"],
        label_visibility="collapsed"
    )
    
    st.markdown("### 알림")
    alert_container = st.container()
    
    with alert_container:
        alerts = []  # 모든 경고를 리스트에 쌓는다

        # DeepStream 경고
        if not deepstream_running:
            alerts.append(
                f"""
            <div class="alert-danger">
                <strong>!! DeepStream 상태</strong><br/>
                {deepstream_msg}<br/>
                DeepStream과 mqtt_receiver.py를 실행하세요.
            </div>
            """
            )

        # 스트리밍 서버 경고
        if not stream_connected and STREAM_SERVER_ENABLED:
            alerts.append(
                f"""
            <div class="alert-warning">
                <strong>!! 스트리밍 서버 연결 실패</strong><br/>
                {stream_msg}<br/>
                rtsp_stream_server.py가 실행 중인지 확인하세요.
            </div>
            """
            )
        
        # 역주행 경고
        if db:
            wrong_direction_alerts = check_wrong_direction(db)
            for alert in wrong_direction_alerts:
                try:
                    dt = datetime.strptime(
                        alert["timestamp"].split(".")[0], "%Y-%m-%dT%H:%M:%S"
                    )
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    formatted_time = alert["timestamp"]

                alerts.append(
                    f"""
                <div class="alert-danger">
                    <strong>!! 역주행 감지</strong><br/>
                    <strong>차로:</strong> {alert['lane']} ({alert['lane_name']})<br/>
                    <strong>감지 횟수:</strong> {alert['count']}회<br/>
                    <strong>감지 시각:</strong> {formatted_time}
                </div>
                """
                )

        # 리스트에 쌓인 alerts를 한 번에 출력
        for alert_html in alerts:
            st.markdown(alert_html, unsafe_allow_html=True)

# 최신 통계 조회
if db:
    stats = get_latest_stats(db)
    if stats:
        info = db.get_db_info()
    else:
        info = {'count': 0}
else:
    info = {'count': 0}

if not stats:
    stats = {
        'timestamp': datetime.now().isoformat(),
        'car_total': 0,
        'bicycle_total': 0,
        'person_total': 0,
        'lc1_entry': 0,
        'lc1_exit': 0,
        'lc2_entry': 0,
        'lc2_exit': 0,
        'roi_car': 0,
        'roi_bicycle': 0,
        'roi_person': 0
    }

# 메인 콘텐츠 영역
col_video, col_stats = st.columns([2, 1])

with col_video:
    if stream_connected:
        stream_status = (
            '<span class="rtsp-badge rtsp-badge-connected">스트림 연결됨</span>'
        )
    else:
        stream_status = '<span class="rtsp-badge rtsp-badge-disconnected">스트림 연결 안됨</span>'

    st.markdown(
        f'<div class="section-header"><span>실시간 영상</span>{stream_status}</div>',
        unsafe_allow_html=True,
    )

    if stream_connected and STREAM_SERVER_ENABLED:
        stream_url = f"{STREAM_SERVER_URL}/stream/main"

        st.markdown(
            f"""
        <div class="rtsp-container">
            <img src="{stream_url}" 
                 style="width: 100%; height: auto; display: block; max-width: 100%;"
                 alt="RTSP Live Stream" />
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 현재 시각 표시
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")
        st.caption(f"실시간 스트리밍 | {current_time}")
    else:
        st.image(
            "https://via.placeholder.com/800x450/2C3E50/FFFFFF?text=No+Video+Feed",
            use_column_width=True,
        )
        st.info("스트리밍 서버를 시작하려면: `python3 rtsp_stream_server.py`")

with col_stats:
    st.markdown(
        '<div class="section-header">현재 물체 분포 비율</div>', unsafe_allow_html=True
    )

    # 필터링 적용된 통계
    if target_filter == "전체":
        total = stats["car_total"] + stats["bicycle_total"] + stats["person_total"]
        if total > 0:
            car_pct = round(stats["car_total"] / total * 100, 1)
            bicycle_pct = round(stats["bicycle_total"] / total * 100, 1)
            person_pct = round(stats["person_total"] / total * 100, 1)
            values = [person_pct, car_pct, bicycle_pct]
        else:
            values = [0, 0, 0]
    elif target_filter == "차량":
        values = [0, 100, 0]
    elif target_filter == "자전거":
        values = [0, 0, 100]
    elif target_filter == "사람":
        values = [100, 0, 0]
    
    labels = ['사람', '차량', '자전거']
    colors = ['#FFA726', '#42A5F5', '#66BB6A']
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textfont=dict(size=14, color='white'),
        textposition='inside'
    )])
    
    fig_donut.update_layout(
        showlegend=False,
        height=250,
        margin=dict(t=10, b=10, l=10, r=10)
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div style="text-align:center"><span style="color:#FFA726;font-size:2rem;font-weight:bold">{values[0]}%</span><br>사람</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div style="text-align:center"><span style="color:#42A5F5;font-size:2rem;font-weight:bold">{values[1]}%</span><br>차량</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div style="text-align:center"><span style="color:#66BB6A;font-size:2rem;font-weight:bold">{values[2]}%</span><br>자전거</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">차로별 차량 통행량</div>', unsafe_allow_html=True)

    left_count, right_count = get_daily_lane_totals(db, selected_date)

    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown(f"""
        <div class="stat-box-left">
            <div class="stat-label">LEFT</div>
            <div class="stat-number">{left_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown(f"""
        <div class="stat-box-right">
            <div class="stat-label">RIGHT</div>
            <div class="stat-number">{right_count}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="section-header">관제 대상 시간대별 트래픽</div>', 
            unsafe_allow_html=True)

if db:
    hourly_result = get_hourly_data(db, selected_date, target_filter)

    if hourly_result:
        hours, car_data, bicycle_data, person_data = hourly_result
        
        hour_labels = [f"{h:02d}시" for h in hours]
        
        fig_traffic = go.Figure()

        # 필터링에 따라 그래프 표시
        if target_filter in ["전체", "차량"]:
            fig_traffic.add_trace(
                go.Scatter(
                    x=hour_labels,
                    y=car_data,
                    mode="lines+markers",
                    name="차량",
                    line=dict(color="#42A5F5", width=3),
                    marker=dict(size=6),
                )
            )

        if target_filter in ["전체", "자전거"]:
            fig_traffic.add_trace(
                go.Scatter(
                    x=hour_labels,
                    y=bicycle_data,
                    mode="lines+markers",
                    name="자전거",
                    line=dict(color="#66BB6A", width=3),
                    marker=dict(size=6),
                )
            )

        if target_filter in ["전체", "사람"]:
            fig_traffic.add_trace(
                go.Scatter(
                    x=hour_labels,
                    y=person_data,
                    mode="lines+markers",
                    name="사람",
                    line=dict(color="#FFA726", width=3),
                    marker=dict(size=6),
                )
            )

        fig_traffic.update_layout(
            height=350,
            xaxis_title="시간",
            yaxis_title="시간당 카운트",
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
            yaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        
        st.plotly_chart(fig_traffic, use_container_width=True)

        if selected_date != "current":
            st.info(f"선택된 날짜: {selected_date}")
        else:
            current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")
            st.info(f"현재 시각: {current_time} (실시간 데이터)")
    else:
        st.warning(f"!! 선택한 날짜({selected_date})의 데이터가 없음")
else:
    st.warning("데이터베이스 연결 팔요")

# 주요 통계
st.markdown('<div class="section-header">주요 통계 요약</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

total_traffic = left_count + right_count
total_objects = stats['car_total'] + stats['bicycle_total'] + stats['person_total']
total_violations = stats['lc1_exit'] + stats['lc2_exit']

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-card-header">탈것 통행량</div>
        <div class="stat-card-value">{total_traffic:,}</div>
        <div class="stat-card-label">LC1: {left_count:,} | LC2: {right_count:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-card-header">감지한 물체</div>
        <div class="stat-card-value">{total_objects:,}</div>
        <div class="stat-card-label">차량·자전거·사람 합계</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    violation_color = "#dc3545" if total_violations > 0 else "#28a745"
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-card-header">역주행 감지</div>
        <div class="stat-card-value" style="color: {violation_color}">{total_violations:,}</div>
        <div class="stat-card-label">{"위험 상황" if total_violations > 0 else "정상"}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-card-header">누적 데이터</div>
        <div class="stat-card-value">{info['count']:,}</div>
        <div class="stat-card-label">전체 데이터베이스</div>
    </div>
    """, unsafe_allow_html=True)

# 상세 통계
st.markdown('<div class="section-header">상세 분석</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["차로별 상세", "물체별 분석", "ROI 영역 분석"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 좌측 차로 (LC1)")
        lc1_total = stats['lc1_entry'] + stats['lc1_exit']
        lc1_normal_pct = (stats['lc1_entry'] / lc1_total * 100) if lc1_total > 0 else 0
        
        st.markdown(f"""
        <div class="metric-row">
            <span class="metric-label">정상 주행</span>
            <span class="metric-value" style="color: #28a745">{stats['lc1_entry']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">역주행 감지</span>
            <span class="metric-value" style="color: #dc3545">{stats['lc1_exit']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">이벤트 발생</span>
            <span class="metric-value">{lc1_total:,}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"**정상 통행률**: {lc1_normal_pct:.1f}%")
        st.markdown(f'<div class="progress-bar"><div class="progress-fill" style="width: {lc1_normal_pct}%; background: {"#28a745" if lc1_normal_pct > 95 else "#ffc107"}"></div></div>', 
                   unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 우측 차로 (LC2)")
        lc2_total = stats['lc2_entry'] + stats['lc2_exit']
        lc2_normal_pct = (stats['lc2_entry'] / lc2_total * 100) if lc2_total > 0 else 0
        
        st.markdown(f"""
        <div class="metric-row">
            <span class="metric-label">정상 주행</span>
            <span class="metric-value" style="color: #28a745">{stats['lc2_entry']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">역주행 감지</span>
            <span class="metric-value" style="color: #dc3545">{stats['lc2_exit']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">이벤트 발생</span>
            <span class="metric-value">{lc2_total:,}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"**정상 통행률**: {lc2_normal_pct:.1f}%")
        st.markdown(f'<div class="progress-bar"><div class="progress-fill" style="width: {lc2_normal_pct}%; background: {"#28a745" if lc2_normal_pct > 95 else "#ffc107"}"></div></div>', 
                   unsafe_allow_html=True)

with tab2:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 차량")
        car_pct = (stats['car_total'] / total_objects * 100) if total_objects > 0 else 0
        st.markdown(f"""
        <div class="stat-card-value" style="color: #42A5F5">{stats['car_total']:,}</div>
        <div class="metric-row">
            <span class="metric-label">전체 대비</span>
            <span class="metric-value">{car_pct:.1f}%</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 자전거")
        bicycle_pct = (stats['bicycle_total'] / total_objects * 100) if total_objects > 0 else 0
        st.markdown(f"""
        <div class="stat-card-value" style="color: #66BB6A">{stats['bicycle_total']:,}</div>
        <div class="metric-row">
            <span class="metric-label">전체 대비</span>
            <span class="metric-value">{bicycle_pct:.1f}%</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("#### 사람")
        person_pct = (stats['person_total'] / total_objects * 100) if total_objects > 0 else 0
        st.markdown(f"""
        <div class="stat-card-value" style="color: #FFA726">{stats['person_total']:,}</div>
        <div class="metric-row">
            <span class="metric-label">전체 대비</span>
            <span class="metric-value">{person_pct:.1f}%</span>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.markdown("#### ROI 영역 누적 카운트")
    
    roi_total = stats['roi_car'] + stats['roi_bicycle'] + stats['roi_person']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("차량", f"{stats['roi_car']:,}", 
                 delta=f"{(stats['roi_car']/roi_total*100):.1f}%" if roi_total > 0 else "0%")
    
    with col2:
        st.metric("자전거", f"{stats['roi_bicycle']:,}",
                 delta=f"{(stats['roi_bicycle']/roi_total*100):.1f}%" if roi_total > 0 else "0%")
    
    with col3:
        st.metric("사람", f"{stats['roi_person']:,}",
                 delta=f"{(stats['roi_person']/roi_total*100):.1f}%" if roi_total > 0 else "0%")
    
    with col4:
        st.metric("총합", f"{roi_total:,}", delta="누적")
    
    st.markdown("---")
    
    st.markdown(f"""
    <div class="metric-row">
        <span class="metric-label">ROI 영역 분석 시작 시각</span>
        <span class="metric-value">{stats['timestamp'][:19]}</span>
    </div>
    """, unsafe_allow_html=True)

# 자동 새로고침
time.sleep(1)
st.rerun()