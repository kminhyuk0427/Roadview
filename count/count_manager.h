#ifndef COUNT_MANAGER_H
#define COUNT_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 0: car
   1: bicycle
   2: person
   3: sign */
#define NUM_CLASSES 4

// analytics 데이터 구조체
typedef struct {
    uint64_t entry_count;
    uint64_t exit_count;
    uint64_t roi_count;        // ROI내 객체 수
    uint64_t frame_number;     // 프레임 번호
    uint64_t total_objects;    // 전체 객체 수
} AnalyticsData;

// 초기화
void count_manager_init(void);

// 매 프레임 객체 처리
void count_manager_process_obj(int class_id, uint64_t object_id);

// Analytics 데이터 업데이트
void count_manager_update_analytics(uint64_t entry, uint64_t exit, uint64_t roi_count, uint64_t frame_num);

// json생성 후 출력 + cur초기화
void count_manager_get_json(char *out, size_t out_size);

#ifdef __cplusplus
}
#endif

#endif