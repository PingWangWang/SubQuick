"""字幕下载器抽象基类"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """字幕源提供者基类，所有字幕源适配器需实现此接口。"""

    @abstractmethod
    def search(self, query: str, languages: list[str]) -> list[dict]:
        ...

    @abstractmethod
    def download(self, subtitle_id: str) -> bytes:
        ...
