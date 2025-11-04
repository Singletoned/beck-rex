"""
Module for fetching podcast information from RSS feeds using podcastparser
"""

import podcastparser
import requests
from typing import Optional, Dict


class PodcastFetcher:
    """Fetches podcast information from RSS feeds using podcastparser"""

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
        Fetch and parse the RSS feed using podcastparser

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Fetch the feed content
            response = requests.get(self.rss_url, timeout=30)
            response.raise_for_status()

            # Parse with podcastparser
            self.feed = podcastparser.parse(self.rss_url, response.content)

            # Check if we have episodes
            return 'episodes' in self.feed and len(self.feed['episodes']) > 0
        except requests.exceptions.RequestException as e:
            print(f"Error fetching feed: {e}")
            return False
        except Exception as e:
            print(f"Error parsing feed: {e}")
            return False

    def get_latest_episode(self) -> Optional[Dict[str, str]]:
        """
        Get information about the latest episode

        Returns:
            Dict containing episode information or None if not found
        """
        if not self.feed or 'episodes' not in self.feed or not self.feed['episodes']:
            return None

        # Episodes are typically in chronological order, first is latest
        latest = self.feed['episodes'][0]

        # Get audio URL from enclosures
        audio_url = None
        if 'enclosures' in latest and latest['enclosures']:
            # Get the first enclosure (usually the audio file)
            audio_url = latest['enclosures'][0]['url']

        if not audio_url:
            print("Warning: No audio URL found in latest episode")
            return None

        return {
            'title': latest.get('title', 'Unknown Title'),
            'published': latest.get('published', 'Unknown Date'),
            'description': latest.get('description', ''),
            'audio_url': audio_url,
            'podcast_title': self.feed.get('title', 'Unknown Podcast')
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
            'title': self.feed.get('title', 'Unknown'),
            'description': self.feed.get('description', ''),
            'author': self.feed.get('author', 'Unknown')
        }
