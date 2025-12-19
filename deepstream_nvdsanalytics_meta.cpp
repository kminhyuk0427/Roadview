/*
 * Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
 */

#include <gst/gst.h>
#include <glib.h>
#include <iostream>
#include <vector>
#include <unordered_map>
#include <sstream>
#include "gstnvdsmeta.h"
#include "nvds_analytics_meta.h"
#include "includes/analytics.h"

/* custom_parse_nvdsanalytics_meta_data
 * and extract nvanalytics metadata */
extern "C" void
analytics_custom_parse_nvdsanalytics_meta_data(void *l_user_ptr, AnalyticsUserMeta *data)
{
	if (!l_user_ptr || !data)
		return;

	NvDsMetaList *l_user = (NvDsMetaList *)l_user_ptr;
	NvDsUserMeta *user_meta = (NvDsUserMeta *)l_user->data;

	/* convert to metadata */
	NvDsAnalyticsFrameMeta *meta =
		(NvDsAnalyticsFrameMeta *)user_meta->user_meta_data;

	/* Fill the data for entry, exit */
	data->lcc_cnt_entry = 0;
	data->lcc_cnt_exit = 0;
	data->lccum_cnt = 0;
	data->lcc_cnt_entry = meta->objLCCumCnt["Entry"];
	data->lcc_cnt_exit = meta->objLCCumCnt["Exit"];
}

// C에서 호출 가능한 analytics 메타데이터 처리 함수
extern "C" void
process_analytics_metadata(void *batch_meta_ptr)
{
	if (!batch_meta_ptr)
		return;

	NvDsBatchMeta *batch_meta = (NvDsBatchMeta *)batch_meta_ptr;

	for (NvDsMetaList *l_frame = batch_meta->frame_meta_list;
		 l_frame != NULL; l_frame = l_frame->next)
	{
		NvDsFrameMeta *frame_meta = (NvDsFrameMeta *)l_frame->data;

		for (NvDsMetaList *l_user = frame_meta->frame_user_meta_list;
			 l_user != NULL; l_user = l_user->next)
		{
			NvDsUserMeta *user_meta = (NvDsUserMeta *)l_user->data;

			if (user_meta->base_meta.meta_type == NVDS_USER_FRAME_META_NVDSANALYTICS)
			{
				NvDsAnalyticsFrameMeta *analytics_meta =
					(NvDsAnalyticsFrameMeta *)user_meta->user_meta_data;

				// ROI 카운트 출력 (objInROIcnt는 std::unordered_map이므로 iterator 사용)
				for (auto &roi_pair : analytics_meta->objInROIcnt)
				{
					g_print("[Analytics] ROI[%s]: %d objects\n",
							roi_pair.first.c_str(),
							roi_pair.second);
				}

				// 현재 라인 크로스 카운트 (objLCCurrCnt도 std::unordered_map)
				for (auto &lc_pair : analytics_meta->objLCCurrCnt)
				{
					g_print("[Analytics] LineCross[%s]: %lu\n",
							lc_pair.first.c_str(),
							lc_pair.second);
				}

				// 누적 카운트 (std::unordered_map)
				AnalyticsUserMeta custom_data = {0};
				analytics_custom_parse_nvdsanalytics_meta_data(l_user, &custom_data);

				g_print("[Analytics] Cumulative - Entry=%d, Exit=%d\n",
						custom_data.lcc_cnt_entry,
						custom_data.lcc_cnt_exit,
						custom_data.lccum_cnt);
			}
		}
	}
}