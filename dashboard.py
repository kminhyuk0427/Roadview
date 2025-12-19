# streamlit run dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

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
        border-bottom: 3px solid #FF6B35;
    }
    .stat-box-in {
        background-color: #FF6B35;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-box-out {
        background-color: #4ECDC4;
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
    .lc-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.9rem;
        margin-left: 10px;
    }
    .lc-badge-all {
        background-color: #95a5a6;
        color: white;
    }
    .lc-badge-lc1 {
        background-color: #3498db;
        color: white;
    }
    .lc-badge-lc2 {
        background-color: #9b59b6;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_database():
    if not DB_AVAILABLE:
        return None, "db_manager.py 모듈을 찾을 수 없음"
    
    try:
        db = DeepStreamDB("deepstream_analytics.db")
        if not db.exists():
            return None, "DB 파일이 존재하지 않습니다"
        return db, None
    except Exception as e:
        return None, f"DB 연결 오류: {str(e)}"

def get_latest_deepstream_frame(output_dir="./deepstream_frames"):
    if not os.path.exists(output_dir):
        return None
    
    try:
        files = sorted(Path(output_dir).glob("*.jpg"), key=os.path.getmtime, reverse=True)
        if files:
            return str(files[0])
    except Exception as e:
        print(f"프레임 로드 오류: {e}")
    return None

def get_available_dates(db):
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
        st.error(f"통계 조회 오류: {e}")
    return None

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
                dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f')
            except:
                try:
                    dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                except Exception as e:
                    continue
            
            hour = dt.hour
            
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
        st.error(f"시간별 데이터 조회 오류: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

db, error = init_database()

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
    
    st.markdown("---")
    
    st.markdown("### 라인크로싱 선택")
    lc_selection = st.radio(
        "표시할 라인",
        ["전체 (LC1 + LC2)", "LC1만", "LC2만"],
        index=0,
        label_visibility="collapsed"
    )
    
    if lc_selection == "LC1만":
        lc_filter = "lc1"
        lc_display = "LC1"
        lc_badge_class = "lc-badge-lc1"
    elif lc_selection == "LC2만":
        lc_filter = "lc2"
        lc_display = "LC2"
        lc_badge_class = "lc-badge-lc2"
    else:
        lc_filter = "all"
        lc_display = "전체"
        lc_badge_class = "lc-badge-all"
    
    st.markdown("---")
    
    st.markdown("### 관제 대상 선택")
    target_filter = st.selectbox(
        "대상",
        ["전체", "사람", "차량", "자전거"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    st.markdown("### 알림")
    alert_container = st.container()
    
    with alert_container:
        st.markdown("""
        <div class="alert-info">
            <strong>정상:</strong> 시스템이 정상 작동 중입니다.
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    auto_refresh = st.checkbox("자동 새로고침", value=False)
    if auto_refresh:
        st.info("1초마다 자동 새로고침")

if db is None:
    st.error("데이터베이스에 연결할 수 없음. mqtt_receiver.py를 실행하세요.")
    st.stop()

info = db.get_db_info()
if info['count'] == 0:
    st.warning("저장된 데이터가 없음. DeepStream과 mqtt_receiver.py가 실행 중인지 확인하세요.")
    st.stop()

stats = get_latest_stats(db)

if not stats:
    st.error("데이터를 불러올 수 없음.")
    st.stop()

col_video, col_stats = st.columns([2, 1])

with col_video:
    st.markdown('<div class="section-header">실시간 영상</div>', unsafe_allow_html=True)
    
    video_container = st.container()
    with video_container:
        frame_path = get_latest_deepstream_frame()
        
        if frame_path and os.path.exists(frame_path):
            st.image(frame_path, use_container_width=True, caption="DeepStream 실시간 분석")
        else:
            st.image("https://via.placeholder.com/800x450/2C3E50/FFFFFF?text=DeepStream+Video+Feed", 
                    use_container_width=True)
            st.info("DeepStream에서 프레임을 ./deepstream_frames/ 디렉토리에 저장하도록 설정하세요")
    
    timestamp_str = datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')
    st.caption(f"촬영 시각: {timestamp_str}")

with col_stats:
    st.markdown('<div class="section-header">이동 분포 비율</div>', unsafe_allow_html=True)
    
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
    
    st.markdown(f'<div class="section-header">관제 대상 IN&OUT <span class="{lc_badge_class} lc-badge">{lc_display}</span></div>', 
                unsafe_allow_html=True)
    
    if lc_filter == "lc1":
        total_in = stats['lc1_entry']
        total_out = stats['lc1_exit']
    elif lc_filter == "lc2":
        total_in = stats['lc2_entry']
        total_out = stats['lc2_exit']
    else:
        total_in = stats['lc1_entry'] + stats['lc2_entry']
        total_out = stats['lc1_exit'] + stats['lc2_exit']
    
    col_in, col_out = st.columns(2)
    
    with col_in:
        st.markdown(f"""
        <div class="stat-box-in">
            <div class="stat-label">IN</div>
            <div class="stat-number">{total_in}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_out:
        st.markdown(f"""
        <div class="stat-box-out">
            <div class="stat-label">OUT</div>
            <div class="stat-number">{total_out}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="section-header">관제 대상 시간대별 트래픽 (ROI 누적)</div>', 
            unsafe_allow_html=True)

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
    st.info("선택한 날짜의 데이터가 없음.")

st.markdown('<div class="section-header">주요 통계</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="총 진입", value=f"{total_in:,}", delta=None)
with col2:
    st.metric(label="총 진출", value=f"{total_out:,}", delta=None)
with col3:
    current_stay = max(0, total_in - total_out)
    st.metric(label="현재 체류", value=f"{current_stay:,}", delta=None)
with col4:
    st.metric(label="총 레코드", value=f"{info['count']:,}", delta=None)

st.markdown('<div class="section-header">상세 통계</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("**라인크로싱 1 (LC1)**")
    st.write(f"진입: {stats['lc1_entry']:,}")
    st.write(f"진출: {stats['lc1_exit']:,}")
    st.write(f"합계: {stats['lc1_entry'] + stats['lc1_exit']:,}")

with col2:
    st.markdown("**라인크로싱 2 (LC2)**")
    st.write(f"진입: {stats['lc2_entry']:,}")
    st.write(f"진출: {stats['lc2_exit']:,}")
    st.write(f"합계: {stats['lc2_entry'] + stats['lc2_exit']:,}")

st.markdown("**ROI 누적 카운트**")
col1, col2, col3 = st.columns(3)
with col1:
    st.write(f"차량: {stats['roi_car']:,}")
with col2:
    st.write(f"자전거: {stats['roi_bicycle']:,}")
with col3:
    st.write(f"사람: {stats['roi_person']:,}")

if auto_refresh:
    import time
    time.sleep(1)
    st.rerun()