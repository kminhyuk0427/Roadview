#include "mqtt_client.h"
#include <MQTTClient.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

// MQTT 클라이언트 포인터, 연결 상태 플래그
static MQTTClient client = NULL;
static volatile bool mqtt_connected = false;

// 멀티스레드 동시접근 방지
static pthread_mutex_t mqtt_lock = PTHREAD_MUTEX_INITIALIZER;

// 마지막으로 사용한 호스트, 포트 (재연결용
static char last_host[256] = {0};
static int last_port = 0;
static char mqtt_address[512] = {0};

// MQTT 설정
#define MQTT_CLIENTID "DeepStreamClient"
#define QOS 1
#define TIMEOUT 10000L

// 연결 끊김
void connection_lost(void *context, char *cause)
{
    (void)context;

    pthread_mutex_lock(&mqtt_lock);
    mqtt_connected = false;
    pthread_mutex_unlock(&mqtt_lock);

    printf("[MQTT] Connection lost: %s\n", cause ? cause : "Unknown");
    printf("[MQTT] Attempting to reconnect...\n");
}

// 메시지 도착
int message_arrived(void *context, char *topicName, int topicLen, MQTTClient_message *message)
{
    (void)context;
    (void)topicName;
    (void)topicLen;

    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}

// 전송 완료
void delivery_complete(void *context, MQTTClient_deliveryToken dt)
{
    (void)context;
    (void)dt;
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
    snprintf(mqtt_address, sizeof(mqtt_address), "tcp://%s:%d", host, port);
    pthread_mutex_unlock(&mqtt_lock);

    printf("[MQTT] init start: host=%s port=%d\n", host, port);

    // 클라이언트 생성
    int rc = MQTTClient_create(&client, mqtt_address, MQTT_CLIENTID,
                               MQTTCLIENT_PERSISTENCE_NONE, NULL);
    if (rc != MQTTCLIENT_SUCCESS)
    {
        printf("[MQTT] MQTTClient_create failed: %d\n", rc);
        return;
    }

    // 콜백 설정
    MQTTClient_setCallbacks(client, NULL, connection_lost,
                            message_arrived, delivery_complete);

    // 연결 옵션 설정
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;
    conn_opts.connectTimeout = 10;
    conn_opts.retryInterval = 5;

    // 연결 시도
    rc = MQTTClient_connect(client, &conn_opts);
    if (rc != MQTTCLIENT_SUCCESS)
    {
        printf("[MQTT] MQTTClient_connect failed: %d\n", rc);
        pthread_mutex_lock(&mqtt_lock);
        mqtt_connected = false;
        pthread_mutex_unlock(&mqtt_lock);
        return;
    }

    pthread_mutex_lock(&mqtt_lock);
    mqtt_connected = true;
    pthread_mutex_unlock(&mqtt_lock);

    printf("[MQTT] Connected successfully!\n");
}

// 문자열 payload publish
void mqtt_client_publish(const char *topic, const char *payload)
{
    if (!topic || !payload)
        return;

    pthread_mutex_lock(&mqtt_lock);

    if (!client || !mqtt_connected)
    {
        pthread_mutex_unlock(&mqtt_lock);
        printf("[MQTT] Publish skipped: not connected\n");
        return;
    }

    MQTTClient_message pubmsg = MQTTClient_message_initializer;
    MQTTClient_deliveryToken token;

    pubmsg.payload = (void *)payload;
    pubmsg.payloadlen = strlen(payload);
    pubmsg.qos = QOS;
    pubmsg.retained = 0;

    int rc = MQTTClient_publishMessage(client, topic, &pubmsg, &token);

    pthread_mutex_unlock(&mqtt_lock);

    if (rc == MQTTCLIENT_SUCCESS)
    {
        printf("[MQTT] Publish OK - Topic: %s\n", topic);
    }
    else
    {
        printf("[MQTT] Publish Failed: %d\n", rc);
        pthread_mutex_lock(&mqtt_lock);
        mqtt_connected = false;
        pthread_mutex_unlock(&mqtt_lock);
    }
}

// MQTT 종료 및 정리
void mqtt_client_deinit(void)
{
    pthread_mutex_lock(&mqtt_lock);

    if (client)
    {
        if (mqtt_connected)
        {
            MQTTClient_disconnect(client, 10000);
        }
        MQTTClient_destroy(&client);
        client = NULL;
    }

    mqtt_connected = false;
    last_host[0] = '\0';
    last_port = 0;
    mqtt_address[0] = '\0';

    pthread_mutex_unlock(&mqtt_lock);

    printf("[MQTT] Deinitialized\n");
}