"""pytest 共享 fixtures 和配置"""
import pytest
from pathlib import Path
from app.models.video import VideoFile
from app.models.subtitle import SubtitleInfo


@pytest.fixture
def sample_video() -> VideoFile:
    """返回一个示例视频文件"""
    return VideoFile(
        path=Path("/movies/test_movie.mp4"),
        file_name="test_movie.mp4",
        extension=".mp4",
        file_size=1_500_000_000,
        duration=7260,
        width=1920,
        height=1080,
        subtitle_status="missing",
    )


@pytest.fixture
def sample_subtitle_zh() -> SubtitleInfo:
    """返回一个中文字幕示例"""
    return SubtitleInfo(
        provider="opensubtitles",
        subtitle_id="123456",
        language="zh",
        file_name="test_movie.chi.srt",
        score=9.2,
    )


@pytest.fixture
def sample_subtitle_en() -> SubtitleInfo:
    """返回一个英文字幕示例"""
    return SubtitleInfo(
        provider="opensubtitles",
        subtitle_id="789012",
        language="en",
        file_name="test_movie.eng.srt",
        score=8.5,
    )
