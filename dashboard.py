import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import threading
import time

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

current_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
sys.path.insert(0, str(current_dir))

try:
    from db_manager import DeepStreamDB
    DB_AVAILABLE = True
except ImportError as e:
    st.error(f"db_manager.py를 찾을 수 없음: {e}")
    DB_AVAILABLE = False

try:
    from config import (
        RTSP_ENABLED, RTSP_URL, RTSP_RECONNECT_INTERVAL,
        RTSP_FRAME_SKIP, RTSP_TIMEOUT, DB_PATH,
        FRAME_SAVE_DIR, VIDEO_DISPLAY_WIDTH, VIDEO_DISPLAY_HEIGHT
    )
    CONFIG_AVAILABLE = True
except ImportError:
    st.warning("config.py를 찾을 수 없음")
    CONFIG_AVAILABLE = False
    RTSP_ENABLED = False
    RTSP_URL = "RTSP_address"
    DB_PATH = "deepstream_analytics.db"
    FRAME_SAVE_DIR = "./deepstream_frames"
    VIDEO_DISPLAY_WIDTH = 800
    VIDEO_DISPLAY_HEIGHT = 450

st.set_page_config(
    page_title="Roadview Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
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
    div[data-testid="stImage"] {
        transition: none !important;
        animation: none !important;
    }
    div[data-testid="stImage"] > img {
        transition: none !important;
        animation: none !important;
    }
    .element-container {
        transition: none !important;
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
</style>
""", unsafe_allow_html=True)


#RTSP 스트림을 백그라운드에서 읽고 최신 프레임을 저장
class RTSPStreamReader:
    def __init__(self, rtsp_url, frame_skip=1, target_width=800, target_height=450):
        self.rtsp_url = rtsp_url
        self.frame_skip = frame_skip
        self.target_width = target_width
        self.target_height = target_height
        self.current_frame = None
        self.is_connected = False
        self.is_running = False
        self.frame_count = 0
        self.cap = None
        self.lock = threading.Lock()
        self.thread = None
        self.last_update = time.time()
        self.connection_attempts = 0
        self.max_connection_attempts = 5

    # RTSP 연결 시도
    def connect(self):
        
        try:
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.3)
            
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
            
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    resized_frame = cv2.resize(frame, (self.target_width, self.target_height), 
                                              interpolation=cv2.INTER_AREA)
                    
                    self.is_connected = True
                    self.connection_attempts = 0
                    with self.lock:
                        self.current_frame = resized_frame.copy()
                        self.last_update = time.time()
                    print(f"RTSP 연결 성공: {self.rtsp_url}")
                    return True
            
            self.is_connected = False
            self.connection_attempts += 1
            return False
                
        except Exception as e:
            print(f"RTSP 연결 오류: {e}")
            self.is_connected = False
            self.connection_attempts += 1
            return False
     # 백그라운드 스레드에서 지속적으로 프레임 읽기
    def _read_loop(self):
        reconnect_interval = 5
        last_reconnect = time.time()
        frame_skip_counter = 0
        
        while self.is_running:
            if not self.is_connected:
                if self.connection_attempts >= self.max_connection_attempts:
                    time.sleep(10)
                    self.connection_attempts = 0
                
                if time.time() - last_reconnect > reconnect_interval:
                    self.connect()
                    last_reconnect = time.time()
                time.sleep(1)
                continue
            
            try:
                if frame_skip_counter < self.frame_skip:
                    self.cap.grab()
                    frame_skip_counter += 1
                    continue
                
                frame_skip_counter = 0
                
                buffer_size = int(self.cap.get(cv2.CAP_PROP_BUFFERSIZE))
                for _ in range(buffer_size):
                    self.cap.grab()
                
                ret, frame = self.cap.retrieve()
                
                if ret and frame is not None:
                    resized_frame = cv2.resize(frame, (self.target_width, self.target_height),
                                              interpolation=cv2.INTER_AREA)
                    
                    with self.lock:
                        self.current_frame = resized_frame.copy()
                        self.last_update = time.time()
                    self.frame_count += 1
                else:
                    if time.time() - self.last_update > 10:
                        self.is_connected = False
                
                time.sleep(0.02)
                
            except Exception as e:
                print(f"프레임 읽기 오류: {e}")
                self.is_connected = False
                time.sleep(1)
    # 백그라운드 스레드 시작
    def start(self):
        
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        
        max_init_attempts = 3
        for attempt in range(max_init_attempts):
            if self.connect():
                break
            if attempt < max_init_attempts - 1:
                time.sleep(2)
    
    def get_current_frame(self):
        """현재 프레임 반환"""
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy(), self.last_update
            return None, 0

# 백그라운드 스레드 중지
    def stop(self):
        self.is_running = False
        if self.thread is not None:
            self.thread.join(timeout=3)
        if self.cap is not None:
            self.cap.release()
        self.is_connected = False

@st.cache_resource
def get_rtsp_reader():
    if not RTSP_ENABLED or not CV2_AVAILABLE:
        return None
    
    reader = RTSPStreamReader(RTSP_URL, frame_skip=RTSP_FRAME_SKIP,
                             target_width=VIDEO_DISPLAY_WIDTH,
                             target_height=VIDEO_DISPLAY_HEIGHT)
    reader.start()
    return reader

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
                return True, "정상 작동 중"
                
        except Exception as e:
            return False, "데이터 형식 오류"
            
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
            min_time = datetime.strptime(min_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
        except:
            min_time = datetime.strptime(min_str, '%Y-%m-%dT%H:%M:%S')
        
        try:
            max_time = datetime.strptime(max_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
        except:
            max_time = datetime.strptime(max_str, '%Y-%m-%dT%H:%M:%S')
        
        dates = []
        current = min_time.date()
        end = max_time.date()
        
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
        
        return dates
    except Exception as e:
        return []

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
        pass
    return None
# 역주행 감지
def check_wrong_direction(db):
    try:
        latest_rows = db.get_latest(10)
        if len(latest_rows) < 2:
            return []
        
        alerts = []
        
        for row in latest_rows:
            lc1_exit = row[6] or 0
            lc2_exit = row[8] or 0
            timestamp = row[1]
            
            if lc1_exit > 0:
                if not any(alert['timestamp'] == timestamp and alert['lane'] == 'LC1' for alert in alerts):
                    alerts.append({
                        'type': 'wrong_direction',
                        'lane': 'LC1',
                        'lane_name': '좌측 차로',
                        'count': lc1_exit,
                        'timestamp': timestamp
                    })
            
            if lc2_exit > 0:
                if not any(alert['timestamp'] == timestamp and alert['lane'] == 'LC2' for alert in alerts):
                    alerts.append({
                        'type': 'wrong_direction',
                        'lane': 'LC2',
                        'lane_name': '우측 차로',
                        'count': lc2_exit,
                        'timestamp': timestamp
                    })
        
        return alerts[:5]
    except Exception as e:
        return []

def get_hourly_roi_data(db, date_str):
    try:
        if date_str == "current":
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_str = today_start.strftime('%Y-%m-%dT%H:%M:%S')
            end_str = now.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            start_str = f"{date_str} 00:00:00"
            end_str = f"{date_str} 23:59:59"
        
        rows = db.get_time_range(start_str, end_str)
        
        if not rows:
            return None
        
        hourly_dict = {}
        for row in rows:
            timestamp_str = row[1]
            try:
                if '.' in timestamp_str:
                    dt = datetime.strptime(timestamp_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                else:
                    dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                
                from datetime import timezone, timedelta
                dt = dt.replace(tzinfo=timezone.utc)
                dt_kst = dt.astimezone(timezone(timedelta(hours=9)))
                
                hour = dt_kst.hour
                
            except Exception as e:
                continue
            
            if hour not in hourly_dict:
                hourly_dict[hour] = {
                    'roi_car': [],
                    'roi_bicycle': [],
                    'roi_person': []
                }
            
            hourly_dict[hour]['roi_car'].append(row[9] or 0)
            hourly_dict[hour]['roi_bicycle'].append(row[10] or 0)
            hourly_dict[hour]['roi_person'].append(row[11] or 0)
        
        hours = list(range(24))
        car_data = []
        bicycle_data = []
        person_data = []
        
        for hour in hours:
            if hour in hourly_dict:
                car_data.append(max(hourly_dict[hour]['roi_car']))
                bicycle_data.append(max(hourly_dict[hour]['roi_bicycle']))
                person_data.append(max(hourly_dict[hour]['roi_person']))
            else:
                car_data.append(0)
                bicycle_data.append(0)
                person_data.append(0)
        
        return hours, car_data, bicycle_data, person_data
        
    except Exception as e:
        return None

# 세션 상태 초기화
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()
if 'auto_refresh_enabled' not in st.session_state:
    st.session_state.auto_refresh_enabled = True

# 데이터베이스 초기화
db, error = init_database()

# DeepStream 상태 확인
deepstream_running, deepstream_msg = check_deepstream_status(db)

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
            period_options = ["현재"] + [d.strftime('%Y.%m.%d') for d in available_dates]
            period_mode = st.selectbox("기간", period_options, index=0, label_visibility="collapsed")
            
            if period_mode == "현재":
                selected_date = "current"
            else:
                selected_date = datetime.strptime(period_mode, '%Y.%m.%d').strftime('%Y-%m-%d')
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
        if not deepstream_running:
            st.markdown(f"""
            <div class="alert-danger">
                <strong>DeepStream 미실행</strong><br/>
                {deepstream_msg}<br/>
                DeepStream과 mqtt_receiver.py를 실행하세요.
            </div>
            """, unsafe_allow_html=True)
        
        if db:
            wrong_direction_alerts = check_wrong_direction(db)
            
            if wrong_direction_alerts:
                for alert in wrong_direction_alerts:
                    try:
                        dt = datetime.strptime(alert['timestamp'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_time = alert['timestamp']
                    
                    st.markdown(f"""
                    <div class="alert-danger">
                        <strong>역주행 감지</strong><br/>
                        <strong>차로:</strong> {alert['lane']} ({alert['lane_name']})<br/>
                        <strong>감지 횟수:</strong> {alert['count']}회<br/>
                        <strong>감지 시각:</strong> {formatted_time}
                    </div>
                    """, unsafe_allow_html=True)
            elif deepstream_running:
                st.markdown("""
                <div class="alert-info">
                    <strong>정상:</strong> 시스템이 정상 작동 중입니다.
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert-warning">
                <strong>경고:</strong> DB 연결 안됨
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    auto_refresh = st.checkbox("자동 새로고침", value=st.session_state.auto_refresh_enabled)
    st.session_state.auto_refresh_enabled = auto_refresh
    
    if auto_refresh:
        refresh_interval = st.slider("새로고침 간격 (초)", 0.5, 5.0, 1.0, 0.5)
    
    if st.button("지금 새로고침", use_container_width=True):
        st.session_state.last_refresh = time.time()
        st.rerun()

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
    # RTSP 상태 배지
    if RTSP_ENABLED and CV2_AVAILABLE:
        reader = get_rtsp_reader()
        if reader and reader.is_connected:
            rtsp_status = '<span class="rtsp-badge rtsp-badge-connected">RTSP 연결됨</span>'
        else:
            rtsp_status = '<span class="rtsp-badge rtsp-badge-disconnected">RTSP 연결 안됨</span>'
    else:
        rtsp_status = '<span class="rtsp-badge rtsp-badge-disconnected">RTSP 비활성화</span>'
    
    st.markdown(f'<div class="section-header"><span>실시간 영상</span>{rtsp_status}</div>', 
                unsafe_allow_html=True)
    
    # 영상을 위한 컨테이너
    video_placeholder = st.empty()
    
    if RTSP_ENABLED and CV2_AVAILABLE:
        reader = get_rtsp_reader()
        
        if reader:
            frame, frame_time = reader.get_current_frame()
            
            if frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp_str = datetime.fromtimestamp(frame_time).strftime('%Y년 %m월 %d일 %H:%M:%S')
                
                # placeholder를 사용하여 이미지 업데이트
                video_placeholder.image(
                    frame_rgb,
                    use_container_width=True,
                    caption=f"RTSP 실시간 스트림 - {timestamp_str}"
                )
            else:
                if reader.is_connected:
                    video_placeholder.info("프레임 로딩 중...")
                else:
                    video_placeholder.error("RTSP 연결 실패")
                    video_placeholder.info("재연결 시도 중...")
        else:
            video_placeholder.error("RTSP 리더 초기화 실패")
    else:
        video_placeholder.image("https://via.placeholder.com/800x450/2C3E50/FFFFFF?text=No+Video+Feed", 
                use_container_width=True)
        st.info("RTSP를 사용하려면 config.py에서 RTSP_ENABLED = True 설정")

with col_stats:
    st.markdown('<div class="section-header">물체 분포 비율</div>', unsafe_allow_html=True)
    
    total = stats['car_total'] + stats['bicycle_total'] + stats['person_total']
    
    if total > 0:
        car_pct = round(stats['car_total'] / total * 100, 1)
        bicycle_pct = round(stats['bicycle_total'] / total * 100, 1)
        person_pct = round(stats['person_total'] / total * 100, 1)
        values = [person_pct, car_pct, bicycle_pct]
    else:
        values = [0, 0, 0]
    
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
    
    left_count = stats['lc1_entry']
    right_count = stats['lc2_entry']
    
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

st.markdown('<div class="section-header">관제 대상 시간대별 트래픽 (ROI 누적)</div>', 
            unsafe_allow_html=True)

if db:
    hourly_result = get_hourly_roi_data(db, selected_date)

    if hourly_result:
        hours, car_data, bicycle_data, person_data = hourly_result
        
        hour_labels = [f"{h:02d}시" for h in hours]
        
        fig_traffic = go.Figure()
        
        fig_traffic.add_trace(go.Scatter(
            x=hour_labels,
            y=car_data,
            mode='lines+markers',
            name='차량',
            line=dict(color='#42A5F5', width=3),
            marker=dict(size=6)
        ))
        
        fig_traffic.add_trace(go.Scatter(
            x=hour_labels,
            y=bicycle_data,
            mode='lines+markers',
            name='자전거',
            line=dict(color='#66BB6A', width=3),
            marker=dict(size=6)
        ))
        
        fig_traffic.add_trace(go.Scatter(
            x=hour_labels,
            y=person_data,
            mode='lines+markers',
            name='사람',
            line=dict(color='#FFA726', width=3),
            marker=dict(size=6)
        ))
        
        fig_traffic.update_layout(
            height=350,
            xaxis_title="시간",
            yaxis_title="누적 카운트",
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
    else:
        st.info("선택한 날짜의 데이터가 없습니다.")
else:
    st.warning("데이터베이스 연결이 필요합니다.")

# 주요 통계
st.markdown('<div class="section-header">주요 통계 요약</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

total_traffic = left_count + right_count
total_objects = stats['car_total'] + stats['bicycle_total'] + stats['person_total']
total_violations = stats['lc1_exit'] + stats['lc2_exit']

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-card-header">총 차량 통행량</div>
        <div class="stat-card-value">{total_traffic:,}</div>
        <div class="stat-card-label">LC1: {left_count:,} | LC2: {right_count:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-card-header">총 감지 물체</div>
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
        <div class="stat-card-header">누적 레코드</div>
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
            <span class="metric-label">정상 진입</span>
            <span class="metric-value" style="color: #28a745">{stats['lc1_entry']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">역주행 감지</span>
            <span class="metric-value" style="color: #dc3545">{stats['lc1_exit']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">총 이벤트</span>
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
            <span class="metric-label">정상 진입</span>
            <span class="metric-value" style="color: #28a745">{stats['lc2_entry']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">역주행 감지</span>
            <span class="metric-value" style="color: #dc3545">{stats['lc2_exit']:,}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">총 이벤트</span>
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

# 자동 새로고침 로직
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()