# streamlit run dashboard.py
import streamlit as st
import sys
import os
from pathlib import Path

# db_manager 임포트
current_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
sys.path.insert(0, str(current_dir))

try:
    from db_manager import DeepStreamDB
    DB_AVAILABLE = True
except ImportError as e:
    st.error(f"db_manager.py를 찾을 수 없음: {e}")
    DB_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="Roadview Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2c3e50;
        padding: 15px 0;
        border-bottom: 3px solid #3498db;
        margin-bottom: 20px;
    }
    .status-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .status-connected {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
    }
    .status-error {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
    }
    .status-warning {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
    }
    .info-text {
        font-size: 1.1rem;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# DB 연결 초기화
@st.cache_resource
def init_database():
    if not DB_AVAILABLE:
        return None, "db_manager.py 모듈을 찾을 수 없음"
    
    try:
        db = DeepStreamDB("deepstream_analytics.db")
        
        # DB 파일 존재 확인
        if not db.exists():
            return None, "DB 파일이 존재하지 않음음 mqtt_receiver.py 먼저 실행"
        
        # 연결 테스트
        info = db.get_db_info()
        if info:
            return db, None
        else:
            return None, "DB 정보를 가져올 수 없음"

    except Exception as e:
        return None, f"DB 연결 오류: {str(e)}"

# 메인 헤더
st.markdown('<div class="main-header">Roadview Dashboard</div>', 
           unsafe_allow_html=True)

# DB 연결 상태 확인
db, error = init_database()

# 연결 상태 표시
st.markdown("### 시스템 연결 상태")

col1, col2 = st.columns(2)

with col1:
    if DB_AVAILABLE:
        st.markdown("""
        <div class="status-box status-connected">
            <div class="info-text"><b>db_manager 모듈</b></div>
            <div style="color: #155724; margin-left: 30px;">정상 로드됨</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-box status-error">
            <div class="info-text"><b>db_manager 모듈</b></div>
            <div style="color: #721c24; margin-left: 30px;">로드 실패</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    if db is not None:
        st.markdown("""
        <div class="status-box status-connected">
            <div class="info-text"><b>SQLite DB 연결</b></div>
            <div style="color: #155724; margin-left: 30px;">연결 성공</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-box status-error">
            <div class="info-text"><b>SQLite DB 연결</b></div>
            <div style="color: #721c24; margin-left: 30px;">{error if error else '연결 실패'}</div>
        </div>
        """, unsafe_allow_html=True)

# DB 정보 표시
if db is not None:
    st.markdown("---")
    st.markdown("### 데이터베이스 정보")
    
    try:
        info = db.get_db_info()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="DB 파일",
                value=info['path']
            )
        
        with col2:
            st.metric(
                label="파일 크기",
                value=f"{info['size'] / 1024:.2f} KB"
            )
        
        with col3:
            st.metric(
                label="총 레코드",
                value=f"{info['count']:,}개"
            )
        
        # 최신 데이터 확인
        if info['count'] > 0:
            st.success("데이터가 정상적으로 저장 됨")
            
            # 최신 레코드 표시
            latest = db.get_latest(1)
            if latest and len(latest) > 0:
                st.markdown("#### 최신 데이터")
                row = latest[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**타임스탬프:** {row[1]}")
                with col2:
                    st.info(f"**DB ID:** {row[0]}")
        else:
            st.warning("아직 저장된 데이터가 없음 mqtt_receiver.py가 실행 중인지 확인")
    
    except Exception as e:
        st.error(f"DB 정보 조회 중 오류: {e}")

# 사이드바
with st.sidebar:
    st.header("설정")
    
    st.markdown("#### 파일 경로")
    db_path = st.text_input(
        "DB 파일 경로",
        value="deepstream_analytics.db",
        help="deepstream_analytics.db 파일의 경로"
    )
    
    st.markdown("---")
    st.markdown("#### 새로고침")
    
    if st.button("연결 상태 새로고침", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()
    
    auto_refresh = st.checkbox("자동 새로고침", value=False)
    if auto_refresh:
        refresh_interval = st.slider(
            "새로고침 간격 (초)",
            min_value=5,
            max_value=60,
            value=10
        )
        import time
        time.sleep(refresh_interval)
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### 사용 가이드")
    st.markdown("""
    1. MQTT 브로커 실행
    2. DeepStream 파이프라인 실행
    3. `mqtt_receiver.py` 실행
    4. 대시보드 확인
    """)

# 푸터
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 20px;">
    <p>DeepStream 7.1 Analytics Dashboard</p>
    <p>연결이 성공하면 실시간 데이터 시각화가 표시됨</p>
</div>
""", unsafe_allow_html=True)

# 디버그 정보
with st.expander("디버그 정보"):
    st.write("**현재 작업 디렉토리:**", os.getcwd())
    st.write("**Python 경로:**", sys.path[:3])
    st.write("**DB_AVAILABLE:**", DB_AVAILABLE)
    st.write("**DB 객체:**", db is not None)
    
    # 파일 존재 확인
    files_to_check = [
        "db_manager.py",
        "data_parser.py",
        "deepstream_analytics.db"
    ]
    
    st.write("**파일 존재 확인:**")
    for file in files_to_check:
        exists = os.path.exists(file)
        st.write(f"  - {file}: {'Y' if exists else 'N'}")