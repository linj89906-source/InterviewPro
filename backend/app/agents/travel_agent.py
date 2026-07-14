# -*- coding: utf-8 -*-
"""Travel Agent - interview trip planner (no LLM dependency)"""
import json, logging, re, os
from app.services.map_service import (
    geocode, search_all_accommodations, _get_cost_hint,
)

logger = logging.getLogger(__name__)

ACCOMMODATION_TYPE_LABELS = {
    "0600": "hotel", "0601": "hotel", "0602": "budget", "0603": "hostel",
    "0604": "guesthouse", "0605": "bnb", "1000": "apartment", "1001": "apartment",
}
PRICE_LABELS = {"low": "budget", "medium": "mid-range"}

_CITY_PATTERNS = [
    "北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安",
    "苏州", "重庆", "天津", "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波",
    "昆明", "大连", "厦门", "合肥", "佛山", "福州", "哈尔滨", "济南", "温州",
]
_COMPANY_PATTERNS = [
    "腾讯", "阿里", "阿里巴巴", "百度", "字节", "字节跳动", "华为", "美团",
    "京东", "网易", "拼多多", "快手", "滴滴", "小米", "蚂蚁", "携程",
    "哔哩哔哩", "B站", "小红书", "大疆",
]

NL = chr(10)

def _extract_location_regex(user_query):
    result = {"city": "", "address": "", "company": "", "budget": 0, "nights": 1}
    for city in sorted(_CITY_PATTERNS, key=len, reverse=True):
        if city in user_query:
            result["city"] = city
            break
    for comp in sorted(_COMPANY_PATTERNS, key=len, reverse=True):
        if comp in user_query:
            result["company"] = comp
            break
    parts = []
    if result["city"]:
        parts.append(result["city"])
    if result["company"]:
        parts.append(result["company"] + "总部")
    result["address"] = "".join(parts) if parts else user_query.strip()
    m = re.search(r'(?:预算)?(\d+)(?:元|块|以内|预算)', user_query)
    if m:
        result["budget"] = int(m.group(1))
    m = re.search(r'(\d+)\s*[晚天]', user_query)
    if m:
        result["nights"] = int(m.group(1))
    logger.info("TravelAgent regex extract: %s", result)
    return result


class TravelAgent:
    @staticmethod
    def _load_profile(user_id):
        try:
            import sqlite3
            db = os.path.join(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))), "interview.db")
            c = sqlite3.connect(db)
            row = c.execute(
                "SELECT skill_level, school, target_role, target_city FROM user_profiles WHERE user_id=?",
                (user_id,)).fetchone()
            c.close()
            p = {"is_student": True, "budget_pref": "low", "target_city": "", "school": ""}
            if row:
                if row[3]: p["target_city"] = row[3]
                if row[1]: p["school"] = row[1]
            return p
        except:
            return {"is_student": True, "budget_pref": "low", "target_city": "", "school": ""}

    def _score(self, poi, profile):
        s = 0
        try: d = int(poi.get("distance", "5000"))
        except: d = 5000
        s += 40 if d <= 500 else (35 if d <= 1000 else (25 if d <= 2000 else (15 if d <= 3000 else (8 if d <= 5000 else 3))))
        ch = poi.get("_cost_hint", "unknown")
        if profile.get("budget_pref") == "low":
            s += 30 if ch == "low" else (15 if ch == "medium" else 5)
        else:
            s += 18 if ch == "low" else (25 if ch == "medium" else 10)
        biz = poi.get("biz_ext", {}) or {}
        rt = biz.get("rating", "")
        if rt:
            try:
                r = float(rt)
                s += 20 if r >= 4.5 else (14 if r >= 4.0 else (8 if r >= 3.5 else 0))
            except: pass
        if poi.get("address") and len(poi.get("address", "")) > 5: s += 10
        elif poi.get("address"): s += 5
        return s

    def _to_hotel(self, poi, profile):
        tc = (poi.get("typecode", "") or "")[:4]
        ch = poi.get("_cost_hint", "unknown")
        pc = PRICE_LABELS.get(ch, "unknown")
        tn = ACCOMMODATION_TYPE_LABELS.get(tc) or poi.get("_label", "stay")
        ds = (poi.get("distance", "") or "")
        if ds and ds.isdigit():
            di = int(ds)
            dt = f"{di}m" if di < 1000 else f"{di/1000:.1f}km"
        else:
            dt = "unknown"
        rs = []
        if ds and ds.isdigit() and int(ds) <= 1000: rs.append("walkable")
        if ch == "low" and profile.get("budget_pref") == "low": rs.append("student deal")
        elif ch == "low": rs.append("affordable")
        if tc == "0603": rs.append("student budget")
        if tc == "0601": rs.append("reliable")
        biz = poi.get("biz_ext", {}) or {}
        rt = biz.get("rating", "")
        if rt: rs.append(f"rated {rt}")
        reason = ", ".join(rs) if rs else "recommended"
        return {"name": poi.get("name", "unknown"), "distance": dt, "price": pc,
                "type": tn, "reason": reason}

    def _format_answer(self, loc, hotels, profile, coords, geo_ok):
        lines = []
        company = loc.get("company", "") or "unknown"
        city = loc.get("city", "") or "unknown"
        addr = loc.get("address", "") or "unknown"
        budget = loc.get("budget", 0)
        nights = loc.get("nights", 1)
        lines.append("## Location")
        lines.append("- Company: " + company)
        lines.append("- Address: " + addr)
        if not geo_ok:
            lines.append("- (Could not geocode. Showing results based on text search.)")
        lines.append("")
        lines.append("## Recommended Accommodations")
        if hotels:
            lines.append("")
            lines.append("| Name | Type | Distance | Price | Reasons |")
            lines.append("|---|---|---|---|---|")
            for h in hotels:
                lines.append("| " + h["name"] + " | " + h["type"] + " | " + h["distance"] + " | " + h["price"] + " | " + h["reason"] + " |")
        else:
            lines.append("(No accommodations found nearby.)")
        lines.append("")
        lines.append("## Tips")
        if profile.get("is_student"):
            lines.append("- As a student, budget options are prioritized.")
            lines.append("- Consider youth hostels (青旅) for the best rates.")
        lines.append("- Arrive 30 min early on interview day.")
        lines.append("- Check the route the night before.")
        if budget > 0:
            lines.append("- Your budget: " + chr(0x00a5) + str(budget) + "/night.")
        lines.append("")
        return NL.join(lines)

    async def plan(self, user_query, user_id=1):
        loc = _extract_location_regex(user_query)
        addr = loc.get("address") or user_query
        city = loc.get("city") or ""
        company = loc.get("company") or ""
        budget = loc.get("budget", 0)
        nights = loc.get("nights", 1)
        logger.info("TravelAgent: addr=%r city=%r company=%r", addr, city, company)
        profile = self._load_profile(user_id)
        logger.info("TravelAgent: student=%s pref=%s", profile.get("is_student"), profile.get("budget_pref"))
        coords = ""
        geo_ok = False
        try:
            geo = await geocode(address=addr, city=city)
            gc = geo.get("geocodes", [])
            if gc:
                coords = gc[0].get("location", "")
                geo_ok = True
            logger.info("TravelAgent: geocoded->%s", coords)
        except Exception as e:
            logger.warning("geocode fail: %s", e)
        hotels = []
        if geo_ok and coords:
            try:
                acc = await search_all_accommodations(coords, radius=5000)
                pois = acc.get("pois", [])
                if pois:
                    scored = [(self._score(p, profile), p) for p in pois]
                    scored.sort(key=lambda x: x[0], reverse=True)
                    for _, p in scored[:5]:
                        hotels.append(self._to_hotel(p, profile))
                    logger.info("TravelAgent: %d pois -> %d hotels", len(pois), len(hotels))
            except Exception as e:
                logger.warning("accommodation fail: %s", e)
        answer = self._format_answer(loc, hotels, profile, coords, geo_ok)
        return {
            "query": user_query,
            "location": addr if addr else (company or "unknown"),
            "city": city,
            "company": company,
            "coordinates": coords,
            "hotels": hotels,
            "transport": "",
            "suggestion": "",
            "answer": answer,
        }