#db조회도구
# python3 view_db.py

import sys
from db_manager import DeepStreamDB

db = DeepStreamDB("deepstream_analytics.db")

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def show_statistics():
    print_header("전체 통계")
    
    if not db.exists():
        print("\nDB 파일을 찾을 수 없음")
        return
    
    stats = db.get_statistics()
    
    if not stats:
        print("\n데이터 없음")
        return
    
    print(f"총 저장된 데이터: {stats['total_count']:,}개")
    print(f"데이터 기간: {stats['time_range'][0]} ~ {stats['time_range'][1]}")
    
    max_vals = stats['max_values']
    print(f"\n누적 최대값:")
    print(f"  - Car: {max_vals[0]}")
    print(f"  - Bicycle: {max_vals[1]}")
    print(f"  - Person: {max_vals[2]}")
    print(f"\nLC 1:")
    print(f"  - Entry: {max_vals[3]}")
    print(f"  - Exit: {max_vals[4]}")
    print(f"\nLC 2:")
    print(f"  - Entry: {max_vals[5]}")
    print(f"  - Exit: {max_vals[6]}")
    print(f"\nROI 누적:")
    print(f"  - Car: {max_vals[7]}")
    print(f"  - Bicycle: {max_vals[8]}")
    print(f"  - Person: {max_vals[9]}")
    
    avg_vals = stats['avg_values']
    print(f"\n평균값:")
    print(f"  - Car: {avg_vals[0]:.1f}")
    print(f"  - Bicycle: {avg_vals[1]:.1f}")
    print(f"  - Person: {avg_vals[2]:.1f}")

def show_recent(n=10):
    print_header(f"최근 {n}개 데이터")
    
    if not db.exists():
        print("\nDB 찾을 수 없음")
        return
    
    rows = db.get_recent_data(n)
    
    if not rows:
        print("데이터 없음")
        return
    
    print(f"\n{'ID':<6} {'Timestamp':<20} {'Car':<6} {'Bike':<6} {'Person':<7} {'LC1(E/X)':<10} {'LC2(E/X)':<10} {'ROI(C/B/P)':<15}")
    print("-"*90)
    
    for row in rows:
        print(f"{row[0]:<6} {row[1]:<20} {row[2]:<6} {row[3]:<6} {row[4]:<7} "
              f"{row[5]}/{row[6]:<8} {row[7]}/{row[8]:<8} {row[9]}/{row[10]}/{row[11]:<10}")

def show_latest():
    print_header("최신 데이터 상세")
    
    if not db.exists():
        print("\nDB 찾을 수 없음")
        return
    
    rows = db.get_latest(1)
    
    if not rows or len(rows) == 0:
        print("데이터 없음")
        return
    
    row = rows[0]
    
    print(f"ID: {row[0]}")
    print(f"타임스탬프: {row[1]}")
    print(f"\n객체 누적 카운트:")
    print(f"  - Car: {row[2]}")
    print(f"  - Bicycle: {row[3]}")
    print(f"  - Person: {row[4]}")
    print(f"\nLC 1:")
    print(f"  - Entry: {row[5]}")
    print(f"  - Exit: {row[6]}")
    print(f"\nLC 2:")
    print(f"  - Entry: {row[7]}")
    print(f"  - Exit: {row[8]}")
    print(f"\nROI 누적:")
    print(f"  - Car: {row[9]}")
    print(f"  - Bicycle: {row[10]}")
    print(f"  - Person: {row[11]}")
    
    # row[12]가 raw_message
    if len(row) > 12 and row[12]:
        print(f"\n원본 메시지 (처음 200자):")
        print(str(row[12])[:200])

def show_timeline():
    print_header("시간대별 요약 (24시간)")
    
    if not db.exists():
        print("\nDB 찾을 수 없음")
        return
    
    rows = db.get_timeline_summary(24)
    
    if not rows:
        print("최근 24시간 데이터가 없습니다")
        return
    
    print(f"\n{'시간':<17} {'데이터수':<10} {'최대Car':<9} {'최대Bike':<10} {'최대Person':<11} {'LC1합':<8} {'LC2합'}")
    print("-"*80)
    
    for row in rows:
        print(f"{row[0]:<17} {row[1]:<10} {row[2]:<9} {row[3]:<10} {row[4]:<11} {row[5]:<8} {row[6]}")

def interactive_menu():
    while True:
        print("\n" + "="*70)
        print("  DeepStream DB 조회 메뉴")
        print("="*70)
        
        if db.exists():
            info = db.get_db_info()
            print(f"  현재: {info['count']:,}개 데이터")
        else:
            print("  DB 없음")
        
        print("\n  1. 전체 통계 보기")
        print("  2. 최근 10개 데이터")
        print("  3. 최신 데이터 상세")
        print("  4. 시간대별 요약")
        print("  5. 최근 N개 보기 (사용자 지정)")
        print("  0. 종료")
        print("="*70)
        
        choice = input("\n선택 (0-5): ").strip()
        
        if choice == '1':
            show_statistics()
        elif choice == '2':
            show_recent(10)
        elif choice == '3':
            show_latest()
        elif choice == '4':
            show_timeline()
        elif choice == '5':
            try:
                n = int(input("몇 개를 볼까요? "))
                show_recent(n)
            except ValueError:
                print("   숫자를 입력")
        elif choice == '0':
            print("\n   종료\n")
            break
        else:
            print("   잘못된 선택")

def main():
    # 명령줄 인자 처리
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'stats':
            show_statistics()
        elif cmd == 'recent':
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            show_recent(n)
        elif cmd == 'latest':
            show_latest()
        elif cmd == 'timeline':
            show_timeline()
        else:
            print(f"알 수 없는 명령: {cmd}")
            print("\n사용법:")
            print("  python3 view_db.py              - 인터랙티브 메뉴")
            print("  python3 view_db.py stats        - 전체 통계")
            print("  python3 view_db.py recent [N]   - 최근 N개")
            print("  python3 view_db.py latest       - 최신 데이터 상세")
            print("  python3 view_db.py timeline     - 시간대별 요약")
    else:
        # 인터랙티브 모드
        interactive_menu()

if __name__ == "__main__":
    main()