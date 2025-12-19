# 파싱
import json

def parse_deepstream_json(payload):
# 문자열 -> timestamp
    try:
        json_data = json.loads(payload)
        data = {}

        timestamp = json_data.get('timestamp', None)
        
        # 객체 누적 total 값만 추출
        if 'objects' in json_data:
            objects = json_data['objects']
            
            if 'car' in objects and isinstance(objects['car'], dict):
                data['car_total'] = int(objects['car'].get('total', 0))
            
            if 'bicycle' in objects and isinstance(objects['bicycle'], dict):
                data['bicycle_total'] = int(objects['bicycle'].get('total', 0))
            
            if 'person' in objects and isinstance(objects['person'], dict):
                data['person_total'] = int(objects['person'].get('total', 0))
        
        # analytics 파싱
        if 'analytics' in json_data:
            analytics = json_data['analytics']
            
            if 'line_crossing_pair_1' in analytics:
                lc1 = analytics['line_crossing_pair_1']
                data['lc1_entry_count'] = int(lc1.get('entry', 0))
                data['lc1_exit_count'] = int(lc1.get('exit', 0))
            
            if 'line_crossing_pair_2' in analytics:
                lc2 = analytics['line_crossing_pair_2']
                data['lc2_entry_count'] = int(lc2.get('entry', 0))
                data['lc2_exit_count'] = int(lc2.get('exit', 0))
            
            # roi모든 클래스 추출
            if 'roi_cumulative_per_class' in analytics:
                roi = analytics['roi_cumulative_per_class']
                data['roi_car_cumulative'] = int(roi.get('car', 0))
                data['roi_bicycle_cumulative'] = int(roi.get('bicycle', 0))
                data['roi_person_cumulative'] = int(roi.get('person', 0))
        
        return timestamp, data if data else None
        
    except json.JSONDecodeError as e:
        print(f"JSON 디코딩 오류: {e}")
        return None, None
    except (KeyError, ValueError, TypeError) as e:
        print(f"JSON 파싱 오류: {e}")
        return None, None
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        return None, None


def format_data_summary(data):
    if not data:
        return "파싱된 데이터 없음"
    
    lines = []
    
    # 객체 누적 카운트
    if any(k in data for k in ['car_total', 'bicycle_total', 'person_total']):
        lines.append("객체 누적:")
        if 'car_total' in data:
            lines.append(f"  Car: {data['car_total']}")
        if 'bicycle_total' in data:
            lines.append(f"  Bicycle: {data['bicycle_total']}")
        if 'person_total' in data:
            lines.append(f"  Person: {data['person_total']}")
    
    # lC 1
    if 'lc1_entry_count' in data or 'lc1_exit_count' in data:
        lines.append("\lC 1:")
        lines.append(f"  Entry: {data.get('lc1_entry_count', 0)}")
        lines.append(f"  Exit: {data.get('lc1_exit_count', 0)}")
    
    # lC 2
    if 'lc2_entry_count' in data or 'lc2_exit_count' in data:
        lines.append("\lC 2:")
        lines.append(f"  Entry: {data.get('lc2_entry_count', 0)}")
        lines.append(f"  Exit: {data.get('lc2_exit_count', 0)}")
    
    # ROI 카운트
    if any(k in data for k in ['roi_car_cumulative', 'roi_bicycle_cumulative', 'roi_person_cumulative']):
        lines.append("\nROI 누적:")
        if 'roi_car_cumulative' in data:
            lines.append(f"  Car: {data['roi_car_cumulative']}")
        if 'roi_bicycle_cumulative' in data:
            lines.append(f"  Bicycle: {data['roi_bicycle_cumulative']}")
        if 'roi_person_cumulative' in data:
            lines.append(f"  Person: {data['roi_person_cumulative']}")
    
    return '\n'.join(lines) if lines else "데이터 none"