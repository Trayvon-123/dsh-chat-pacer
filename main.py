from __future__ import annotations

import asyncio
import random

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

# ==== 可调参数 ====
IGNORE_PROB = 0.18      # 装死概率
DELAY_MIN = 1.5         # 回复前最小延迟（秒）
DELAY_MAX = 6.0         # 回复前最大延迟（秒）
MAX_CHARS = 60          # 单条回复最长字数，超出截断
SEND_GAP_MIN = 0.8      # 分段发送之间的额外间隔
SEND_GAP_MAX = 2.0
# =================


@register("chat_pacer", "dsh", "拟人化回复节奏：随机延迟 + 装死 + 限长", "0.1.0")
class ChatPacer(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def pace_incoming(self, event: AstrMessageEvent):
        """收到消息后：按概率装死，否则随机等一会儿再处理。"""
        try:
            text = (event.get_message_str() or "").strip()
        except Exception:  # noqa: BLE001
            text = ""
        # 指令不装死，否则没法调试
        if text.startswith("/") or text.startswith("#"):
            return
        if not text:
            return
        if random.random() < IGNORE_PROB:
            logger.info("[chat_pacer] 装死，跳过这条")
            event.stop_event()
            return
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        logger.info(f"[chat_pacer] 延迟 {delay:.1f}s 后回复")
        await asyncio.sleep(delay)

    @filter.on_decorating_result()
    async def pace_outgoing(self, event: AstrMessageEvent):
        """发送前：再随机等一下，并截断过长内容。"""
        try:
            await asyncio.sleep(random.uniform(SEND_GAP_MIN, SEND_GAP_MAX))
        except Exception:  # noqa: BLE001
            pass
        try:
            result = event.get_result()
            chain = getattr(result, "chain", None) or []
            for comp in chain:
                text = getattr(comp, "text", None)
                if isinstance(text, str) and len(text) > MAX_CHARS:
                    comp.text = text[:MAX_CHARS].rstrip() + "…"
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"[chat_pacer] 截断失败（忽略）: {exc}")
