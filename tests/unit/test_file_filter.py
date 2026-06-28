"""FileFilter 单元测试"""
import pytest
from pathlib import Path
from app.scanner.file_filter import (
    FileFilter,
    is_supported_format,
    is_excluded_directory,
    matches_ignore_pattern,
    matches_ignore_directory,
)


class TestIsSupportedFormat:
    def test_supported_formats(self):
        assert is_supported_format(Path("test.mp4"))
        assert is_supported_format(Path("test.mkv"))
        assert is_supported_format(Path("test.MP4"))  # 大写

    def test_unsupported_format(self):
        assert not is_supported_format(Path("test.txt"))
        assert not is_supported_format(Path("test.pdf"))

    def test_custom_formats(self):
        assert is_supported_format(Path("test.mp4"), ["mp4"])
        assert not is_supported_format(Path("test.mkv"), ["mp4"])


class TestIsExcludedDirectory:
    def test_hidden_directories(self):
        assert is_excluded_directory(Path(".git"))
        assert is_excluded_directory(Path(".venv"))
        assert is_excluded_directory(Path("__pycache__"))

    def test_normal_directories(self):
        assert not is_excluded_directory(Path("Movies"))
        assert not is_excluded_directory(Path("TV Shows"))

    def test_system_directories(self):
        assert is_excluded_directory(Path("$Recycle.Bin"))
        assert is_excluded_directory(Path("System Volume Information"))


class TestMatchesIgnorePattern:
    def test_sample_pattern(self):
        assert matches_ignore_pattern("sample.mp4", ["*sample*"])
        assert matches_ignore_pattern("test_sample.mp4", ["*sample*"])
        assert not matches_ignore_pattern("movie.mp4", ["*sample*"])

    def test_trailer_pattern(self):
        assert matches_ignore_pattern("trailer.mp4", ["*trailer*"])
        assert not matches_ignore_pattern("movie.mp4", ["*trailer*"])

    def test_case_insensitive(self):
        assert matches_ignore_pattern("Sample.MP4", ["*sample*"])

    def test_multiple_patterns(self):
        patterns = ["*sample*", "*trailer*", "*_unpack"]
        assert matches_ignore_pattern("sample.mp4", patterns)
        assert matches_ignore_pattern("trailer.mkv", patterns)
        assert matches_ignore_pattern("test_unpack", patterns)
        assert not matches_ignore_pattern("movie.mp4", patterns)


class TestMatchesIgnoreDirectory:
    def test_matches_path(self):
        assert matches_ignore_directory(
            Path("D:/Movies/Samples/test.mp4"),
            ["D:/Movies/Samples"],
        )

    def test_no_match(self):
        assert not matches_ignore_directory(
            Path("D:/Movies/Main/test.mp4"),
            ["D:/Movies/Samples"],
        )


class TestFileFilter:
    @pytest.fixture
    def filter_obj(self):
        return FileFilter(
            video_formats=["mp4", "mkv"],
            ignore_patterns=["*sample*"],
            ignore_directories=["/samples"],
        )

    def test_is_video_file(self, tmp_path, filter_obj):
        video = tmp_path / "movie.mp4"
        video.write_text("fake")
        assert filter_obj.is_video_file(video)

    def test_non_video_file(self, tmp_path, filter_obj):
        txt = tmp_path / "notes.txt"
        txt.write_text("text")
        assert not filter_obj.is_video_file(txt)

    def test_ignored_pattern(self, tmp_path, filter_obj):
        video = tmp_path / "sample.mp4"
        video.write_text("fake")
        assert not filter_obj.is_video_file(video)

    def test_ignored_directory(self, tmp_path, filter_obj):
        """忽略目录的路径需要是实际系统路径才能匹配"""
        # 创建实际被忽略的目录并生成文件
        ignore_dir = tmp_path / "samples"
        ignore_dir.mkdir()
        video = ignore_dir / "movie.mp4"
        video.write_text("fake")

        # 使用实际路径更新过滤器
        filter_with_real_path = FileFilter(
            video_formats=["mp4", "mkv"],
            ignore_patterns=["*sample*"],
            ignore_directories=[str(ignore_dir)],
        )
        assert not filter_with_real_path.is_video_file(video)

    def test_should_scan_directory(self, tmp_path, filter_obj):
        assert filter_obj.should_scan_directory(tmp_path)
        assert not filter_obj.should_scan_directory(tmp_path / ".git")
        assert not filter_obj.should_scan_directory(tmp_path / "__pycache__")

    def test_repr(self, filter_obj):
        r = repr(filter_obj)
        assert "FileFilter" in r
        assert "mp4" in r
