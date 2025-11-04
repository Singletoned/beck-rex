"""
Module for fetching podcast information from RSS feeds
"""

import feedparser
from typing import Optional, Dict
from urllib.parse import urlparse


class PodcastFetcher:
    """Fetches podcast information from RSS feeds"""

    def __init__(self, rss_url: str):
        """
        Initialize the podcast fetcher

        Args:
            rss_url: URL of the podcast RSS feed
        """
        self.rss_url = rss_url
        self.feed = None

    def fetch_feed(self) -> bool:
        """
        Fetch and parse the RSS feed

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.feed = feedparser.parse(self.rss_url)
            if self.feed.bozo:
                print(f"Warning: Feed has parsing issues: {self.feed.bozo_exception}")
            return len(self.feed.entries) > 0
        except Exception as e:
            print(f"Error fetching feed: {e}")
            return False

    def get_latest_episode(self) -> Optional[Dict[str, str]]:
        """
        Get information about the latest episode

        Returns:
            Dict containing episode information or None if not found
        """
        if not self.feed or not self.feed.entries:
            return None

        latest = self.feed.entries[0]

        # Find the audio enclosure
        audio_url = None
        for enclosure in getattr(latest, 'enclosures', []):
            if 'audio' in enclosure.get('type', ''):
                audio_url = enclosure.get('href') or enclosure.get('url')
                break

        # Fallback: check links
        if not audio_url:
            for link in getattr(latest, 'links', []):
                if 'audio' in link.get('type', ''):
                    audio_url = link.get('href')
                    break

        if not audio_url:
            print("Warning: No audio URL found in latest episode")
            return None

        return {
            'title': latest.get('title', 'Unknown Title'),
            'published': latest.get('published', 'Unknown Date'),
            'description': latest.get('summary', ''),
            'audio_url': audio_url,
            'podcast_title': self.feed.feed.get('title', 'Unknown Podcast')
        }

    def get_podcast_info(self) -> Dict[str, str]:
        """
        Get general information about the podcast

        Returns:
            Dict containing podcast information
        """
        if not self.feed:
            return {}

        return {
            'title': self.feed.feed.get('title', 'Unknown'),
            'description': self.feed.feed.get('subtitle', ''),
            'author': self.feed.feed.get('author', 'Unknown')
        }
