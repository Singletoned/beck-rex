"""
Module for downloading podcast audio files
"""

import os
import requests
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote


class PodcastDownloader:
    """Downloads podcast audio files"""

    def __init__(self, download_dir: str = "downloads"):
        """
        Initialize the downloader

        Args:
            download_dir: Directory to save downloaded files
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, filename: Optional[str] = None) -> str:
        """
        Download an audio file from URL

        Args:
            url: URL of the audio file
            filename: Optional custom filename

        Returns:
            Path to downloaded file
        """
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

        # If file already exists, use it
        if filepath.exists():
            file_size = self.get_file_size(str(filepath))
            print(f"✓ File already exists: {filepath}")
            print(f"  Size: {file_size}")
            print("  Using existing file.")
            return str(filepath)

        # Download to temp file, then move on success
        print(f"Downloading from: {url}")
        print(f"Saving to: {filepath}")

        # Set headers
        headers = {
            'User-Agent': 'PodcastTranscriber/1.0 (Whisper AI Transcription)'
        }

        # Download to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
            tmp_path = tmp_file.name

            response = requests.get(url, stream=True, headers=headers, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp_file.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        mb_downloaded = downloaded_size / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f'\rProgress: {progress:5.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)', end='', flush=True)

        # Move temp file to final location
        shutil.move(tmp_path, filepath)
        print("\nDownload complete!")
        return str(filepath)

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
