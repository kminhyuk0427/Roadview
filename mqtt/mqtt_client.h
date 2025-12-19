#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// MQTT 초기화
void mqtt_client_init(const char *host, int port);

// 문자열 publish
void mqtt_client_publish(const char *topic, const char *payload);

// MQTT 종료 처리
void mqtt_client_deinit(void);

#ifdef __cplusplus
}
#endif

#endif