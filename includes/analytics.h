#ifndef _ANALYTICS_H_
#define _ANALYTICS_H_

#include <gst/gst.h>

#ifdef __cplusplus
extern "C" {
#endif

/* User defined */
typedef struct 
{
    guint32 lcc_cnt_exit;
    guint32 lccum_cnt;
    guint32 lcc_cnt_entry;
    guint32 source_id;
} AnalyticsUserMeta;

/* C에서 호출 가능한 wrapper 함수 */
void analytics_custom_parse_nvdsanalytics_meta_data(void *l_user, AnalyticsUserMeta *data);

/* Analytics 메타데이터 처리 함수 (C에서 호출 가능) */
void process_analytics_metadata(void *batch_meta_ptr);

#ifdef __cplusplus
}
#endif

#endif