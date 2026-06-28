"""下载模块集成测试（mock API）"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.downloader.base import SearchParams, SearchResult, SearchResultItem
from app.downloader.opensubtitles import OpenSubtitlesProvider, OpenSubtitlesError
from app.downloader.manager import DownloadManager, DownloadConfig
from app.models.video import VideoFile


class TestOpenSubtitlesProvider:
    @pytest.fixture
    def provider(self):
        return OpenSubtitlesProvider(api_key="test_key")

    def test_provider_name(self, provider):
        assert provider.provider_name == "opensubtitles"

    def test_search_invalid_params(self, provider):
        params = SearchParams()
        result = provider.search(params)
        assert not result.is_success
        assert "无效" in result.error

    def test_validate_api_key_empty(self):
        provider = OpenSubtitlesProvider(api_key="")
        assert not provider.validate_api_key()

    def test_rate_limit_respected(self, provider):
        """确认速率限制逻辑存在"""
        import time
        t1 = time.time()
        provider._respect_rate_limit()
        t2 = time.time()
        elapsed = t2 - t1
        # 首次调用不应等待
        assert elapsed < 0.5


class TestDownloadManager:
    @pytest.fixture
    def manager(self):
        return DownloadManager(
            config=DownloadConfig(
                max_concurrent=3,
                max_subtitles_per_video=3,
                language_priority=["zh", "en"],
            ),
        )

    @pytest.fixture
    def video(self):
        return VideoFile(
            path=Path("/movies/test.mp4"),
            file_name="test.mp4",
            file_size=1_000_000,
        )

    def test_add_task(self, manager, video):
        task = manager.add_task(video)
        assert task.video.file_name == "test.mp4"
        assert len(manager.tasks) == 1

    def test_add_tasks(self, manager):
        videos = [
            VideoFile(path=Path(f"/movies/v{i}.mp4"), file_name=f"v{i}.mp4")
            for i in range(3)
        ]
        tasks = manager.add_tasks(videos)
        assert len(tasks) == 3
        assert len(manager.tasks) == 3

    def test_batch_progress_empty(self, manager):
        bp = manager.batch_progress
        assert bp.total == 0

    def test_batch_progress_with_tasks(self, manager, video):
        manager.add_task(video)
        manager.tasks[0].mark_completed()
        bp = manager.batch_progress
        assert bp.total == 1
        assert bp.completed == 1

    def test_cancel_all(self, manager, video):
        manager.add_task(video)
        manager.cancel_all()
        assert manager.tasks[0].status == "cancelled"

    def test_clear_tasks(self, manager, video):
        manager.add_task(video)
        manager.clear_tasks()
        assert len(manager.tasks) == 0

    def test_run_all_no_tasks(self, manager):
        bp = manager.run_all()
        assert bp.total == 0
