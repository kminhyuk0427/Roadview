#ifndef COUNT_MANAGER_H
#define COUNT_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* 0: car
   1: bicycle
   2: person
   3: sign */
#define NUM_CLASSES 4

// 초기화
void count_manager_init(void);

// 매 프레임 객체 처리
void count_manager_process_obj(int class_id, uint64_t object_id);

// 클래스별 total / current 조회
uint64_t count_manager_get_total(int class_id);
uint64_t count_manager_get_current(int class_id);

// json생성 후 출력 + cur초기화
void count_manager_get_json(char *out, size_t out_size);

#endif
