#include "count_manager.h"
#include "mqtt_client.h"
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#define MAX_TRACKED 10000
#define NUM_CLASSES 4     // 0:car, 1:bicycle, 2:person, 3:sign

// 클래스별 total
static uint64_t total_count[NUM_CLASSES] = {0};

// 현재 프레임에서 보이는 개수 cur
static uint64_t cur_count[NUM_CLASSES] = {0};

//클래스별 seen_id
static uint64_t seen_ids[NUM_CLASSES][MAX_TRACKED];
static int seen_count[NUM_CLASSES] = {0};

// 클래스별 ROI 객체 추적용
static uint64_t roi_seen_ids[NUM_CLASSES][MAX_TRACKED];
static int roi_seen_count[NUM_CLASSES] = {0};

// Analytics 데이터
static AnalyticsData analytics_data = {0};

// 시간 추적용 변수
static int last_hour = -1;

//mutex
static pthread_mutex_t cm_lock = PTHREAD_MUTEX_INITIALIZER;

// 현재 시간 문자열 생성
static void get_current_timestamp(char *buffer, size_t size)
{
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    strftime(buffer, size, "%Y-%m-%dT%H:%M:%S", tm_info);
}

// 현재 시각 가져오기
static int get_current_hour(void)
{
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    return tm_info->tm_hour;
}

// ROI 카운트 초기화 함수
static void reset_roi_counts_locked(void)
{
    printf("[COUNT_MGR] ===== HOURLY RESET: Clearing all ROI cumulative counts =====\n");

    for (int c = 0; c < NUM_CLASSES; c++)
    {
        const char *class_names[] = {"Car", "Bicycle", "Person", "Sign"};
        uint64_t old_count = analytics_data.roi_cumulative_count_per_class[c];

        // ROI seen 배열 초기화
        roi_seen_count[c] = 0;
        memset(roi_seen_ids[c], 0, sizeof(roi_seen_ids[c]));

        // ROI 누적 카운트 초기화
        analytics_data.roi_cumulative_count_per_class[c] = 0;

        if (old_count > 0)
        {
            printf("[COUNT_MGR]   %s: %llu -> 0\n",
                   class_names[c],
                   (unsigned long long)old_count);
        }
    }

    printf("[COUNT_MGR] ===== ROI Reset Complete =====\n");
}

// 시간 체크 및 필요시 초기화
static void check_and_reset_hourly_locked(void)
{
    int current_hour = get_current_hour();

    // 처음 실행되는 경우
    if (last_hour == -1)
    {
        last_hour = current_hour;
        printf("[COUNT_MGR] Starting hour tracking at %d:00\n", current_hour);
        return;
    }

    // 시간이 변경된 경우 (23시 -> 0시 케이스 포함)
    if (current_hour != last_hour)
    {
        printf("[COUNT_MGR] Hour changed: %d -> %d\n", last_hour, current_hour);
        reset_roi_counts_locked();
        last_hour = current_hour;
    }
}

//초기화
void count_manager_init(void)
{
    pthread_mutex_lock(&cm_lock);

    for (int c = 0; c < NUM_CLASSES; c++)
    {
        total_count[c] = 0;
        cur_count[c] = 0;
        seen_count[c] = 0;
        roi_seen_count[c] = 0;
        analytics_data.roi_cumulative_count_per_class[c] = 0;
    }

    analytics_data.lc1_entry_count = 0;
    analytics_data.lc1_exit_count = 0;
    analytics_data.lc2_entry_count = 0;
    analytics_data.lc2_exit_count = 0;
    analytics_data.frame_number = 0;
    analytics_data.total_objects = 0;

    get_current_timestamp(analytics_data.json_timestamp,
                          sizeof(analytics_data.json_timestamp));

    // 시간 추적 초기화
    last_hour = get_current_hour();

    pthread_mutex_unlock(&cm_lock);

    printf("[COUNT_MGR] Initialized with per-class ROI tracking and hourly reset\n");
    printf("[COUNT_MGR] Starting at hour: %d\n", last_hour);
}

// 내부: 이미 본 객체인지 검사
static bool has_seen_before_locked(int class_id, uint64_t id)
{
    if (class_id < 0 || class_id >= NUM_CLASSES)
        return false;

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
    if (class_id < 0 || class_id >= NUM_CLASSES)
        return;

    if (seen_count[class_id] < MAX_TRACKED)
    {
        seen_ids[class_id][seen_count[class_id]++] = id;
    }
}

// 내부: 중복 seen 확인
static bool roi_has_seen_before_locked(int class_id, uint64_t id)
{
    if (class_id < 0 || class_id >= NUM_CLASSES)
        return false;

    for (int i = 0; i < roi_seen_count[class_id]; i++)
    {
        if (roi_seen_ids[class_id][i] == id)
            return true;
    }
    return false;
}

// 내부: 중복x 등록
static void roi_mark_seen_locked(int class_id, uint64_t id)
{
    if (class_id < 0 || class_id >= NUM_CLASSES)
        return;

    if (roi_seen_count[class_id] < MAX_TRACKED && !roi_has_seen_before_locked(class_id, id))
    {
        roi_seen_ids[class_id][roi_seen_count[class_id]++] = id;
        // 클래스 카운트 증가
        analytics_data.roi_cumulative_count_per_class[class_id]++;

        const char *class_names[] = {"Car", "Bicycle", "Person", "Sign"};
        printf("[COUNT_MGR] New %s in ROI: ID=%llu, Cumulative=%llu\n",
               class_names[class_id],
               (unsigned long long)id,
               (unsigned long long)analytics_data.roi_cumulative_count_per_class[class_id]);
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

// ROI 내 객체 처리 - 클래스별 누적 카운트
void count_manager_process_roi_obj(int class_id, uint64_t object_id)
{
    if (class_id < 0 || class_id >= NUM_CLASSES)
        return;

    pthread_mutex_lock(&cm_lock);

    // 매 호출마다 시간 체크
    check_and_reset_hourly_locked();

    // 처음 ROI에 들어온 해당 클래스의 객체라면 누적 카운트 증가
    roi_mark_seen_locked(class_id, object_id);

    pthread_mutex_unlock(&cm_lock);
}

// Analytics 데이터 업데이트
void count_manager_update_analytics(
    uint64_t lc1_entry, uint64_t lc1_exit,
    uint64_t lc2_entry, uint64_t lc2_exit,
    uint64_t roi_current_count,
    uint64_t frame_num)
{
    pthread_mutex_lock(&cm_lock);

    // 시간 체크 및 필요시 ROI 초기화
    check_and_reset_hourly_locked();

    analytics_data.lc1_entry_count = lc1_entry;
    analytics_data.lc1_exit_count = lc1_exit;

    analytics_data.lc2_entry_count = lc2_entry;
    analytics_data.lc2_exit_count = lc2_exit;

    analytics_data.frame_number = frame_num;

    // 전체 객체 수 계산
    analytics_data.total_objects = 0;
    for (int c = 0; c < NUM_CLASSES; c++)
    {
        analytics_data.total_objects += cur_count[c];
    }

    // 타임스탬프 업데이트
    get_current_timestamp(analytics_data.json_timestamp,
                          sizeof(analytics_data.json_timestamp));

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
             "{\n"
             "  \"timestamp\": \"%s\",\n"
             "  \"frame_number\": %llu,\n"
             "  \"objects\": {\n"
             "    \"total\": %llu,\n"
             "    \"car\": {\"current\": %llu, \"total\": %llu},\n"
             "    \"bicycle\": {\"current\": %llu, \"total\": %llu},\n"
             "    \"person\": {\"current\": %llu, \"total\": %llu},\n"
             "    \"sign\": {\"current\": %llu, \"total\": %llu}\n"
             "  },\n"
             "  \"analytics\": {\n"
             "    \"line_crossing_pair_1\": {\n"
             "      \"entry\": %llu,\n"
             "      \"exit\": %llu\n"
             "    },\n"
             "    \"line_crossing_pair_2\": {\n"
             "      \"entry\": %llu,\n"
             "      \"exit\": %llu\n"
             "    },\n"
             "    \"roi_cumulative_per_class\": {\n"
             "      \"car\": %llu,\n"
             "      \"bicycle\": %llu,\n"
             "      \"person\": %llu,\n"
             "      \"sign\": %llu\n"
             "    }\n"
             "  }\n"
             "}\n",
             analytics_data.json_timestamp,
             (unsigned long long)analytics_data.frame_number,
             (unsigned long long)analytics_data.total_objects,
             (unsigned long long)cur_count[0], (unsigned long long)total_count[0],
             (unsigned long long)cur_count[1], (unsigned long long)total_count[1],
             (unsigned long long)cur_count[2], (unsigned long long)total_count[2],
             (unsigned long long)cur_count[3], (unsigned long long)total_count[3],
             (unsigned long long)analytics_data.lc1_entry_count,
             (unsigned long long)analytics_data.lc1_exit_count,
             (unsigned long long)analytics_data.lc2_entry_count,
             (unsigned long long)analytics_data.lc2_exit_count,
             (unsigned long long)analytics_data.roi_cumulative_count_per_class[0],
             (unsigned long long)analytics_data.roi_cumulative_count_per_class[1],
             (unsigned long long)analytics_data.roi_cumulative_count_per_class[2],
             (unsigned long long)analytics_data.roi_cumulative_count_per_class[3]);

    for (int c = 0; c < NUM_CLASSES; c++)
        cur_count[c] = 0;

    pthread_mutex_unlock(&cm_lock);
}