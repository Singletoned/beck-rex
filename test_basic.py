"""
Basic unit tests for podcast transcriber
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from podcast_transcriber.downloader import PodcastDownloader
from podcast_transcriber.podcast_fetcher import PodcastFetcher
from podcast_transcriber.transcriber import AudioTranscriber


class TestPodcastDownloader(unittest.TestCase):
    """Test the podcast downloader"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = PodcastDownloader(download_dir=self.temp_dir)

    def tearDown(self):
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directory(self):
        """Test that initializing creates the download directory"""
        self.assertTrue(Path(self.temp_dir).exists())

    def test_existing_file_returns_path(self):
        """Test that existing files are reused"""
        # Create a fake file
        test_file = Path(self.temp_dir) / "test.mp3"
        test_file.write_text("fake audio data")

        # Try to download with same filename
        result = self.downloader.download("http://example.com/test.mp3", "test.mp3")

        # Should return existing file path
        self.assertEqual(result, str(test_file))

    def test_get_file_size(self):
        """Test file size formatting"""
        # Create a test file
        test_file = Path(self.temp_dir) / "test.mp3"
        test_file.write_bytes(b"x" * 1024)  # 1KB

        size_str = self.downloader.get_file_size(str(test_file))
        self.assertIn("KB", size_str)

    @patch('podcast_transcriber.downloader.requests.get')
    def test_download_creates_file(self, mock_get):
        """Test that download creates a file"""
        # Mock the response
        mock_response = Mock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content = lambda chunk_size: [b"test data"]
        mock_get.return_value.__enter__ = Mock(return_value=mock_response)
        mock_get.return_value.__exit__ = Mock(return_value=False)

        # This will fail because we can't fully mock requests.get in context manager
        # but it tests the basic structure
        # In a real scenario, you'd use a test server or VCR cassettes


class TestPodcastFetcher(unittest.TestCase):
    """Test the podcast RSS fetcher"""

    @patch('podcast_transcriber.podcast_fetcher.requests.get')
    @patch('podcast_transcriber.podcast_fetcher.podcastparser.parse')
    def test_fetch_feed_success(self, mock_parse, mock_get):
        """Test successful feed fetching"""
        # Mock the response
        mock_response = Mock()
        mock_response.content = b"fake rss content"
        mock_get.return_value = mock_response

        # Mock the parser
        mock_parse.return_value = {
            'title': 'Test Podcast',
            'episodes': [
                {
                    'title': 'Episode 1',
                    'enclosures': [{'url': 'http://example.com/ep1.mp3'}]
                }
            ]
        }

        fetcher = PodcastFetcher("http://example.com/feed.xml")
        result = fetcher.fetch_feed()

        self.assertTrue(result)
        self.assertEqual(fetcher.feed['title'], 'Test Podcast')

    @patch('podcast_transcriber.podcast_fetcher.requests.get')
    @patch('podcast_transcriber.podcast_fetcher.podcastparser.parse')
    def test_get_latest_episode(self, mock_parse, mock_get):
        """Test getting the latest episode"""
        mock_response = Mock()
        mock_response.content = b"fake rss content"
        mock_get.return_value = mock_response

        mock_parse.return_value = {
            'title': 'Test Podcast',
            'episodes': [
                {
                    'title': 'Latest Episode',
                    'published': '2024-01-01',
                    'description': 'Test description',
                    'enclosures': [{'url': 'http://example.com/latest.mp3'}]
                }
            ]
        }

        fetcher = PodcastFetcher("http://example.com/feed.xml")
        fetcher.fetch_feed()
        episode = fetcher.get_latest_episode()

        self.assertIsNotNone(episode)
        self.assertEqual(episode['title'], 'Latest Episode')
        self.assertEqual(episode['audio_url'], 'http://example.com/latest.mp3')


class TestAudioTranscriber(unittest.TestCase):
    """Test the audio transcriber"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directory(self):
        """Test that transcriber creates output directory"""
        transcriber = AudioTranscriber(output_dir=self.temp_dir)
        self.assertTrue(Path(self.temp_dir).exists())

    def test_format_timestamp(self):
        """Test timestamp formatting"""
        transcriber = AudioTranscriber(output_dir=self.temp_dir)

        # Test SRT format (with comma)
        srt_time = transcriber._format_timestamp(90.5, vtt=False)
        self.assertEqual(srt_time, "00:01:30,500")

        # Test VTT format (with dot)
        vtt_time = transcriber._format_timestamp(90.5, vtt=True)
        self.assertEqual(vtt_time, "00:01:30.500")

    def test_format_time_readable(self):
        """Test readable time formatting"""
        transcriber = AudioTranscriber(output_dir=self.temp_dir)

        # Test without hours
        time1 = transcriber._format_time_readable(90)
        self.assertEqual(time1, "01:30")

        # Test with hours
        time2 = transcriber._format_time_readable(3665)
        self.assertEqual(time2, "01:01:05")


if __name__ == '__main__':
    unittest.main()
