"""VideoFile 数据模型单元测试"""
import pytest
from pathlib import Path
from app.models.video import VideoFile, SubtitleStatus, VIDEO_EXTENSIONS


class TestVideoFile:
    def test_create_minimal(self):
        """测试最小化创建"""
        v = VideoFile(path=Path("/movies/test.mp4"))
        assert v.file_name == "test.mp4"
        assert v.extension == ".mp4"
        assert v.subtitle_status == "missing"

    def test_create_with_string_path(self):
        """测试字符串路径"""
        v = VideoFile(path="/movies/test.mp4")
        assert isinstance(v.path, Path)
        assert v.file_name == "test.mp4"

    def test_create_with_exists_subtitle(self):
        """测试已有字幕状态"""
        v = VideoFile(path=Path("/movies/test.mp4"), has_subtitle=True)
        assert v.subtitle_status == "exists"

    def test_formatted_size(self):
        v = VideoFile(path=Path("a.mp4"), file_size=0)
        assert v.formatted_size == "未知"

        v = VideoFile(path=Path("a.mp4"), file_size=500)
        assert "B" in v.formatted_size

        v = VideoFile(path=Path("a.mp4"), file_size=2_000_000_000)
        assert "GB" in v.formatted_size

        v = VideoFile(path=Path("a.mp4"), file_size=5_000_000_000_000)
        assert "TB" in v.formatted_size

    def test_duration_str(self):
        v = VideoFile(path=Path("a.mp4"), duration=0)
        assert v.duration_str == "未知"

        v = VideoFile(path=Path("a.mp4"), duration=90)
        assert "m" in v.duration_str

        v = VideoFile(path=Path("a.mp4"), duration=3661)
        assert "h" in v.duration_str

    def test_resolution_and_quality(self):
        v = VideoFile(path=Path("a.mp4"), width=1920, height=1080)
        assert v.resolution == "1920x1080"
        assert v.quality_label == "1080P"

        v = VideoFile(path=Path("a.mp4"), width=0, height=0)
        assert v.resolution == ""
        assert v.quality_label == ""

    def test_quality_labels(self):
        cases = [
            (3840, 2160, "4K"),
            (2560, 1440, "2K"),
            (1920, 1080, "1080P"),
            (1280, 720, "720P"),
            (640, 480, "480P"),
            (320, 240, "SD"),
        ]
        for w, h, expected in cases:
            v = VideoFile(path=Path("a.mp4"), width=w, height=h)
            assert v.quality_label == expected

    def test_file_name_without_ext(self):
        v = VideoFile(path=Path("/dir/test.mkv"))
        assert v.file_name_without_ext == "test"

    def test_directory(self):
        import os
        v = VideoFile(path=Path("/dir/sub/test.mp4"))
        # Windows 使用反斜杠，POSIX 使用正斜杠
        expected = os.path.join("dir", "sub")
        assert v.directory.endswith(expected)

    def test_status_icon(self):
        mapping = {
            "missing": "⚠",
            "exists": "✓",
            "downloading": "⏳",
            "downloaded": "✅",
            "failed": "✗",
        }
        for status, icon in mapping.items():
            v = VideoFile(path=Path("a.mp4"), subtitle_status=status)
            assert v.status_icon == icon

    def test_is_video_file(self):
        assert VideoFile.is_video_file(Path("test.mp4"))
        assert VideoFile.is_video_file(Path("test.mkv"))
        assert not VideoFile.is_video_file(Path("test.txt"))
        assert not VideoFile.is_video_file(Path("test.srt"))

        # 边界
        assert VideoFile.is_video_file(Path("test.MP4"))  # 大写扩展名

    def test_is_subtitle_file(self):
        assert VideoFile.is_subtitle_file(Path("test.srt"))
        assert VideoFile.is_subtitle_file(Path("test.ass"))
        assert not VideoFile.is_subtitle_file(Path("test.mp4"))

    def test_find_matching_subtitles(self, tmp_path):
        """测试同名字幕查找"""
        video = tmp_path / "movie.mp4"
        video.write_text("fake video")

        # 创建匹配的字幕
        sub1 = tmp_path / "movie.srt"
        sub1.write_text("sub1")
        sub2 = tmp_path / "movie.chi.srt"
        sub2.write_text("sub2")
        # 不匹配的字幕
        sub3 = tmp_path / "other.srt"
        sub3.write_text("sub3")

        matches = VideoFile.find_matching_subtitles(video)
        assert len(matches) == 2
        assert sub1 in matches
        assert sub2 in matches
        assert sub3 not in matches

    def test_find_matching_subtitles_case_insensitive(self, tmp_path):
        """测试不区分大小写的匹配"""
        video = tmp_path / "Movie.2024.mp4"
        video.write_text("fake")
        sub = tmp_path / "movie.2024.srt"
        sub.write_text("sub")
        matches = VideoFile.find_matching_subtitles(video)
        assert len(matches) == 1

    def test_to_dict(self):
        v = VideoFile(
            path=Path("/movies/test.mp4"),
            file_name="test.mp4",
            extension=".mp4",
            file_size=1_500_000_000,
            duration=7260,
            width=1920,
            height=1080,
            subtitle_status="missing",
        )
        d = v.to_dict()
        assert d["file_name"] == "test.mp4"
        assert d["formatted_size"] == "1.4 GB"
        assert d["duration_str"] == "2h01m"
        assert d["resolution"] == "1920x1080"
        assert d["quality"] == "1080P"
        assert d["subtitle_status"] == "missing"

    def test_str_repr(self):
        v = VideoFile(path=Path("test.mp4"), file_size=1000)
        s = str(v)
        assert "test.mp4" in s
        r = repr(v)
        assert "VideoFile" in r
        assert "test.mp4" in r


class TestSubtitleStatus:
    def test_from_string(self):
        assert SubtitleStatus.from_string("missing") == SubtitleStatus.MISSING
        assert SubtitleStatus.from_string("unknown") == SubtitleStatus.UNKNOWN
        assert SubtitleStatus.from_string("invalid").value == "unknown"

    def test_display_name(self):
        assert SubtitleStatus.MISSING.display_name() == "缺失"
        assert SubtitleStatus.EXISTS.display_name() == "已存在"
