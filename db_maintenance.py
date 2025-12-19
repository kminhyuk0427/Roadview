# DB관리 도구
# python3 db_maintenance.py
import sys
from db_manager import DeepStreamDB

db = DeepStreamDB("deepstream_analytics.db")

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def show_status():
    print_header("DB 상태")
    
    if not db.exists():
        print("\n저장된게 없음")
        return False
    
    info = db.get_db_info()
    print(f"\n파일: {info['path']}")
    print(f"크기: {info['size']:,} bytes ({info['size']/1024:.2f} KB)")
    print(f"데이터: {info['count']:,}개")
    return True

# 백업
def backup_database():
    print_header("DB 백업")
    
    if not db.exists():
        print("\n백업할 DB 없음")
        return
    
    try:
        backup_path = db.backup()
        print(f"\n백업 완료: {backup_path}")
        
        import os
        size = os.path.getsize(backup_path)
        print(f"백업 크기: {size:,} bytes ({size/1024:.2f} KB)")
    except Exception as e:
        print(f"\n백업 실패: {e}")

# 데이터 삭제 
def clear_data():
    print_header("데이터 삭제")
    
    if not db.exists():
        print("\nDB가 없음")
        return
    
    info = db.get_db_info()
    print(f"\n현재: {info['count']:,}개 데이터")
    print("테이블 구조 유지하고 DB삭제됨")
    
    confirm = input("\n삭제? (Y/N): ").strip().lower()
    
    if confirm == 'Y':
        try:
            deleted = db.clear_all_data()
            print(f"\n{deleted:,}개 데이터 삭제 완료")
            
            # 최적화 실행
            print("\nDB 최적화 중...")
            vacuum_database(auto=True)
        except Exception as e:
            print(f"\n삭제 실패: {e}")
    else:
        print("\n취소됨")

# 최적화
def vacuum_database(auto=False):
    if not auto:
        print_header("DB 최적화")
    
    if not db.exists():
        print("\nDB가 없음")
        return
    
    try:
        before, after = db.vacuum()
        saved = before - after
        
        print(f"\n최적화 완료")
        print(f"  이전: {before:,} bytes ({before/1024:.2f} KB)")
        print(f"  이후: {after:,} bytes ({after/1024:.2f} KB)")
        print(f"  절약: {saved:,} bytes ({saved/before*100:.1f}%)")
    except Exception as e:
        print(f"\n최적화 실패: {e}")

# 재생성
def recreate_database():
    print_header("DB 재생성")
    
    if db.exists():
        info = db.get_db_info()
        print(f"\n경고: {info['count']:,}개 데이터가 삭제됩니다")
    else:
        print("\n새 DB를 생성")
    
    confirm = input("\n진행하시겠습니까 (Y/N): ").strip().lower()
    
    if confirm != 'Y':
        print("\n취소됨")
        return
    
    # 백업 여부 확인
    if db.exists():
        backup = input("백업 생성? (Y/N): ").strip().lower()
        if backup == 'Y':
            backup_database()
    
    # 기존 DB 삭제
    if db.exists():
        import os
        try:
            os.remove(db.db_path)
            print(f"\n기존 DB 삭제 완료")
        except Exception as e:
            print(f"\n삭제 실패: {e}")
            return
    
    # 새 DB 생성
    try:
        db.init_database()
        print(f"새 DB 생성 완료: {db.db_path}")
    except Exception as e:
        print(f"\n생성 실패: {e}")

# 무결성 검사
def check_integrity():
    print_header("DB 무결성 검사")
    
    if not db.exists():
        print("\nDB없음")
        return
    
    try:
        import sqlite3
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 무결성 검사
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            print("\n무결성 검사: 정상")
        else:
            print(f"\n무결성 검사: 문제 발견")
            print(f"결과: {result}")
        
        # 테이블 정보
        cursor.execute("PRAGMA table_info(analytics_data)")
        columns = cursor.fetchall()
        
        print(f"\n테이블 구조:")
        print(f"  총 {len(columns)}개 컬럼")
        for col in columns:
            print(f"    {col[1]} ({col[2]})")
        
        # 인덱스 정보
        cursor.execute("PRAGMA index_list(analytics_data)")
        indexes = cursor.fetchall()
        
        print(f"\n인덱스: {len(indexes)}개")
        for idx in indexes:
            print(f"    {idx[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n검사 실패: {e}")

# 메뉴
def interactive_menu():
    while True:
        print("\n" + "="*70)
        print("  DeepStream DB 관리 메뉴")
        print("="*70)
        
        if db.exists():
            info = db.get_db_info()
            print(f"  현재: {info['count']:,}개 데이터, {info['size']/1024:.1f} KB")
        else:
            print("  현재: DB 없음")
        
        print("\n  1. 상태 확인")
        print("  2. 백업 생성")
        print("  3. 데이터 삭제 (구조 유지)")
        print("  4. DB 최적화")
        print("  5. DB 재생성")
        print("  6. 무결성 검사")
        print("  0. 종료")
        print("="*70)
        
        choice = input("\n선택 (0-6): ").strip()
        
        if choice == '1':
            show_status()
        elif choice == '2':
            backup_database()
        elif choice == '3':
            clear_data()
        elif choice == '4':
            vacuum_database()
        elif choice == '5':
            recreate_database()
        elif choice == '6':
            check_integrity()
        elif choice == '0':
            print("\n종료합니다.\n")
            break
        else:
            print("\n오류")

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == 'status':
            show_status()
        elif cmd == 'backup':
            backup_database()
        elif cmd == 'clear':
            clear_data()
        elif cmd == 'vacuum':
            vacuum_database()
        elif cmd == 'recreate':
            recreate_database()
        elif cmd == 'check':
            check_integrity()
        elif cmd == 'help':
            print("\n사용법:")
            print("  python3 db_maintenance.py             - 인터랙티브 메뉴")
            print("  python3 db_maintenance.py status      - 상태 확인")
            print("  python3 db_maintenance.py backup      - 백업 생성")
            print("  python3 db_maintenance.py clear       - 데이터 삭제")
            print("  python3 db_maintenance.py vacuum      - 최적화")
            print("  python3 db_maintenance.py recreate    - 재생성")
            print("  python3 db_maintenance.py check       - 무결성 검사")
            print("  python3 db_maintenance.py help        - 도움말\n")
        else:
            print(f"\n알 수 없는 명령: {cmd}")
            print("도움말: python3 db_maintenance.py help\n")
    else:
        interactive_menu()

if __name__ == "__main__":
    main()