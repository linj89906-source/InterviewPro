# -*- coding: utf-8 -*-
"""
高德地图服务封装 — 增强版

- 地理编码（地址 → 经纬度）
- POI 搜索（关键词/分类搜索）
- 周边搜索（多种住宿类型）
- 路线规划（驾车/公交/步行）
- 批量住宿搜索（酒店 + 青旅 + 公寓一站式）
"""

import asyncio
import httpx
import logging
from app.config import AMAP_API_KEY

logger = logging.getLogger(__name__)

AMAP_BASE = "https://restapi.amap.com/v3"

# ── 住宿类型映射（精细分类）───────────────────────────────────

ACCOMMODATION_TYPES = {
    # 酒店/宾馆类
    "hotel": "060000|060100",
    # 经济型/招待所/青年旅社
    "hostel": "060200|060300|060400",
    # 服务式公寓/民宿/短租
    "apartment": "100000|100100|060500",
    # 全部住宿
    "all": "060000|060100|060200|060300|060400|100000|100100|060500",
}

# 住宿类型的中文名
ACCOMMODATION_LABELS = {
    "hotel": "酒店",
    "hostel": "青年旅社/招待所",
    "apartment": "公寓/民宿",
    "all": "全部住宿",
}

# 住宿类型成本估算（用于排序）
ACCOMMODATION_COST_HINT = {
    "0601": "medium",
    "0602": "low",
    "0603": "low",
    "0604": "low",
    "0605": "low",
    "1000": "low",
    "1001": "low",
}

def _get_cost_hint(typecode: str) -> str:
    if not typecode:
        return "unknown"
    for prefix, hint in ACCOMMODATION_COST_HINT.items():
        if typecode.startswith(prefix):
            return hint
    return "unknown"
async def geocode(address: str, city: str = "") -> dict:
    """地理编码：地址 → 经纬度坐标。"""
    params = {"key": AMAP_API_KEY, "address": address}
    if city:
        params["city"] = city
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{AMAP_BASE}/geocode/geo", params=params)
        resp.raise_for_status()
        return resp.json()


async def search_nearby(location: str, types: str, radius: int = 5000) -> dict:
    """周边搜索：根据经纬度和分类搜索附近 POI。"""
    params = {
        "key": AMAP_API_KEY,
        "location": location,
        "types": types,
        "radius": radius,
        "offset": 15,
        "extensions": "all",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{AMAP_BASE}/place/around", params=params)
        resp.raise_for_status()
        return resp.json()


async def search_poi(keywords: str, city: str = "", location: str = "",
                     radius: int = 3000, types: str = "") -> dict:
    """POI 关键词搜索。"""
    params = {
        "key": AMAP_API_KEY,
        "keywords": keywords,
        "city": city,
        "offset": 20,
        "extensions": "all",
    }
    if location:
        params["location"] = location
        params["radius"] = radius
    if types:
        params["types"] = types

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{AMAP_BASE}/place/text", params=params)
        resp.raise_for_status()
        return resp.json()


async def transit_route(origin: str, destination: str, city: str = "") -> dict:
    """公交路线规划（含步行 + 地铁 + 公交）。"""
    params = {
        "key": AMAP_API_KEY,
        "origin": origin,
        "destination": destination,
        "city": city,
        "extensions": "all",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{AMAP_BASE}/direction/transit/integrated", params=params
        )
        resp.raise_for_status()
        return resp.json()


async def driving_route(origin: str, destination: str) -> dict:
    """驾车路线规划。"""
    params = {
        "key": AMAP_API_KEY,
        "origin": origin,
        "destination": destination,
        "extensions": "all",
        "strategy": "0",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{AMAP_BASE}/direction/driving", params=params)
        resp.raise_for_status()
        return resp.json()


# ── 住宿POI过滤白名单 ──────────────────────────────────────

# 只保留真实住宿POI的typecode前缀（宾馆/酒店/青旅/民宿/度假村）
# 住宿类POI: 高德分类06=住宿服务，排除0600(大类太宽泛)和10(住宅)
# Whitelist of real accommodation typecode prefixes (Amap classification)
_ALLOWED_ACCOMMODATION_PREFIXES = ["0601", "0602", "0603", "0604", "0605", "1000", "1001"]


# Name patterns to EXCLUDE (non-accommodation businesses misclassified by Amap)
_EXCLUDE_NAME_PATTERNS = ["便利店","旗舰店","专卖店","超市","银行","atm","lawson","seven","family","餐厅","火锅","奶茶",]

def filter_accommodation_pois(pois: list) -> list:
    if not pois:
        return []
    filtered = []
    excluded_samples = []
    for p in pois:
        code = (p.get("typecode", "") or "")[:4]
        name = (p.get("name", "") or "").lower()
        code_ok = any(code.startswith(prefix) for prefix in _ALLOWED_ACCOMMODATION_PREFIXES)
        name_bad = any(pat in name for pat in _EXCLUDE_NAME_PATTERNS)
        if code_ok and not name_bad:
            filtered.append(p)
        elif len(excluded_samples) < 5:
            excluded_samples.append(p.get("typecode","?")+":"+p.get("name","?"))
    kept = len(filtered)
    total = len(pois)
    if kept < total:
        logger.info("POI filter: kept %d/%d, dropped: %s", kept, total, excluded_samples)
    return filtered
async def search_all_accommodations(location: str, radius: int = 5000) -> dict:
    """
    一站式搜索周边所有住宿类型。

    并行查询：酒店、青旅/招待所、公寓/民宿
    返回三个分类的结果合并列表，按距离排序。
    """
    tasks = [
        search_nearby(location, ACCOMMODATION_TYPES["hotel"], radius),
        search_nearby(location, ACCOMMODATION_TYPES["hostel"], radius),
        search_nearby(location, ACCOMMODATION_TYPES["apartment"], radius),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_pois = []
    categories = ["hotel", "hostel", "apartment"]

    for cat, result in zip(categories, results):
        if isinstance(result, Exception):
            logger.warning("Search failed for %s: %s", cat, result)
            continue
        try:
            pois = result.get("pois", [])
            for p in pois:
                p["_category"] = cat           # 标记类型
                p["_label"] = ACCOMMODATION_LABELS.get(cat, cat)
                biz = p.get("biz_ext", {}) or {}
                p["_cost_hint"] = _get_cost_hint(p.get("typecode", ""))
            all_pois.extend(pois)
        except Exception as e:
            logger.warning("Parse failed for %s: %s", cat, e)

    # 过滤：只保留真实住宿POI
    all_pois = filter_accommodation_pois(all_pois)

    # 按距离排序
    all_pois.sort(key=lambda x: int(x.get("distance", "99999")) if x.get("distance", "").isdigit() else 99999)

    logger.info("Accommodation search: total=%d", len(all_pois))
    return {
        "location": location,
        "total": len(all_pois),
        "pois": all_pois,
    }


# ── 交通分析 ──────────────────────────────────────────────────

async def analyze_transit(origin_loc: str, dest_loc: str, dest_city: str = "") -> dict:
    """
    分析两地之间的交通便利度。

    返回公交方案数、最短时间、步行距离等信息。
    """
    try:
        result = await transit_route(origin_loc, dest_loc, dest_city)
        routes = result.get("route", {}).get("transits", [])
        if routes:
            shortest = min(routes, key=lambda r: int(r.get("duration", "99999")))
            return {
                "mode": "transit",
                "route_count": len(routes),
                "shortest_minutes": int(int(shortest.get("duration", "0")) / 60),
                "walking_distance": shortest.get("walking_distance", "0"),
            }
    except Exception as e:
        logger.warning("Transit analysis failed: %s", e)

    # 回退：仅步行距离估算
    try:
        result = await driving_route(origin_loc, dest_loc)
        paths = result.get("route", {}).get("paths", [])
        if paths:
            duration = int(paths[0].get("duration", "0"))
            return {
                "mode": "driving",
                "route_count": len(paths),
                "shortest_minutes": int(duration / 60),
                "distance": paths[0].get("distance", "0"),
            }
    except Exception as e:
        logger.warning("Driving fallback failed: %s", e)

    return {"mode": "unknown", "error": "无法估算交通时间"}
