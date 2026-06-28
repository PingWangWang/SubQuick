"""VideoScanner 单元测试"""
import pytest
from pathlib import Path
from app.scanner.video_scanner import scan_directory, ScanResult, ScanCancelled
from app.scanner.file_filter import FileFilter


@pytest.fixture
def movie_dir(tmp_path):
    """创建测试用的电影目录结构"""
    # 根目录
    root = tmp_path / "Movies"
    root.mkdir()

    # 主目录
    main = root / "Main"
    main.mkdir()
    v1 = main / "Movie1.mp4"
    v1.write_text("fake1")
    v2 = main / "Movie2.mkv"
    v2.write_text("fake2")

    # 子目录
    sub = root / "Sub"
    sub.mkdir()
    v3 = sub / "Series_S01E01.mp4"
    v3.write_text("fake3")
    # 带字幕的
    s3 = sub / "Series_S01E01.srt"
    s3.write_text("sub3")

    # 应忽略的
    samples = root / "Samples"
    samples.mkdir()
    v4 = samples / "sample.mp4"
    v4.write_text("sample")

    # 非视频文件
    txt = main / "notes.txt"
    txt.write_text("text")

    return root, [v1, v2, v3], [v4]


class TestScanDirectory:
    def test_scan_all(self, movie_dir):
        root, expected, _ = movie_dir
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(root), file_filter=filter_obj)
        assert isinstance(result, ScanResult)
        assert result.total_videos == 3
        assert result.total_files_found >= 4

    def test_scan_with_ignored_files(self, movie_dir):
        root, expected, ignored = movie_dir
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(root), file_filter=filter_obj)
        result_paths = [str(v.path) for v in result.video_files]
        for ig in ignored:
            assert str(ig) not in result_paths

    def test_scan_subtitle_detection(self, movie_dir):
        root, expected, _ = movie_dir
        result = scan_directory(str(root))
        for vf in result.video_files:
            if "Series_S01E01" in vf.file_name:
                assert vf.has_subtitle
                assert vf.subtitle_status == "exists"
                assert vf.subtitle_count == 1
            else:
                assert not vf.has_subtitle
                assert vf.subtitle_status == "missing"

    def test_non_recursive(self, movie_dir):
        root, expected, _ = movie_dir
        result = scan_directory(str(root), recursive=False)
        # 非递归只扫根目录，Movies 下没有直接视频文件
        assert result.total_videos == 0

    def test_nonexistent_directory(self):
        with pytest.raises(FileNotFoundError):
            scan_directory("/nonexistent/path")

    def test_custom_file_filter(self, movie_dir):
        root, expected, _ = movie_dir
        # 只接受 MKV
        filter_obj = FileFilter(video_formats=["mkv"])
        result = scan_directory(str(root), file_filter=filter_obj)
        assert result.total_videos == 1
        assert all(v.extension == ".mkv" for v in result.video_files)

    def test_cancel_flag(self, movie_dir):
        root, expected, _ = movie_dir
        cancelled = False

        def cancel_check():
            return cancelled

        # 先扫描获取正常结果
        result = scan_directory(
            str(root), cancel_flag=cancel_check
        )
        assert result.total_videos > 0


class TestScanResult:
    def test_summary(self):
        result = ScanResult(
            total_files_found=100,
            video_files=[],
            scan_duration=5.0,
        )
        s = result.summary()
        assert "100" in s
        assert "5.0" in s

    def test_missing_count(self, movie_dir):
        root, expected, _ = movie_dir
        filter_obj = FileFilter(ignore_patterns=["*sample*"])
        result = scan_directory(str(root), file_filter=filter_obj)
        assert result.missing_subtitle_count == 2  # Movie1, Movie2
        assert result.existing_subtitle_count == 1  # Series_S01E01
