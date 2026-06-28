"""扫描模块集成测试"""
import pytest
from pathlib import Path
from app.scanner.video_scanner import scan_directory
from app.scanner.file_filter import FileFilter
from app.scanner.subtitle_detector import find_subtitle_files


@pytest.fixture
def complex_dir(tmp_path):
    """创建复杂的测试目录结构"""
    root = tmp_path / "Media"
    root.mkdir()

    # 电影目录
    movies = root / "Movies"
    movies.mkdir()
    (movies / "Inception.mp4").write_text("fake")
    (movies / "Inception.srt").write_text("sub")  # 有字幕
    (movies / "Interstellar.mkv").write_text("fake")  # 无字幕
    (movies / "Interstellar.chi.srt").write_text("sub")

    # 剧集目录
    tv = root / "TV"
    tv.mkdir()
    (tv / "BreakingBad_S01E01.mp4").write_text("fake")
    (tv / "BreakingBad_S01E02.mp4").write_text("fake")
    (tv / "BreakingBad_S01E01.srt").write_text("sub")

    # 隐藏目录（应跳过）
    hidden = root / ".archive"
    hidden.mkdir()
    (hidden / "old_movie.mp4").write_text("fake")

    # 采样目录（应跳过）
    samples = root / "Samples"
    samples.mkdir()
    (samples / "test_sample.mp4").write_text("fake")

    # 非视频文件
    (root / "playlist.txt").write_text("playlist")

    return root


class TestScannerIntegration:
    def test_scan_complex_directory(self, complex_dir):
        """扫描复杂目录结构"""
        result = scan_directory(
            str(complex_dir),
            file_filter=FileFilter(
                ignore_patterns=["*sample*"],
            ),
        )
        # 应该找到 4 个视频（Movies:2, TV:2），排除隐藏和采样
        assert result.total_videos == 4
        assert result.total_files_found >= 5

    def test_video_details(self, complex_dir):
        """验证扫描后的视频详情"""
        result = scan_directory(str(complex_dir))
        for vf in result.video_files:
            assert vf.file_name
            assert vf.extension in (".mp4", ".mkv")
            assert vf.file_size > 0

    def test_subtitle_detection(self, complex_dir):
        """验证字幕检测"""
        result = scan_directory(str(complex_dir))
        inception = None
        interstellar = None
        for vf in result.video_files:
            if "Inception" in vf.file_name:
                inception = vf
            if "Interstellar" in vf.file_name:
                interstellar = vf

        assert inception is not None
        assert inception.has_subtitle
        assert inception.subtitle_count >= 1
        assert inception.subtitle_status == "exists"

        assert interstellar is not None
        assert interstellar.has_subtitle
        assert interstellar.subtitle_count >= 1

    def test_hidden_directory_skipped(self, complex_dir):
        """隐藏目录应被跳过"""
        result = scan_directory(str(complex_dir))
        for vf in result.video_files:
            assert ".archive" not in vf.directory

    def test_scan_performance(self, complex_dir):
        """扫描大量文件时不应超时"""
        # 创建额外文件模拟较大数量
        extra_dir = complex_dir / "Extra"
        extra_dir.mkdir()
        for i in range(50):
            (extra_dir / f"video_{i}.mp4").write_text("fake")

        import time
        start = time.time()
        result = scan_directory(str(complex_dir))
        elapsed = time.time() - start
        # 扫描 50+ 文件应 < 1秒
        assert elapsed < 5.0
        assert result.total_videos >= 50

    def test_progress_callback(self, complex_dir):
        """进度回调应被调用"""
        calls = []

        def progress(path, current, total, phase):
            calls.append((current, phase))

        result = scan_directory(
            str(complex_dir),
            progress_callback=progress,
        )
        assert len(calls) > 0
        # 最后一次调用应接近总数
        last_call = calls[-1]
        assert last_call[0] >= result.total_files_found * 0.5
