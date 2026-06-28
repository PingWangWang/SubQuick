"""OpenSubtitles.com API v2 适配器

通过 https://api.opensubtitles.com/api/v1/ 接口搜索和下载字幕。
"""

from __future__ import annotations

import hashlib
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


# 默认 API 地址
API_BASE_URL = "https://api.opensubtitles.com/api/v1"

# 用户代理
USER_AGENT = "SubQuick v1.0"

# API 限制：每分钟最多请求数
API_RATE_LIMIT = 10

# 请求重试配置
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 3.0, 5.0]


class OpenSubtitlesError(Exception):
    """OpenSubtitles API 错误"""
    pass


class OpenSubtitlesProvider(BaseProvider):
    """OpenSubtitles.com API v2 适配器"""

    def __init__(
        self,
        api_key: str = "",
        api_base: str = API_BASE_URL,
        user_agent: str = USER_AGENT,
        timeout: int = 30,
        proxy: Optional[dict] = None,
    ):
        super().__init__(api_key=api_key, timeout=timeout)
        self.api_base = api_base.rstrip("/")
        self.user_agent = user_agent
        self.proxy = proxy
        self._session: Optional[requests.Session] = None
        self._last_request_time: float = 0.0
        self._request_count: int = 0

    @property
    def provider_name(self) -> str:
        return "opensubtitles"

    def _get_session(self) -> requests.Session:
        """获取或创建 HTTP 会话"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            })
            if self.api_key:
                self._session.headers["Api-Key"] = self.api_key
        return self._session

    def _respect_rate_limit(self) -> None:
        """遵守 API 速率限制"""
        elapsed = time.time() - self._last_request_time
        min_interval = 60.0 / API_RATE_LIMIT
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """发送 HTTP 请求，含重试逻辑

        Args:
            method: HTTP 方法
            endpoint: API 端点（如 /subtitles）
            **kwargs: 传递给 requests 的参数

        Returns:
            JSON 响应字典

        Raises:
            OpenSubtitlesError: API 返回错误
            requests.RequestException: 网络错误
        """
        url = f"{self.api_base}{endpoint}"
        session = self._get_session()

        proxies = None
        if self.proxy:
            proxy_url = self.proxy.get("url", "")
            if proxy_url:
                proxies = {"http": proxy_url, "https": proxy_url}

        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                self._respect_rate_limit()
                response = session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    proxies=proxies,
                    **kwargs,
                )

                if response.status_code == 429:
                    # 速率限制，等待后重试
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    time.sleep(retry_after)
                    continue

                if response.status_code == 401:
                    raise OpenSubtitlesError("API Key 无效，请在设置中重新配置")

                if response.status_code == 403:
                    raise OpenSubtitlesError("API 访问被拒绝，请检查 API Key 权限")

                if response.status_code == 404:
                    return {}

                if response.status_code >= 500:
                    # 服务器错误，等待后重试
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                    raise OpenSubtitlesError(
                        f"服务器错误 ({response.status_code})"
                    )

                response.raise_for_status()
                return response.json()

            except requests.Timeout as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                raise OpenSubtitlesError(f"请求超时: {url}") from e

            except requests.ConnectionError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                raise OpenSubtitlesError(f"连接失败: {url}") from e

            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                raise OpenSubtitlesError(f"请求失败: {e}") from e

        raise OpenSubtitlesError(f"请求失败（已重试 {MAX_RETRIES} 次）") from last_error

    def search(self, params: SearchParams) -> SearchResult:
        """搜索字幕

        API: POST /api/v1/subtitles

        Args:
            params: 搜索参数

        Returns:
            搜索结果
        """
        if not params.is_valid:
            return SearchResult(
                provider=self.provider_name,
                error="搜索参数无效：至少需要文件名或 hash",
            )

        # 构建查询参数
        query_params: dict = {
            "languages": ",".join(params.languages) if params.languages else "en",
            "order_by": "download_count",
            "order_direction": "desc",
            "limit": params.max_count,
        }

        if params.query:
            query_params["query"] = params.query
        elif params.file_name:
            # 使用文件名（不含扩展名）作为搜索词
            name_without_ext = os.path.splitext(params.file_name)[0]
            query_params["query"] = name_without_ext

        if params.imdb_id:
            query_params["imdb_id"] = params.imdb_id

        if params.file_hash and params.file_size > 0:
            query_params["moviehash"] = params.file_hash
            query_params["moviebytesize"] = str(params.file_size)

        if params.season > 0:
            query_params["season_number"] = params.season
        if params.episode > 0:
            query_params["episode_number"] = params.episode

        try:
            data = self._request("GET", "/subtitles", params=query_params)
        except OpenSubtitlesError as e:
            return SearchResult(
                provider=self.provider_name,
                error=str(e),
            )

        # 解析响应
        items: list[SearchResultItem] = []
        total_count = 0

        try:
            total_count = data.get("total_count", 0)
            subtitle_data = data.get("data", [])

            for item in subtitle_data:
                attributes = item.get("attributes", {})
                features = attributes.get("feature_details", {}) or {}

                # 提取语言代码
                lang_info = attributes.get("language", {}) or {}
                language = lang_info.get("language_code", "")

                # 提取文件信息
                files = attributes.get("files", []) or []
                file_info = files[0] if files else {}

                # 计算评分（综合多个因素）
                score = _calculate_score(
                    attributes=attributes,
                    features=features,
                )

                result_item = SearchResultItem(
                    subtitle_id=str(item.get("id", "")),
                    language=language,
                    file_name=file_info.get("file_name", ""),
                    score=score,
                    download_url="",
                    uploader=attributes.get("uploader", {}).get("name", "")
                    if isinstance(attributes.get("uploader"), dict) else "",
                    upload_date=attributes.get("upload_date", ""),
                    downloads_count=attributes.get("download_count", 0),
                    format=file_info.get("file_format", ""),
                    fps=str(features.get("fps", "")),
                    cds=attributes.get("subtitles_count", 1),
                    hearing_impaired=attributes.get("hearing_impaired", False),
                    raw_data=item,
                )
                items.append(result_item)

        except (KeyError, TypeError, ValueError) as e:
            return SearchResult(
                provider=self.provider_name,
                items=items,
                total_count=total_count,
                error=f"解析响应失败: {e}",
            )

        return SearchResult(
            provider=self.provider_name,
            items=items,
            total_count=total_count,
        )

    def download(self, subtitle_id: str) -> tuple[bytes, str]:
        """下载字幕文件

        API: POST /api/v1/download

        Args:
            subtitle_id: 字幕 ID

        Returns:
            (文件内容 bytes, 推荐文件名)

        Raises:
            OpenSubtitlesError: 下载失败
        """
        try:
            data = self._request(
                "POST",
                "/download",
                json={"file_id": int(subtitle_id)},
            )
        except (ValueError, OpenSubtitlesError) as e:
            raise OpenSubtitlesError(f"下载失败: {e}")

        # 获取下载链接
        link = data.get("link", "")
        file_name = data.get("file_name", f"subtitle_{subtitle_id}.srt")

        if not link:
            raise OpenSubtitlesError(f"未获取到下载链接 (ID: {subtitle_id})")

        # 下载文件内容
        try:
            session = self._get_session()
            file_response = session.get(link, timeout=self.timeout)
            file_response.raise_for_status()
            content = file_response.content
        except requests.RequestException as e:
            raise OpenSubtitlesError(f"下载字幕文件失败: {e}")

        if not content:
            raise OpenSubtitlesError("下载的文件内容为空")

        return content, file_name

    def validate_api_key(self) -> bool:
        """验证 API Key

        通过获取用户信息接口验证 Key 有效性。

        Returns:
            True 有效, False 无效
        """
        if not self.api_key:
            return False
        try:
            data = self._request("GET", "/user/info")
            return "data" in data
        except (OpenSubtitlesError, Exception):
            return False


def _calculate_score(attributes: dict, features: dict) -> float:
    """计算字幕的综合评分（0-10）

    考虑因素：
    - 下载次数
    - 上传者评分
    - 字幕格式（SRT 加分）
    - 是否有听力障碍标记（减分，除非用户偏好）
    - 上传天数（越新越高）

    Args:
        attributes: 字幕属性字典
        features: 视频特征字典

    Returns:
        0-10 的评分
    """
    score = 5.0  # 基础分

    # 下载次数（每1000次+1分，上限+3分）
    downloads = attributes.get("download_count", 0)
    if isinstance(downloads, (int, float)):
        score += min(downloads / 1000, 3.0)

    # 上传天数（30天内+1分，7天内+2分）
    upload_date = attributes.get("upload_date", "")
    if upload_date:
        try:
            from datetime import datetime
            uploaded = datetime.fromisoformat(upload_date.replace("Z", "+00:00"))
            days_ago = (datetime.now().astimezone() - uploaded).days
            if days_ago < 7:
                score += 2.0
            elif days_ago < 30:
                score += 1.0
        except Exception:
            pass

    # 格式加分（SRT 最通用）
    files = attributes.get("files", []) or []
    for f in files:
        fmt = (f.get("file_format") or "").lower()
        if fmt == "srt":
            score += 0.5
            break
        elif fmt == "ass":
            score += 0.3

    # 封顶
    return min(score, 10.0)
