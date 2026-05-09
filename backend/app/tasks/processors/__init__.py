"""Platform-specific hardcoded processors.

Each processor handles one platform's Excel parsing, column derivation,
and aggregation logic without relying on the generic rule engine.
"""

from app.tasks.processors.douyin import douyin_processor
from app.tasks.processors.kuaishou import kuaishou_processor
from app.tasks.processors.weixin_video import weixin_video_processor
from app.tasks.processors.xiaohongshu import xiaohongshu_processor

# Registry: platform_code -> processor instance
PLATFORM_PROCESSORS = {
    "douyin": douyin_processor,
    "抖店": douyin_processor,
    "kuaishou": kuaishou_processor,
    "快手": kuaishou_processor,
    "xiaohongshu": xiaohongshu_processor,
    "小红书": xiaohongshu_processor,
    "weixin_video": weixin_video_processor,
    "微信小店": weixin_video_processor,
    "视频号": weixin_video_processor,
}

__all__ = [
    "PLATFORM_PROCESSORS",
    "douyin_processor",
    "kuaishou_processor",
    "weixin_video_processor",
    "xiaohongshu_processor",
]
