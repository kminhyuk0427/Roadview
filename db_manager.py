import sqlite3
import os
from datetime import datetime

class DeepStreamDB:

    def __init__(self, db_path="deepstream_analytics.db"):
        self.db_path = db_path
        
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 기본 분석 데이터 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                car_total INTEGER,
                bicycle_total INTEGER,
                person_total INTEGER,
                lc1_entry_count INTEGER,
                lc1_exit_count INTEGER,
                lc2_entry_count INTEGER,
                lc2_exit_count INTEGER,
                roi_car_cumulative INTEGER,
                roi_bicycle_cumulative INTEGER,
                roi_person_cumulative INTEGER,
                raw_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 알림 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                line_crossing TEXT,
                object_type TEXT,
                message TEXT,
                acknowledged INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 인덱스 생성
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON analytics_data(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON analytics_data(created_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alert_timestamp 
            ON alerts(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alert_acknowledged 
            ON alerts(acknowledged)
        ''')
        
        conn.commit()
        conn.close()
        print(f"  DB 초기화 완료: {self.db_path}")
        return True
        
    def exists(self):
        # DB 파일 존재 여부 확인
        return os.path.exists(self.db_path)
    
    def get_connection(self):
        # DB 연결 반환
        return sqlite3.connect(self.db_path)
    
    def insert_data(self, timestamp, data, raw_message):
        # 데이터 삽입
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO analytics_data (
                    timestamp,
                    car_total,
                    bicycle_total,
                    person_total,
                    lc1_entry_count,
                    lc1_exit_count,
                    lc2_entry_count,
                    lc2_exit_count,
                    roi_car_cumulative,
                    roi_bicycle_cumulative,
                    roi_person_cumulative,
                    raw_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                data.get('car_total', 0),
                data.get('bicycle_total', 0),
                data.get('person_total', 0),
                data.get('lc1_entry_count', 0),
                data.get('lc1_exit_count', 0),
                data.get('lc2_entry_count', 0),
                data.get('lc2_exit_count', 0),
                data.get('roi_car_cumulative', 0),
                data.get('roi_bicycle_cumulative', 0),
                data.get('roi_person_cumulative', 0),
                raw_message
            ))
            
            record_id = cursor.lastrowid
            conn.commit()
            return record_id
            
        except Exception as e:
            print(f" 데이터 삽입 오류: {e}")
            return None
        finally:
            conn.close()

    # add 알림
    def insert_alert(self, timestamp, alert_type, severity, line_crossing=None, 
                    object_type=None, message=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO alerts (
                    timestamp,
                    alert_type,
                    severity,
                    line_crossing,
                    object_type,
                    message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, alert_type, severity, line_crossing, object_type, message))
            
            alert_id = cursor.lastrowid
            conn.commit()
            return alert_id
            
        except Exception as e:
            print(f" 알림 삽입 오류: {e}")
            return None
        finally:
            conn.close()
    
    # 알림 조회
    def get_recent_alerts(self, limit=10, unacknowledged_only=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if unacknowledged_only:
            query = '''
                SELECT * FROM alerts
                WHERE acknowledged = 0
                ORDER BY id DESC
                LIMIT ?
            '''
        else:
            query = '''
                SELECT * FROM alerts
                ORDER BY id DESC
                LIMIT ?
            '''
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    #알림 확인 처리
    def acknowledge_alert(self, alert_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE alerts
                SET acknowledged = 1
                WHERE id = ?
            ''', (alert_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f" 알림 확인 처리 오류: {e}")
            return False
        finally:
            conn.close()
    
    # 심각도별 알림 개수 조회
    def get_alert_count_by_severity(self, hours=24):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT severity, COUNT(*) as count
            FROM alerts
            WHERE timestamp >= datetime('now', '-' || ? || ' hours')
            GROUP BY severity
        ''', (hours,))
        
        result = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in result}
    
    # 오래된 알림 삭제
    def clear_old_alerts(self, days=7):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM alerts
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            ''', (days,))
            
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        except Exception as e:
            print(f" 알림 삭제 오류: {e}")
            return 0
        finally:
            conn.close()

    def get_total_count(self):
        # 전체 데이터 수 췍
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM analytics_data")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_latest(self, limit=1):
        # 최신 데이터 조회
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT * FROM analytics_data
            ORDER BY id DESC
            LIMIT {limit}
        ''')
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_statistics(self):
        # 전체 통계 조회
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 기본 통계
        cursor.execute("SELECT COUNT(*) FROM analytics_data")
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            conn.close()
            return None
        
        # 시간 범위
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM analytics_data")
        min_time, max_time = cursor.fetchone()
        
        # 최대값
        cursor.execute("""
            SELECT 
                MAX(car_total) as max_car,
                MAX(bicycle_total) as max_bicycle,
                MAX(person_total) as max_person,
                MAX(lc1_entry_count) as max_lc1_entry,
                MAX(lc1_exit_count) as max_lc1_exit,
                MAX(lc2_entry_count) as max_lc2_entry,
                MAX(lc2_exit_count) as max_lc2_exit,
                MAX(roi_car_cumulative) as max_roi_car,
                MAX(roi_bicycle_cumulative) as max_roi_bicycle,
                MAX(roi_person_cumulative) as max_roi_person
            FROM analytics_data
        """)
        max_values = cursor.fetchone()
        
        # 평균값
        cursor.execute("""
            SELECT 
                AVG(car_total) as avg_car,
                AVG(bicycle_total) as avg_bicycle,
                AVG(person_total) as avg_person
            FROM analytics_data
        """)
        avg_values = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_count': total_count,
            'time_range': (min_time, max_time),
            'max_values': max_values,
            'avg_values': avg_values
        }
    
    def get_recent_data(self, limit=10):
        # 최근 N개 데이터
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT 
                id, timestamp, 
                car_total, bicycle_total, person_total,
                lc1_entry_count, lc1_exit_count,
                lc2_entry_count, lc2_exit_count,
                roi_car_cumulative, roi_bicycle_cumulative, roi_person_cumulative
            FROM analytics_data
            ORDER BY id DESC
            LIMIT {limit}
        ''')
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_timeline_summary(self, hours=24):
        # 시간별
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as hour,
                COUNT(*) as frame_count,
                MAX(car_total) as max_car,
                MAX(bicycle_total) as max_bicycle,
                MAX(person_total) as max_person,
                MAX(lc1_entry_count + lc1_exit_count) as max_lc1_total,
                MAX(lc2_entry_count + lc2_exit_count) as max_lc2_total
            FROM analytics_data
            WHERE timestamp >= datetime('now', '-{hours} hour')
            GROUP BY hour
            ORDER BY hour DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_time_range(self, start_time, end_time):
        # 특정 범위 조회
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM analytics_data
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        ''', (start_time, end_time))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def clear_all_data(self):
        # 다 삭제
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analytics_data")
        deleted = cursor.rowcount
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='analytics_data'")
        conn.commit()
        conn.close()
        return deleted
    
    def vacuum(self):
        # 최적화
        before_size = os.path.getsize(self.db_path)
        conn = self.get_connection()
        conn.execute("VACUUM")
        conn.close()
        after_size = os.path.getsize(self.db_path)
        return before_size, after_size
    
    def backup(self, backup_path=None):
        # 백업
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"deepstream_analytics_backup_{timestamp}.db"
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        return backup_path
    
    def get_db_info(self):
        # DB정보 조회
        if not self.exists():
            return None
        
        file_size = os.path.getsize(self.db_path)
        record_count = self.get_total_count()
        
        return {
            'path': self.db_path,
            'size': file_size,
            'count': record_count
        }