"""DownloadTask 和 TaskStatus 单元测试"""
import pytest
import time
from app.models.task import DownloadTask, TaskStatus, BatchProgress
from app.models.video import VideoFile
from app.models.subtitle import SubtitleInfo
from pathlib import Path


@pytest.fixture
def video():
    return VideoFile(path=Path("/movies/test.mp4"), file_size=1_000_000)


@pytest.fixture
def subtitle():
    return SubtitleInfo(provider="os", subtitle_id="1", language="zh", score=9.0)


@pytest.fixture
def task(video):
    return DownloadTask(video=video)


class TestTaskStatus:
    def test_from_string(self):
        assert TaskStatus.from_string("pending") == TaskStatus.PENDING
        assert TaskStatus.from_string("completed") == TaskStatus.COMPLETED
        assert TaskStatus.from_string("invalid") == TaskStatus.PENDING

    def test_display_name(self):
        assert TaskStatus.PENDING.display_name() == "等待中"
        assert TaskStatus.COMPLETED.display_name() == "已完成"

    def test_is_terminal(self):
        assert TaskStatus.COMPLETED.is_terminal()
        assert TaskStatus.FAILED.is_terminal()
        assert TaskStatus.CANCELLED.is_terminal()
        assert TaskStatus.SKIPPED.is_terminal()
        assert not TaskStatus.PENDING.is_terminal()
        assert not TaskStatus.DOWNLOADING.is_terminal()

    def test_is_active(self):
        assert TaskStatus.SEARCHING.is_active()
        assert TaskStatus.DOWNLOADING.is_active()
        assert not TaskStatus.PENDING.is_active()
        assert not TaskStatus.COMPLETED.is_active()


class TestTaskStatusTransitions:
    def test_valid_transitions(self):
        assert TaskStatus.PENDING.can_transition_to(TaskStatus.SEARCHING)
        assert TaskStatus.SEARCHING.can_transition_to(TaskStatus.DOWNLOADING)
        assert TaskStatus.DOWNLOADING.can_transition_to(TaskStatus.COMPLETED)

    def test_invalid_transitions(self):
        assert not TaskStatus.PENDING.can_transition_to(TaskStatus.PENDING)
        assert not TaskStatus.COMPLETED.can_transition_to(TaskStatus.PENDING)
        assert not TaskStatus.FAILED.can_transition_to(TaskStatus.SEARCHING)

    def test_skip_from_pending(self):
        assert TaskStatus.PENDING.can_transition_to(TaskStatus.SKIPPED)

    def test_cancel_anytime(self):
        assert TaskStatus.PENDING.can_transition_to(TaskStatus.CANCELLED)
        assert TaskStatus.SEARCHING.can_transition_to(TaskStatus.CANCELLED)
        assert TaskStatus.DOWNLOADING.can_transition_to(TaskStatus.CANCELLED)


class TestDownloadTask:
    def test_create(self, task):
        assert task.status == "pending"
        assert task.progress == 0
        assert task.created_at > 0
        assert task.elapsed_time == 0.0
        assert not task.is_done
        assert not task.is_running

    def test_start_search(self, task):
        task.start_search()
        assert task.status == "searching"
        assert task.started_at > 0
        assert task.is_running

    def test_start_download(self, task):
        task.start_search()
        task.start_download()
        assert task.status == "downloading"
        assert task.is_running

    def test_mark_completed(self, task):
        task.start_search()
        task.start_download()
        task.mark_completed()
        assert task.status == "completed"
        assert task.progress == 100
        assert task.completed_at > 0
        assert task.is_done

    def test_mark_failed(self, task):
        task.start_search()
        task.mark_failed("API 连接超时")
        assert task.status == "failed"
        assert task.error == "API 连接超时"
        assert task.is_done

    def test_mark_cancelled(self, task):
        task.start_search()
        task.mark_cancelled()
        assert task.status == "cancelled"
        assert task.is_done

    def test_mark_skipped(self, task):
        task.mark_skipped("语言不可用")
        assert task.status == "skipped"
        assert task.error == "语言不可用"

    def test_illegal_transition_raises(self, task):
        task.mark_completed()
        with pytest.raises(ValueError, match="非法状态转换"):
            task.start_search()

    def test_retry(self, task):
        task.start_search()
        task.mark_failed("临时错误")
        assert task.can_retry()
        task.retry()
        assert task.status == "pending"
        assert task.retry_count == 1
        assert task.progress == 0
        assert task.error == ""

    def test_max_retries(self, task):
        task.max_retries = 1
        task.start_search()
        task.mark_failed("错误")
        task.retry()
        task.start_search()
        task.mark_failed("再次错误")
        assert not task.can_retry()
        assert task.retry_count == 1

    def test_update_progress(self, task):
        task.start_search()
        task.start_download()
        task.update_progress(50)
        assert task.progress == 50
        assert not task.is_done
        task.update_progress(100)
        assert task.is_done
        assert task.status == "completed"

    def test_progress_clamping(self, task):
        task.start_search()
        task.start_download()
        task.update_progress(-10)
        assert task.progress == 0
        task.update_progress(150)
        assert task.status == "completed"

    def test_subtitle_advance(self, task):
        sub1 = SubtitleInfo(provider="t", subtitle_id="1", language="zh")
        sub2 = SubtitleInfo(provider="t", subtitle_id="2", language="en")
        task.subtitles = [sub1, sub2]
        task.total_subtitles = 2

        assert task.current_subtitle_index == 0
        assert task.current_subtitle == sub1

        assert task.advance_subtitle()
        assert task.current_subtitle_index == 1
        assert task.current_subtitle == sub2

        assert not task.advance_subtitle()

    def test_to_dict(self, task):
        d = task.to_dict()
        assert d["status"] == "pending"
        assert d["progress"] == 0
        assert d["retry_count"] == 0
        assert "video" in d
        assert d["video"]["file_name"] == "test.mp4"

    def test_str_repr(self, task):
        assert "等待中" in str(task)
        assert "DownloadTask" in repr(task)


class TestBatchProgress:
    def test_empty(self):
        bp = BatchProgress()
        assert bp.overall_progress == 100

    def test_from_tasks(self, video):
        from app.models.task import DownloadTask
        t1 = DownloadTask(video=video)
        t1.mark_completed()
        t2 = DownloadTask(video=video)
        t2.mark_failed("error")

        bp = BatchProgress.from_tasks([t1, t2])
        assert bp.total == 2
        assert bp.completed == 1
        assert bp.failed == 1
        assert bp.overall_progress == 100  # all terminal

    def test_summary(self):
        bp = BatchProgress(total=5, completed=3, failed=1)
        assert "共 5" in bp.summary
        assert "3 完成" in bp.summary
        assert "1 失败" in bp.summary
