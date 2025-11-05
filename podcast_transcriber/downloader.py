"""
Module for downloading podcast audio files using robust gPodder downloader
"""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote
import sys

# Import the robust downloader from podcast_downloader module
sys.path.insert(0, str(Path(__file__).parent.parent))
from podcast_downloader import PodcastDownloader as RobustDownloader, DownloadError


class PodcastDownloader:
    """Downloads podcast audio files with retry and resume capability"""

    def __init__(self, download_dir: str = "downloads"):
        """
        Initialize the downloader

        Args:
            download_dir: Directory to save downloaded files
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Initialize the robust downloader with sensible defaults
        self.robust_downloader = RobustDownloader(
            user_agent='PodcastTranscriber/1.0 (Whisper AI Transcription)',
            max_retries=3,
            timeout=60
        )

    def download(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Download an audio file from URL with retry and resume capability

        Args:
            url: URL of the audio file
            filename: Optional custom filename

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Generate filename if not provided
            if not filename:
                parsed_url = urlparse(url)
                filename = unquote(os.path.basename(parsed_url.path))
                if not filename or '.' not in filename:
                    filename = "episode.mp3"

            # Ensure we have a proper extension
            if not any(filename.endswith(ext) for ext in ['.mp3', '.m4a', '.wav', '.ogg']):
                filename += '.mp3'

            filepath = self.download_dir / filename

            # Check if file already exists and is complete
            if filepath.exists():
                # Let the robust downloader handle resume if file is incomplete
                print(f"File exists: {filepath}")
                print("Checking if download is complete or needs resume...")

            print(f"Downloading from: {url}")
            print(f"Saving to: {filepath}")

            # Progress callback
            def progress_callback(count, block_size, total_size):
                if total_size > 0:
                    downloaded = count * block_size
                    progress = min(100.0, 100.0 * downloaded / total_size)
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    print(f'\rProgress: {progress:5.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)', end='', flush=True)

            # Use the robust downloader
            headers, real_url = self.robust_downloader.download(
                url=url,
                filename=str(filepath),
                progress_callback=progress_callback
            )

            print("\nDownload complete!")
            return str(filepath)

        except DownloadError as e:
            print(f"Download error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def get_file_size(self, filepath: str) -> str:
        """
        Get human-readable file size

        Args:
            filepath: Path to file

        Returns:
            Formatted file size string
        """
        size_bytes = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
