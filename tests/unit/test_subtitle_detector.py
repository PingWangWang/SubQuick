"""SubtitleDetector 单元测试"""
import pytest
from pathlib import Path
from app.scanner.subtitle_detector import (
    find_subtitle_files,
    has_subtitle,
    count_subtitles,
    get_subtitle_filenames,
    detect_subtitles_for_videos,
)


@pytest.fixture
def video_dir(tmp_path):
    """创建带视频和字幕的测试目录"""
    # 视频文件
    video = tmp_path / "movie.mp4"
    video.write_text("fake video")
    # 匹配的字幕
    sub1 = tmp_path / "movie.srt"
    sub1.write_text("sub1")
    sub2 = tmp_path / "movie.chi.srt"
    sub2.write_text("sub2")
    sub3 = tmp_path / "movie.eng.srt"
    sub3.write_text("sub3")
    # 不匹配的字幕
    sub4 = tmp_path / "other.srt"
    sub4.write_text("sub4")
    # 非字幕文件
    txt = tmp_path / "movie.txt"
    txt.write_text("text")
    return tmp_path, video


class TestFindSubtitleFiles:
    def test_find_exact_match(self, video_dir):
        d, video = video_dir
        subs = find_subtitle_files(video)
        assert len(subs) >= 1
        assert (d / "movie.srt") in subs

    def test_find_language_suffix(self, video_dir):
        d, video = video_dir
        subs = find_subtitle_files(video)
        assert (d / "movie.chi.srt") in subs
        assert (d / "movie.eng.srt") in subs

    def test_exclude_non_matching(self, video_dir):
        d, video = video_dir
        subs = find_subtitle_files(video)
        assert (d / "other.srt") not in subs
        assert (d / "movie.txt") not in subs

    def test_no_subtitles(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        assert find_subtitle_files(video) == []

    def test_nonexistent_dir(self, tmp_path):
        video = tmp_path / "video.mp4"
        assert find_subtitle_files(video, search_dir=tmp_path / "nonexistent") == []

    def test_case_insensitive(self, tmp_path):
        video = tmp_path / "Movie.Name.mp4"
        video.write_text("fake")
        sub = tmp_path / "movie.name.srt"
        sub.write_text("sub")
        assert len(find_subtitle_files(video)) == 1

    def test_dash_separator(self, tmp_path):
        video = tmp_path / "my movie.mp4"
        video.write_text("fake")
        sub = tmp_path / "my movie-chi.srt"
        sub.write_text("sub")
        assert len(find_subtitle_files(video)) == 1


class TestHasSubtitle:
    def test_has_subtitle(self, video_dir):
        _, video = video_dir
        assert has_subtitle(video)

    def test_no_subtitle(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        assert not has_subtitle(video)


class TestCountSubtitles:
    def test_count(self, video_dir):
        _, video = video_dir
        assert count_subtitles(video) >= 3

    def test_count_zero(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        assert count_subtitles(video) == 0


class TestGetSubtitleFilenames:
    def test_filenames(self, video_dir):
        d, video = video_dir
        names = get_subtitle_filenames(video)
        assert "movie.srt" in names
        assert "movie.chi.srt" in names
        assert "other.srt" not in names


class TestDetectSubtitlesForVideos:
    def test_multiple_videos(self, tmp_path):
        v1 = tmp_path / "movie1.mp4"
        v1.write_text("fake")
        v2 = tmp_path / "movie2.mp4"
        v2.write_text("fake")
        s1 = tmp_path / "movie1.srt"
        s1.write_text("sub")

        result = detect_subtitles_for_videos([v1, v2])
        assert len(result[v1]) == 1
        assert len(result[v2]) == 0
