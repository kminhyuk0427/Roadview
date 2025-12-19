#include <mosquitto.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <signal.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdbool.h>

// MQTT 클라이언트 포인터, 연결 상태 플래그
static struct mosquitto *mosq = NULL;
static volatile bool mqtt_connected = false;

// 멀티스레드 동시접근 방지
static pthread_mutex_t mqtt_lock = PTHREAD_MUTEX_INITIALIZER;

// 마지막으로 사용한 호스트, 포트 (필요 시 재연결용)
static char last_host[256] = {0};
static int last_port = 0;

// 연결 성공/실패 시 호출
static void on_connect(struct mosquitto *mosq_, void *obj, int rc)
{
    (void)mosq_;
    (void)obj;

    pthread_mutex_lock(&mqtt_lock);
    mqtt_connected = (rc == 0);
    pthread_mutex_unlock(&mqtt_lock);

    if (rc == 0)
        printf("[MQTT] connect: success\n");
    else
        printf("[MQTT] connect: fail: %s\n", mosquitto_strerror(rc));
}

//연결 끊김 시 호출
static void on_disconnect(struct mosquitto *mosq_, void *obj, int rc)
{
    (void)mosq_;
    (void)obj;

    pthread_mutex_lock(&mqtt_lock);
    mqtt_connected = false;
    pthread_mutex_unlock(&mqtt_lock);

    printf("[MQTT] connect: disconnection (rc=%d).\n", rc);
}

//초기화
void mqtt_client_init(const char *host, int port)
{
    if (!host || port <= 0)
    {
        printf("[MQTT] invalid host/port\n");
        return;
    }

    // host,port 저장
    pthread_mutex_lock(&mqtt_lock);
    strncpy(last_host, host, sizeof(last_host) - 1);
    last_port = port;
    pthread_mutex_unlock(&mqtt_lock);

    printf("[MQTT] init start: host=%s port=%d\n", host, port);

    // SIGPIPE 무시 (네트워크 끊겨도 프로그램 안죽게)
    signal(SIGPIPE, SIG_IGN);

    mosquitto_lib_init();

    // 클라이언트 생성
    mosq = mosquitto_new(NULL, true, NULL);
    if (!mosq)
    {
        printf("[MQTT] mosquitto_new() failed\n");
        mosquitto_lib_cleanup();
        return;
    }

    // 연결 성공/실패 알림받기
    mosquitto_connect_callback_set(mosq, on_connect);
    mosquitto_disconnect_callback_set(mosq, on_disconnect);

    //네트워크 I/O 백그라운드 스레드 시작
    if (mosquitto_loop_start(mosq) != MOSQ_ERR_SUCCESS)
    {
        printf("[MQTT] mosquitto_loop_start() failed\n");
        mosquitto_destroy(mosq);
        mosq = NULL;
        mosquitto_lib_cleanup();
        return;
    }

    // 비동기 연결 요청
    int rc = mosquitto_connect_async(mosq, host, port, 60);
    if (rc != MOSQ_ERR_SUCCESS)
    {
        printf("[MQTT] mosquitto_connect_async failed: %s\n", mosquitto_strerror(rc));
        pthread_mutex_lock(&mqtt_lock);
        mqtt_connected = false;
        pthread_mutex_unlock(&mqtt_lock);
        return;
    }

    printf("[MQTT] mosquitto_connect_async called (waiting for on_connect)...\n");
}

// (내부용) 실제 publish 수행
static int mqtt_do_publish(const char *topic, const void *payload, int payloadlen, int qos, bool retain)
{
    if (!topic)
        return MOSQ_ERR_INVAL;

    pthread_mutex_lock(&mqtt_lock);

    struct mosquitto *m = mosq;
    bool connected = mqtt_connected;

    if (!m || !connected)
    {
        pthread_mutex_unlock(&mqtt_lock);
        return MOSQ_ERR_NO_CONN;
    }

    int rc = mosquitto_publish(m, NULL, topic, payloadlen, payload, qos, retain);
    if (rc != MOSQ_ERR_SUCCESS)
    {
        printf("[MQTT] mosquitto_publish failed: %s\n", mosquitto_strerror(rc));
        mqtt_connected = false;
    }

    pthread_mutex_unlock(&mqtt_lock);

    return rc;
}

// MQTT 종료 및 정리
void mqtt_client_deinit()
{
    // 전체 파괴 과정을 락 안에서 수행하여 race를 차단
    pthread_mutex_lock(&mqtt_lock);
    struct mosquitto *m = mosq;
    if (!m)
    {
        // 이미 초기화 안 된 상태면 그냥 정리 
        pthread_mutex_unlock(&mqtt_lock);
        mosquitto_lib_cleanup();
        return;
    }
    
    mosquitto_disconnect(m);
    mosquitto_loop_stop(m, true);
    mosquitto_destroy(m);

    // 전역 상태 정리
    mosq = NULL;
    mqtt_connected = false;
    last_host[0] = '\0';
    last_port = 0;
    pthread_mutex_unlock(&mqtt_lock);

    mosquitto_lib_cleanup();
    printf("[MQTT] Deinitialized\n");
}

// 문자열 payload publish
void mqtt_client_publish(const char *topic, const char *payload)
{
    if (!topic || !payload)
        return;

    // printf("MQTT call\n  Topic: %s\n  Payload: %s\n", topic, payload);

    int rc = mqtt_do_publish(topic, payload, strlen(payload), 0, false);

    if (rc == MOSQ_ERR_SUCCESS)
        printf("[MQTT] Publish OK\n");
    else if (rc == MOSQ_ERR_NO_CONN)
        printf("[MQTT] Publish skipped: not connected\n");
    else
        printf("[MQTT] Publish Failed: %s\n", mosquitto_strerror(rc));
}
