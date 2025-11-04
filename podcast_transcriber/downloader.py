"""
Module for downloading podcast audio files
"""

import os
import requests
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

    def download(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Download an audio file from URL

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

            # Check if file already exists
            if filepath.exists():
                print(f"File already exists: {filepath}")
                return str(filepath)

            print(f"Downloading from: {url}")
            print(f"Saving to: {filepath}")

            # Download with progress
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"\rProgress: {progress:.1f}%", end='', flush=True)

            print("\nDownload complete!")
            return str(filepath)

        except requests.exceptions.RequestException as e:
            print(f"Error downloading file: {e}")
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
