#!/usr/bin/env python3
"""
Example script showing how to use the podcast transcriber programmatically
"""

from podcast_transcriber.podcast_fetcher import PodcastFetcher
from podcast_transcriber.downloader import PodcastDownloader
from podcast_transcriber.transcriber import AudioTranscriber


def main():
    # Example podcast RSS feed (NPR News Now)
    rss_url = "https://feeds.npr.org/500005/podcast.xml"

    print("Podcast Transcriber - Programmatic Example")
    print("=" * 80)

    # 1. Fetch podcast information
    print("\n1. Fetching podcast feed...")
    fetcher = PodcastFetcher(rss_url)

    if not fetcher.fetch_feed():
        print("Failed to fetch feed")
        return

    # Get podcast info
    podcast_info = fetcher.get_podcast_info()
    print(f"Podcast: {podcast_info['title']}")

    # 2. Get latest episode
    print("\n2. Getting latest episode...")
    episode = fetcher.get_latest_episode()

    if not episode:
        print("No episode found")
        return

    print(f"Episode: {episode['title']}")
    print(f"Published: {episode['published']}")

    # 3. Download audio
    print("\n3. Downloading audio...")
    downloader = PodcastDownloader(download_dir="downloads")
    audio_path = downloader.download(episode['audio_url'])

    if not audio_path:
        print("Download failed")
        return

    print(f"Downloaded to: {audio_path}")

    # 4. Transcribe (using 'tiny' model for speed in this example)
    print("\n4. Transcribing audio...")
    print("Note: Using 'tiny' model for demonstration. Use 'base' or 'small' for better accuracy.")

    transcriber = AudioTranscriber(model_size="tiny", output_dir="transcripts")
    result = transcriber.transcribe(audio_path)

    if not result:
        print("Transcription failed")
        return

    # 5. Save transcript
    transcript_path = transcriber.save_transcript(result, audio_path, format="txt")

    print("\n" + "=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print(f"Transcript saved to: {transcript_path}")
    print(f"\nPreview:")
    print("-" * 80)
    print(result['text'][:300] + "...")
    print("-" * 80)


if __name__ == "__main__":
    main()
