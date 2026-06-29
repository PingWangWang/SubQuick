"""伪射手网 (assrt.net) API 适配器

通过 assrt.net 开放接口搜索和下载中文字幕。
伪射手网是射手网(Shooter.cn)的替代/衍生服务，接口独立。
纯 requests 实现，无需额外依赖。

API 文档参考: docs/API文档-射手网.md

使用流程:
  1. search()     → GET /v1/sub/search     → 获取字幕列表（含 id）
  2. get_detail() → GET /v1/sub/detail?id=  → 获取下载 URL
  3. download()   → 内部自动调 detail + 下载 .rar 并解压
"""

from __future__ import annotations

import io
import os
import time
from typing import Optional

import requests

from app.downloader.base import (
    BaseProvider,
    SearchParams,
    SearchResult,
    SearchResultItem,
)


# ── 常量 ──────────────────────────────────────────────────

API_BASE_URL = "https://api.assrt.net"
API_FALLBACK_URL = "https://api.makedie.me"

USER_AGENT = "SubQuick v1.0 / assrt.net API"

SEARCH_MAX_COUNT = 15               # API 限制最多 15
REQUEST_INTERVAL = 12.0             # 保守限制：5次/分钟（API 默认配额 20次/分钟）
MAX_RETRIES = 2
RETRY_DELAYS = [2.0, 5.0]


# ── 语言代码映射 ──────────────────────────────────────────

LANG_MAP = {
    "langzh": "zh", "langdou": "zh", "langchi": "zh",
    "langen": "en", "langja": "ja", "langkor": "ko",
    "langfr": "fr", "langde": "de", "langru": "ru",
    "langit": "it", "langes": "es", "langpt": "pt",
    "langar": "ar", "langth": "th", "langvi": "vi",
}


class AssrtError(Exception):
    pass


class ShooterProvider(BaseProvider):
    """伪射手网 (assrt.net) 字幕适配器"""

    def __init__(
        self,
        api_key: str = "",
        api_base: str = API_BASE_URL,
        timeout: int = 30,
        proxy: Optional[dict] = None,
    ):
        super().__init__(api_key=api_key, timeout=timeout)
        self.api_base = api_base
        self.proxy = proxy
        self._session: Optional[requests.Session] = None
        self._last_request_time: float = 0.0

    @property
    def provider_name(self) -> str:
        return "shooter"

    # ── HTTP 层 ──────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            })
            if self.api_key:
                self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        return self._session

    def _respect_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _request(
        self, method: str, endpoint: str,
        params: Optional[dict] = None,
        raw: bool = False,
    ) -> dict | bytes:
        base = self.api_base.rstrip("/")
        url = f"{base}{endpoint}"
        p = dict(params or {})
        if self.api_key:
            p.setdefault("token", self.api_key)
        session = self._get_session()
        proxies = None
        if self.proxy:
            pu = self.proxy.get("url", "")
            if pu:
                proxies = {"http": pu, "https": pu}
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                self._respect_rate_limit()
                resp = session.request(
                    method, url, params=p,
                    timeout=self.timeout, proxies=proxies,
                )
                if resp.status_code == 429:
                    time.sleep(5)
                    continue
                if resp.status_code >= 500:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                    raise AssrtError(f"服务器错误 ({resp.status_code})")
                resp.raise_for_status()
                if raw:
                    return resp.content
                data = resp.json()
                status = data.get("status", -1)
                if status != 0:
                    raise AssrtError(f"API 错误 ({status}): {_get_error_message(status)}")
                return data
            except AssrtError:
                raise
            except requests.Timeout as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                raise AssrtError(f"请求超时: {url}") from e
            except requests.ConnectionError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                raise AssrtError(f"连接失败: {url}") from e
            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                raise AssrtError(f"请求失败: {e}") from e
        raise AssrtError(f"请求失败（已重试 {MAX_RETRIES} 次）") from last_error

    # ── 搜索 ──────────────────────────────────────────────

    def search(self, params: SearchParams) -> SearchResult:
        if not params.is_valid:
            return SearchResult(provider=self.provider_name, error="搜索参数无效")
        keyword = (params.query or params.file_name or "").strip()
        if not keyword:
            return SearchResult(provider=self.provider_name, error="搜索关键词为空")
        if len(keyword) < 3:
            return SearchResult(
                provider=self.provider_name,
                error="搜索关键词长度必须大于3个字符",
            )
        query_params = {
            "q": keyword,
            "pos": 0,
            "cnt": min(params.max_count or SEARCH_MAX_COUNT, SEARCH_MAX_COUNT),
            "is_file": 1,
        }
        try:
            data = self._request("GET", "/v1/sub/search", params=query_params)
        except AssrtError as e:
            return SearchResult(provider=self.provider_name, error=str(e))
        items = []
        try:
            for idx, sub in enumerate(data.get("sub", {}).get("subs", [])):
                if not isinstance(sub, dict):
                    continue
                sub_id = str(sub.get("id", ""))
                if not sub_id:
                    continue
                items.append(SearchResultItem(
                    subtitle_id=sub_id,
                    language=self._parse_language(sub),
                    file_name=sub.get("videoname", ""),
                    score=self._calc_score(sub),
                    download_url="",          # 搜索不返回下载链接
                    format="srt" if "srt" in sub.get("subtype", "").lower() else sub.get("subtype", ""),
                    upload_date=sub.get("upload_time", ""),
                    raw_data=sub,
                ))
        except (KeyError, TypeError, ValueError) as e:
            return SearchResult(
                provider=self.provider_name, items=items,
                error=f"解析搜索结果失败: {e}",
            )
        return SearchResult(
            provider=self.provider_name, items=items, total_count=len(items),
        )

    # ── 获取详情（含下载地址） ─────────────────────────────

    def get_detail(self, subtitle_id: str) -> dict:
        """获取字幕详细信息（含下载链接）

        GET /v1/sub/detail?token=TOKEN&id=ID
        """
        data = self._request("GET", "/v1/sub/detail", params={"id": subtitle_id})
        subs = data.get("sub", {}).get("subs", [])
        if not subs:
            raise AssrtError(f"字幕不存在 (ID: {subtitle_id})")
        return subs[0]

    # ── 下载 ──────────────────────────────────────────────

    def download(self, subtitle_id: str) -> tuple[bytes, str]:
        """下载字幕文件

        流程：detail 获取 URL → 下载 .rar → 解压提取 .srt
        """
        try:
            detail = self.get_detail(subtitle_id)
        except AssrtError as e:
            raise AssrtError(f"获取字幕详情失败: {e}")

        download_url = detail.get("url", "")
        if not download_url:
            raise AssrtError(f"未获取到下载链接 (ID: {subtitle_id})")
        archive_name = detail.get("filename", f"subtitle_{subtitle_id}.rar")

        try:
            content = self._request("GET", download_url, raw=True)
        except AssrtError as e:
            raise AssrtError(f"下载字幕文件失败: {e}")
        if not content:
            raise AssrtError("下载的文件内容为空")

        return self._extract_subtitle(content, archive_name, detail)

    # ── 辅助方法 ──────────────────────────────────────────

    @staticmethod
    def _parse_language(sub: dict) -> str:
        lang_info = sub.get("lang", {})
        if isinstance(lang_info, dict):
            langlist = lang_info.get("langlist", {})
            if isinstance(langlist, dict):
                for key in LANG_MAP:
                    if langlist.get(key):
                        return LANG_MAP[key]
            desc = lang_info.get("desc", "")
            if "双" in desc or "中" in desc:
                return "zh"
            if "英" in desc:
                return "en"
        return "zh"

    @staticmethod
    def _calc_score(sub: dict) -> float:
        score = 6.0
        if "srt" in sub.get("subtype", "").lower():
            score += 2.0
        vote = sub.get("vote_score", 0)
        if isinstance(vote, (int, float)) and vote > 0:
            score += min(vote / 100, 2.0)
        return min(score, 10.0)

    @staticmethod
    def _extract_subtitle(
        content: bytes, archive_name: str, detail: dict,
    ) -> tuple[bytes, str]:
        filelist = detail.get("filelist", [])
        # 1) 优先用 filelist 中的独立下载链接
        for entry in filelist:
            if not isinstance(entry, dict):
                continue
            fname = entry.get("f", "")
            if os.path.splitext(fname)[1].lower() not in (".srt", ".ass", ".ssa"):
                continue
            file_url = entry.get("url", "")
            if file_url:
                try:
                    resp = requests.get(file_url, timeout=30)
                    resp.raise_for_status()
                    return resp.content, fname
                except requests.RequestException:
                    pass
        # 2) 尝试 rarfile 解压
        try:
            import rarfile
            return _extract_from_archive(
                rarfile.RarFile(io.BytesIO(content)), filelist,
            )
        except ImportError:
            pass
        except Exception:
            pass
        # 3) 尝试 zipfile 解压
        try:
            import zipfile
            return _extract_from_archive(
                zipfile.ZipFile(io.BytesIO(content)), filelist,
            )
        except Exception:
            pass
        # 4) 单文件字幕
        if archive_name.lower().endswith((".srt", ".ass", ".ssa")):
            return content, archive_name
        raise AssrtError(
            f"无法解压字幕文件: {archive_name}。"
            f"请安装 rarfile 库: pip install rarfile"
        )

    def validate_api_key(self) -> bool:
        """验证 Token：GET /v1/user/quota"""
        if not self.api_key:
            return False
        try:
            self._request("GET", "/v1/user/quota")
            return True
        except (AssrtError, Exception):
            return False


# ── 工具函数 ──────────────────────────────────────────────

def _get_error_message(status: int) -> str:
    errors = {
        1: "用户不存在",
        101: "搜索关键词长度必须大于3",
        20000: "请求缺少参数",
        20001: "Token 无效",
        20400: "API 终结点不存在",
        20900: "字幕不存在",
        30000: "服务器内部错误",
        30001: "数据库不可用",
        30002: "搜索引擎不可用",
        30300: "API 暂时不可用",
        30900: "配额超限",
    }
    return errors.get(status, f"未知错误 ({status})")


def _extract_from_archive(archive, filelist: list) -> tuple[bytes, str]:
    for entry in filelist:
        if not isinstance(entry, dict):
            continue
        fname = entry.get("f", "")
        if os.path.splitext(fname)[1].lower() not in (".srt", ".ass", ".ssa"):
            continue
        try:
            return archive.read(fname), fname
        except (KeyError, Exception):
            continue
    for name in archive.namelist():
        if os.path.splitext(name)[1].lower() in (".srt", ".ass", ".ssa"):
            return archive.read(name), os.path.basename(name)
    raise AssrtError("压缩包中未找到字幕文件 (.srt/.ass)")
