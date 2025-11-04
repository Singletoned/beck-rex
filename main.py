#!/usr/bin/env python3
"""
Podcast Transcriber - Main CLI
Download and transcribe the latest episode of a podcast
"""

import argparse
import sys
from pathlib import Path
from podcast_transcriber.podcast_fetcher import PodcastFetcher
from podcast_transcriber.downloader import PodcastDownloader
from podcast_transcriber.transcriber import AudioTranscriber


def main():
    parser = argparse.ArgumentParser(
        description="Download and transcribe the latest episode of a podcast"
    )
    parser.add_argument(
        "rss_url",
        help="RSS feed URL of the podcast"
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base). Larger = more accurate but slower"
    )
    parser.add_argument(
        "--format",
        default="txt",
        choices=["txt", "srt", "vtt"],
        help="Output format for transcript (default: txt)"
    )
    parser.add_argument(
        "--language",
        help="Language code (e.g., 'en', 'es', 'fr'). Auto-detect if not specified"
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download the audio, don't transcribe"
    )
    parser.add_argument(
        "--download-dir",
        default="downloads",
        help="Directory to save downloaded files (default: downloads)"
    )
    parser.add_argument(
        "--transcript-dir",
        default="transcripts",
        help="Directory to save transcripts (default: transcripts)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Podcast Transcriber")
    print("=" * 80)

    # Step 1: Fetch podcast information
    print("\n[1/4] Fetching podcast feed...")
    fetcher = PodcastFetcher(args.rss_url)

    if not fetcher.fetch_feed():
        print("Error: Could not fetch podcast feed. Please check the RSS URL.")
        return 1

    podcast_info = fetcher.get_podcast_info()
    print(f"\nPodcast: {podcast_info.get('title', 'Unknown')}")

    # Step 2: Get latest episode
    print("\n[2/4] Finding latest episode...")
    episode = fetcher.get_latest_episode()

    if not episode:
        print("Error: Could not find latest episode or audio URL.")
        return 1

    print(f"\nLatest Episode:")
    print(f"  Title: {episode['title']}")
    print(f"  Published: {episode['published']}")
    print(f"  Audio URL: {episode['audio_url']}")

    # Step 3: Download audio
    print("\n[3/4] Downloading audio...")
    downloader = PodcastDownloader(download_dir=args.download_dir)

    # Create a clean filename from episode title
    clean_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in episode['title'])
    clean_title = clean_title.replace(' ', '_')[:100]  # Limit length

    audio_path = downloader.download(episode['audio_url'], filename=f"{clean_title}.mp3")

    if not audio_path:
        print("Error: Failed to download audio file.")
        return 1

    file_size = downloader.get_file_size(audio_path)
    print(f"Downloaded file size: {file_size}")

    if args.download_only:
        print("\n✓ Download complete! (Transcription skipped)")
        print(f"Audio saved to: {audio_path}")
        return 0

    # Step 4: Transcribe
    print("\n[4/4] Transcribing audio...")
    print(f"Using Whisper model: {args.model}")
    print("Note: Transcription may take several minutes depending on audio length and model size.")
    print("Recommendation: 'base' model is good for most cases. Use 'small' or 'medium' for better accuracy.")

    transcriber = AudioTranscriber(model_size=args.model, output_dir=args.transcript_dir)
    result = transcriber.transcribe(audio_path, language=args.language)

    if not result:
        print("Error: Transcription failed.")
        return 1

    # Save transcript
    transcript_path = transcriber.save_transcript(result, audio_path, format=args.format)

    if not transcript_path:
        print("Error: Failed to save transcript.")
        return 1

    # Summary
    print("\n" + "=" * 80)
    print("✓ SUCCESS!")
    print("=" * 80)
    print(f"Audio saved to: {audio_path}")
    print(f"Transcript saved to: {transcript_path}")
    print(f"Detected language: {result.get('language', 'unknown')}")
    print(f"\nTranscript preview (first 500 chars):")
    print("-" * 80)
    print(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
    print("-" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
