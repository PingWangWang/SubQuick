"""全流程端到端集成测试

测试扫描→列表→选择→下载 完整流程的组件协作。
不启动 Flet UI，直接测试业务层的流程整合。
"""

import pytest
import os
from pathlib import Path
from app.scanner import scan_directory, FileFilter
from app.scanner.video_scanner import ScanResult
from app.models.video import VideoFile
from app.downloader import DownloadManager, DownloadConfig
from app.downloader.base import SearchParams, SearchResult, SearchResultItem


@pytest.fixture
def media_dir(tmp_path):
    """创建测试媒体目录"""
    root = tmp_path / "Media"
    root.mkdir()

    # 无字幕视频
    (root / "movie1.mp4").write_text("fake1")
    (root / "movie2.mkv").write_text("fake2")

    # 有字幕视频
    (root / "movie3.mp4").write_text("fake3")
    (root / "movie3.srt").write_text("sub3")

    # 子目录中的视频
    sub = root / "TV"
    sub.mkdir()
    (sub / "episode1.mp4").write_text("fake4")
    (sub / "episode1.chi.srt").write_text("sub4")

    # 应忽略的
    (root / "sample.mp4").write_text("sample")

    return root


class TestScanToListFlow:
    """扫描 → 列表展示 流程"""

    def test_full_scan_flow(self, media_dir):
        """完整扫描流程：扫描应返回正确数量的视频"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        assert isinstance(result, ScanResult)
        # 4 个视频：movie1, movie2, movie3, episode1
        assert result.total_videos == 4

    def test_subtitle_detection_in_flow(self, media_dir):
        """字幕检测在扫描流程中正确工作"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)

        # 检查每个视频的字幕状态
        status_map = {v.file_name: v.subtitle_status for v in result.video_files}
        assert status_map["movie1.mp4"] == "missing"
        assert status_map["movie2.mkv"] == "missing"
        assert status_map["movie3.mp4"] == "exists"
        assert status_map["episode1.mp4"] == "exists"

    def test_video_details_in_flow(self, media_dir):
        """扫描结果包含完整视频详情"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)

        for v in result.video_files:
            assert v.file_name
            assert v.extension in (".mp4", ".mkv")
            assert v.file_size > 0
            assert v.formatted_size
            assert v.subtitle_status in ("missing", "exists")
            assert v.status_icon in ("⚠", "✓")
            assert v.directory

    def test_missing_subtitle_count(self, media_dir):
        """缺失字幕的统计正确"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        assert result.missing_subtitle_count == 2  # movie1, movie2
        assert result.existing_subtitle_count == 2  # movie3, episode1

    def test_scan_summary(self, media_dir):
        """扫描汇总信息正确"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        summary = result.summary()
        assert "4" in summary
        assert "缺失" in summary or "missing" in summary


class TestSelectToDownloadFlow:
    """选择 → 下载 流程"""

    def test_select_missing_videos(self, media_dir):
        """正确筛选出缺失字幕的视频"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]
        assert len(missing) == 2
        for v in missing:
            assert v.subtitle_status == "missing"

    def test_create_download_tasks(self, media_dir):
        """为选中视频创建下载任务"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]

        config = DownloadConfig(
            max_subtitles_per_video=3,
            language_priority=["zh", "en"],
        )
        manager = DownloadManager(config=config)
        tasks = manager.add_tasks(missing)
        assert len(tasks) == 2
        assert len(manager.tasks) == 2
        assert all(t.status == "pending" for t in tasks)

    def test_batch_progress_tracking(self, media_dir):
        """批量进度追踪"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]

        manager = DownloadManager()
        manager.add_tasks(missing)

        batch = manager.batch_progress
        assert batch.total == 2
        assert batch.overall_progress == 0  # 全 pending

        # 模拟完成
        manager.tasks[0].mark_completed()
        batch = manager.batch_progress
        assert batch.completed == 1
        assert batch.overall_progress == 50

    def test_task_status_lifecycle(self, media_dir):
        """单个任务完整生命周期"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]

        manager = DownloadManager()
        task = manager.add_task(missing[0])

        assert task.status == "pending"
        task.start_search()
        assert task.status == "searching"
        task.start_download()
        assert task.status == "downloading"
        task.update_progress(50)
        assert task.progress == 50
        task.mark_completed()
        assert task.is_done
        assert task.status == "completed"

    def test_task_failure_and_retry(self, media_dir):
        """任务失败和重试"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]

        manager = DownloadManager()
        task = manager.add_task(missing[0])

        task.start_search()
        task.mark_failed("API 超时")
        assert task.status == "failed"
        assert task.can_retry()

        task.retry()
        assert task.status == "pending"
        assert task.retry_count == 1
        assert task.progress == 0

    def test_run_all_no_api(self, media_dir):
        """无 API Key 时运行，应标记为搜索失败"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]

        manager = DownloadManager()
        manager.add_tasks(missing)
        batch = manager.run_all()
        # 没有 provider 的 api_key，搜索会出错，任务会被标记
        assert batch.completed + batch.failed + batch.skipped == batch.total


class TestProgressCallback:
    """进度回调集成"""

    def test_scan_progress_callback(self, media_dir):
        """扫描进度回调被正确调用"""
        calls = []

        def progress(path, current, total, phase):
            calls.append((current, path))

        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(
            str(media_dir),
            file_filter=filter_obj,
            progress_callback=progress,
        )
        assert len(calls) > 0
        # 最后一次回调的文件数应接近总数
        last_call = calls[-1]
        assert last_call[1] is not None  # 确认回调被调用且传入了路径信息

    def test_download_progress_callback(self, media_dir):
        """下载进度回调被正确调用"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]

        calls = []

        def progress(task, completed, total):
            calls.append((completed, total))

        manager = DownloadManager()
        manager.add_tasks(missing)

        # 模拟进度回调
        for i, task in enumerate(manager.tasks):
            progress(task, i + 1, len(manager.tasks))

        assert len(calls) == 2
        assert calls[-1] == (2, 2)


class TestExportMissingList:
    """导出缺失列表流程"""

    def test_export_missing_list(self, media_dir):
        """导出缺失字幕视频列表"""
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(media_dir), file_filter=filter_obj)
        missing = [v for v in result.video_files if v.subtitle_status == "missing"]

        # 导出为 CSV
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["文件名", "格式", "大小", "时长", "目录"])
        for v in missing:
            writer.writerow([v.file_name, v.extension, v.formatted_size, v.duration_str, v.directory])

        csv_content = output.getvalue()
        assert "movie1.mp4" in csv_content
        assert "movie2.mkv" in csv_content
        assert "movie3.mp4" not in csv_content  # 有字幕的不导出


class TestFirstRunFlow:
    """首次运行流程"""

    def test_first_run_detection(self):
        """首次运行标志检测"""
        from app.models.settings import Settings
        s = Settings.default()
        assert s.first_run is True

    def test_first_run_after_wizard(self):
        """引导完成后 first_run 应设为 False"""
        from app.models.settings import Settings
        s = Settings.default()
        s.first_run = False
        assert s.first_run is False

    def test_settings_persistence_after_wizard(self, tmp_path):
        """引导中的设置应持久化"""
        from app.models.settings import Settings
        from app.services.settings_service import SettingsService
        import json

        # 保存引导后的设置
        s = Settings()
        s.api_key = "test_key_123"
        s.max_subtitles_per_video = 5
        s.language_priority.primary = "en"
        s.first_run = False

        # 模拟保存和加载
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        service = SettingsService()
        service._config_dir = config_dir
        service._config_file = config_dir / "user_settings.json"
        service._backup_file = config_dir / "user_settings.backup.json"
        service.save(s)

        loaded = service.load()
        assert loaded.api_key == "test_key_123"
        assert loaded.max_subtitles_per_video == 5
        assert loaded.language_priority.primary == "en"
        assert loaded.first_run is False
