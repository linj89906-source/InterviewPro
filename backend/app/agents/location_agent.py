# -*- coding: utf-8 -*-
"""
Location Agent — 面试行程规划助手

不只是"查附近酒店"，而是：
  1. 识别面试地点 → 地理编码
  2. 搜索全类型住宿（酒店 + 青旅 + 公寓/民宿）
  3. 分析交通便利度（公交/地铁到达面试地点的时间）
  4. 结合用户画像（学生 → 优先预算型）给出个性化推荐
  5. 输出结构化的行程建议（住宿 + 交通 + 注意事项）

触发条件：由 Supervisor Agent 自动判断，用户不需要手动选择功能。
"""

import asyncio
import json
import logging
import re
from app.agents.base import BaseAgent
from app.services.map_service import (
    geocode,
    search_all_accommodations,
    analyze_transit,
    ACCOMMODATION_LABELS,
    _get_cost_hint,
)

logger = logging.getLogger(__name__)


# ── 系统提示词 ────────────────────────────────────────────────

LOCATION_SYSTEM_PROMPT = """你是一位贴心的面试出行助手，帮助求职者规划面试地点的住宿和交通。

## 你的能力
- 识别面试公司/地点，获取准确位置
- 搜索附近所有类型的住宿：酒店、青年旅社、公寓/民宿
- 分析交通便利度（是否有地铁/公交直达）
- 结合用户画像给出个性化推荐

## 推荐优先级
1. **预算型用户（学生/应届生）**：优先推荐青年旅社、经济型酒店，标注价格区间
2. **品质型用户**：优先推荐评分高、交通便利的酒店
3. **所有人**：必须考虑步行距离、公共交通可达性、周边安全性

## 回复格式
```
## 面试地点确认
- 公司：XXX
- 地址：XXX

## 推荐住宿（按推荐度排序）
| 名称 | 类型 | 距离 | 交通 | 适合人群 | 亮点 |
|------|------|------|------|----------|------|

## 最佳选择
推荐 1-2 个最合适的，说明理由

## 交通建议
- 面试当天建议提前多久出发
- 推荐交通方式

## 面试小贴士
- 面试前一天实地踩点
- 准备好所需证件
- 其他注意事项
```

## 规则
- 使用中文回复
- 如果地图 API 没有返回数据，诚实告知并给出通用建议
- 如果用户提供的地址模糊，追问澄清
"""


# ── 地点提取提示词 ────────────────────────────────────────────

EXTRACTION_PROMPT = """从以下用户消息中提取面试地点信息。返回纯 JSON（不要 markdown 代码块）：

{{{{
  "city": "城市名",
  "address": "具体地址或公司全称（用于地图搜索）",
  "company": "公司名",
  "interview_date": "面试日期（如果有，格式 YYYY-MM-DD，没有填 null）"
}}}}

用户消息：{user_query}"""


# ── Agent 类 ─────────────────────────────────────────────────

class LocationAgent:
    """面试行程规划 Agent。

    使用方式：
        agent = LocationAgent()
        result = agent.plan(user_query="我要去深圳腾讯总部面试", user_id=1)
        print(result["reply"])
    """

    def __init__(self):
        pass

    # ── 用户画像 ──────────────────────────────────────────────

    @staticmethod
    def _load_profile(user_id: int) -> dict:
        """加载用户画像，用于个性化推荐。"""
        try:
            import sqlite3
            from app.config import DATABASE_URL

            db_path = DATABASE_URL.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)

            # 画像
            row = conn.execute(
                """SELECT skill_level, school, target_role, target_city
                   FROM user_profiles WHERE user_id = ?""",
                (user_id,),
            ).fetchone()

            profile = {
                "is_student": True,       # 默认假设是学生
                "budget": "low",           # low / medium / high
                "target_city": "",
                "school": "",
            }

            if row:
                if row[3]:
                    profile["target_city"] = row[3]
                if row[1]:
                    profile["school"] = row[1]

            # 从简历分析中推断是否学生
            resume = conn.execute(
                """SELECT basic_info FROM resume_analyses
                   WHERE user_id = ? AND status = 'completed'
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id,),
            ).fetchone()

            if resume and resume[0]:
                try:
                    basic = json.loads(resume[0])
                    # 如果简历中有学历信息
                    if "学历" in str(basic) or "本科" in str(basic) or "硕士" in str(basic):
                        profile["is_student"] = True
                except (json.JSONDecodeError, TypeError):
                    pass

            conn.close()
            return profile

        except Exception as e:
            logger.warning("Failed to load profile for user %d: %s", user_id, e)
            return {"is_student": True, "budget": "low", "target_city": "", "school": ""}

    # ── 地点提取 ──────────────────────────────────────────────

    def _extract_location(self, user_query: str) -> dict:
        """用 LLM 从用户消息中提取面试地点信息。"""
        agent = BaseAgent()
        agent.SYSTEM_PROMPT = "你是一个信息抽取器，只返回 JSON。"
        agent.temperature = 0.0
        agent.max_tokens = 300

        prompt = EXTRACTION_PROMPT.format(user_query=user_query)
        raw = agent.invoke(prompt)

        # 尝试解析 JSON
        try:
            # 去除可能的 markdown 代码块标记
            cleaned = raw.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{[^{}]*\}", raw)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        # 兜底：用原始查询作为地址
        logger.warning("Location extraction failed, using raw query")
        return {"city": "", "address": user_query, "company": "", "interview_date": None}

    # ── 住宿打分 ──────────────────────────────────────────────

    def _score_accommodation(self, poi: dict, profile: dict) -> int:
        """
        给一个住宿 POI 打分 (0-100)。

        评分维度：
        - 距离 (0-40)：越近越高
        - 价格 (0-30)：学生用户 → 便宜 = 高分
        - 评分 (0-15)：有高德评分就加分
        - 交通 (0-15)：有公交路线经过加分
        """
        score = 0

        # 距离分
        try:
            dist = int(poi.get("distance", "5000"))
        except (ValueError, TypeError):
            dist = 5000

        if dist <= 500:
            score += 40
        elif dist <= 1000:
            score += 35
        elif dist <= 2000:
            score += 25
        elif dist <= 3000:
            score += 15
        elif dist <= 5000:
            score += 8
        else:
            score += 3

        # 价格分
        cost_hint = poi.get("_cost_hint", "unknown")
        if profile.get("budget") == "low":
            if cost_hint == "low":
                score += 30
            elif cost_hint == "medium":
                score += 15
            else:
                score += 5
        else:
            # 非学生：中等价位加分
            if cost_hint == "medium":
                score += 25
            elif cost_hint == "low":
                score += 18
            else:
                score += 10

        # 评分分
        biz = poi.get("biz_ext", {}) or {}
        rating = biz.get("rating", "")
        if rating:
            try:
                r = float(rating)
                if r >= 4.5:
                    score += 15
                elif r >= 4.0:
                    score += 10
                elif r >= 3.5:
                    score += 5
            except (ValueError, TypeError):
                pass

        # 交通分（有地址说明可达性好）
        address = poi.get("address", "")
        if address and len(address) > 5:
            score += 10
        elif address:
            score += 5

        return score

    # ── 格式化住宿数据 ────────────────────────────────────────

    def _format_accommodations(self, pois: list[dict], profile: dict,
                               top_n: int = 15) -> str:
        """将 POI 数据格式化为 LLM 可读的文本。"""
        if not pois:
            return "（未找到附近住宿）"

        # 打分排序
        scored = [(self._score_accommodation(p, profile), p) for p in pois]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_n]

        lines = []
        for rank, (s, p) in enumerate(top, 1):
            name = p.get("name", "未知")
            dist = p.get("distance", "?") + "m"
            addr = p.get("address", "无地址")
            label = p.get("_label", "酒店")
            cost = p.get("_cost_hint", "unknown")

            biz = p.get("biz_ext", {}) or {}
            rating = biz.get("rating", "无评分")
            biz_cost = biz.get("cost", "无价格")

            # 价格等级翻译
            cost_cn = {"low": "经济型", "medium": "中档", "high": "高端", "unknown": "未知"}

            # 对学生友好的标签
            student_tag = ""
            if profile.get("is_student") and cost in ("low",):
                student_tag = " [学生优选]"

            lines.append(
                f"{rank}. {name}{student_tag} | 类型: {label} | "
                f"距离: {dist} | 档次: {cost_cn.get(cost, cost)} | "
                f"评分: {rating} | 参考价: {biz_cost} | "
                f"地址: {addr}"
            )

        return "\n".join(lines)

    # ── 主入口 ─────────────────────────────────────────────────

    def plan(self, user_query: str, user_id: int = 1) -> dict:
        """
        规划面试行程。

        Args:
            user_query: 用户原始输入，如"我要去深圳腾讯总部面试"
            user_id: 用户 ID

        Returns:
            {
                "query": str,
                "location": {"address": str, "city": str, "coordinates": str, "company": str},
                "accommodations": str,        # 格式化后的住宿列表
                "top_picks": list[dict],      # 排名前 5 的住宿
                "profile_used": dict,         # 使用的用户画像
                "answer": str,                # LLM 生成的最终推荐
            }
        """
        # ── 1. 提取地点 ──
        location_info = self._extract_location(user_query)
        address = location_info.get("address", user_query)
        city = location_info.get("city", "")
        company = location_info.get("company", "")
        interview_date = location_info.get("interview_date")
        logger.info("LocationAgent: address=%r, city=%r, company=%r", address, city, company)

        # ── 2. 加载用户画像 ──
        profile = self._load_profile(user_id)
        logger.info("LocationAgent: profile is_student=%s, budget=%s",
                     profile.get("is_student"), profile.get("budget"))

        # ── 3. 地理编码 ──
        coordinates = ""
        try:
            geo = asyncio.run(geocode(address=address, city=city))
            geocodes = geo.get("geocodes", [])
            if geocodes:
                coordinates = geocodes[0].get("location", "")
                logger.info("Geocoded: %s -> %s", address, coordinates)
        except Exception as e:
            logger.warning("Geocode failed: %s", e)

        # ── 4. 搜索所有住宿类型 ──
        accommodation_text = "（未找到附近住宿数据）"
        top_picks = []

        if coordinates:
            try:
                acc_result = asyncio.run(
                    search_all_accommodations(coordinates, radius=5000)
                )
                pois = acc_result.get("pois", [])

                if pois:
                    # 格式化 + 打分排序
                    accommodation_text = self._format_accommodations(
                        pois, profile, top_n=15
                    )

                    # 选 top 5
                    scored = [(self._score_accommodation(p, profile), p) for p in pois]
                    scored.sort(key=lambda x: x[0], reverse=True)
                    for score, p in scored[:5]:
                        top_picks.append({
                            "name": p.get("name", ""),
                            "type": p.get("_label", ""),
                            "distance": p.get("distance", ""),
                            "address": p.get("address", ""),
                            "score": score,
                            "cost_hint": _get_cost_hint(p.get("typecode", "")),
                        })

                logger.info("Accommodation search: %d found, %d top picks",
                            len(pois), len(top_picks))
            except Exception as e:
                logger.warning("Accommodation search failed: %s", e)
                accommodation_text = f"（搜索住宿时出错：{e}）"

        # ── 5. LLM 生成推荐 ──
        user_prompt = f"""## 用户需求
{user_query}

## 面试地点信息
- 公司：{company or "未识别"}
- 地址：{address}
- 城市：{city or "未识别"}
- 坐标：{coordinates or "无法获取"}
{'面试日期：' + interview_date if interview_date else "面试日期：未提及"}

## 用户画像
- {'在校学生/应届生' if profile.get('is_student') else '有工作经验'}
- 预算偏好：{'经济型优先' if profile.get('budget') == 'low' else '性价比优先'}
- 学校：{profile.get('school') or '未知'}
- 目标城市：{profile.get('target_city') or '未知'}

## 附近住宿数据（按推荐度排序）
{accommodation_text}

请基于以上数据，给出个性化的住宿和行程推荐。"""

        # 组装系统提示词
        system_prompt = LOCATION_SYSTEM_PROMPT
        if profile.get("is_student"):
            system_prompt += (
                "\n\n## 特别注意\n"
                "用户是在校学生/应届生，预算有限。请优先推荐青旅和经济型酒店，"
                "重点关注价格和交通便利度，帮助用户省钱。"
            )
        if profile.get("target_city"):
            system_prompt += (
                f"\n用户的求职目标城市是 {profile['target_city']}，"
                "如果面试城市匹配目标城市，可以提及这一点作为鼓励。"
            )

        agent = BaseAgent()
        agent.SYSTEM_PROMPT = system_prompt
        agent.temperature = 0.4
        agent.max_tokens = 2048

        answer = agent.invoke(user_prompt)

        return {
            "query": user_query,
            "location": {
                "address": address,
                "city": city,
                "company": company,
                "coordinates": coordinates,
                "interview_date": interview_date,
            },
            "accommodations": accommodation_text,
            "top_picks": top_picks,
            "profile_used": profile,
            "answer": answer,
        }
