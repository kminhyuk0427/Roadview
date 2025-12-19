#include "count_manager.h"
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

#define MAX_TRACKED 10000
#define NUM_CLASSES 4     // 0:car, 1:bicycle, 2:person, 3:sign

// 클래스별 total
static uint64_t total_count[NUM_CLASSES] = {0};

// 현재 프레임에서 보이는 개수 cur
static uint64_t cur_count[NUM_CLASSES] = {0};

//클래스별 seen_id
static uint64_t seen_ids[NUM_CLASSES][MAX_TRACKED];
static int seen_count[NUM_CLASSES] = {0};

//mutex
static pthread_mutex_t cm_lock = PTHREAD_MUTEX_INITIALIZER;

static uint64_t frame_count = 0;

static const char* class_names[NUM_CLASSES] = {
    "car", "bicycle", "person", "sign"
};

//초기화
void count_manager_init(void)
{
    pthread_mutex_lock(&cm_lock);

    for (int c = 0; c < NUM_CLASSES; c++)
    {
        total_count[c] = 0;
        cur_count[c] = 0;
        seen_count[c] = 0;
    }

    frame_count = 0;

    pthread_mutex_unlock(&cm_lock);
}

// 내부: 이미 본 객체인지 검사
static bool has_seen_before_locked(int class_id, uint64_t id)
{
    for (int i = 0; i < seen_count[class_id]; i++)
    {
        if (seen_ids[class_id][i] == id)
            return true;
    }
    return false;
}

// 내부: seen 등록 
static void mark_seen_locked(int class_id, uint64_t id)
{
    if (seen_count[class_id] < MAX_TRACKED)
    {
        seen_ids[class_id][seen_count[class_id]++] = id;
    }
}

// 객체 한 개 처리
void count_manager_process_obj(int class_id, uint64_t object_id)
{
    if (class_id < 0 || class_id >= NUM_CLASSES)
        return;

    pthread_mutex_lock(&cm_lock);

    // 프레임에서 나온 개수 증가
    cur_count[class_id]++;

    // total: 처음 등장한 ID
    if (!has_seen_before_locked(class_id, object_id))
    {
        total_count[class_id]++;
        mark_seen_locked(class_id, object_id);
    }

    pthread_mutex_unlock(&cm_lock);
}

// JSON 생성 함수(프래임마다 계속 출력)
void count_manager_get_json(char *out, size_t out_size)
{
    if (!out || out_size == 0)
        return;

    pthread_mutex_lock(&cm_lock);

    // 통계 문자열 생성
    snprintf(out, out_size,
             "car:cur=%llu,total=%llu | "
             "bicycle:cur=%llu,total=%llu | "
             "person:cur=%llu,total=%llu | "
             "sign:cur=%llu,total=%llu",
             (unsigned long long)cur_count[0], (unsigned long long)total_count[0],
             (unsigned long long)cur_count[1], (unsigned long long)total_count[1],
             (unsigned long long)cur_count[2], (unsigned long long)total_count[2],
             (unsigned long long)cur_count[3], (unsigned long long)total_count[3]);

    for (int c = 0; c < NUM_CLASSES; c++)
        cur_count[c] = 0;

    pthread_mutex_unlock(&cm_lock);
}