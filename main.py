#!/usr/bin/env python3
"""
Podcast Transcriber - Main CLI
Download and transcribe the latest episode of a podcast
"""

import click
from pathlib import Path
from podcast_transcriber.podcast_fetcher import PodcastFetcher
from podcast_transcriber.downloader import PodcastDownloader
from podcast_transcriber.transcriber import AudioTranscriber


@click.command()
@click.argument('rss_url')
@click.option(
    '--model',
    type=click.Choice(['tiny', 'base', 'small', 'medium', 'large'], case_sensitive=False),
    default='base',
    show_default=True,
    help='Whisper model size. Larger = more accurate but slower.'
)
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['txt', 'srt', 'vtt'], case_sensitive=False),
    default='txt',
    show_default=True,
    help='Output format for transcript.'
)
@click.option(
    '--language',
    help="Language code (e.g., 'en', 'es', 'fr'). Auto-detect if not specified."
)
@click.option(
    '--download-only',
    is_flag=True,
    help='Only download the audio, don\'t transcribe.'
)
@click.option(
    '--download-dir',
    default='downloads',
    show_default=True,
    help='Directory to save downloaded files.'
)
@click.option(
    '--transcript-dir',
    default='transcripts',
    show_default=True,
    help='Directory to save transcripts.'
)
@click.option(
    '--diarize',
    is_flag=True,
    help='Enable speaker diarization (identifies different speakers).'
)
@click.option(
    '--hf-token',
    envvar='HF_TOKEN',
    help='HuggingFace token for diarization model (or set HF_TOKEN env var).'
)
@click.option(
    '--no-timestamps',
    is_flag=True,
    help='Disable timestamps in text output.'
)
def main(rss_url, model, output_format, language, download_only, download_dir, transcript_dir, diarize, hf_token, no_timestamps):
    """
    Download and transcribe the latest episode of a podcast.

    RSS_URL: The RSS feed URL of the podcast
    """
    click.echo("=" * 80)
    click.echo("Podcast Transcriber")
    click.echo("=" * 80)

    # Step 1: Fetch podcast information
    click.echo("\n[1/4] Fetching podcast feed...")
    fetcher = PodcastFetcher(rss_url)

    if not fetcher.fetch_feed():
        click.secho("Error: Could not fetch podcast feed. Please check the RSS URL.", fg='red', err=True)
        raise click.Abort()

    podcast_info = fetcher.get_podcast_info()
    click.echo(f"\nPodcast: {podcast_info.get('title', 'Unknown')}")

    # Step 2: Get latest episode
    click.echo("\n[2/4] Finding latest episode...")
    episode = fetcher.get_latest_episode()

    if not episode:
        click.secho("Error: Could not find latest episode or audio URL.", fg='red', err=True)
        raise click.Abort()

    click.echo(f"\nLatest Episode:")
    click.echo(f"  Title: {episode['title']}")
    click.echo(f"  Published: {episode['published']}")
    click.echo(f"  Audio URL: {episode['audio_url']}")

    # Step 3: Download audio
    click.echo("\n[3/4] Downloading audio...")
    downloader = PodcastDownloader(download_dir=download_dir)

    # Create a clean filename from episode title
    clean_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in episode['title'])
    clean_title = clean_title.replace(' ', '_')[:100]  # Limit length

    audio_path = downloader.download(episode['audio_url'], filename=f"{clean_title}.mp3")

    if not audio_path:
        click.secho("Error: Failed to download audio file.", fg='red', err=True)
        raise click.Abort()

    file_size = downloader.get_file_size(audio_path)
    click.echo(f"Downloaded file size: {file_size}")

    if download_only:
        click.echo("\n✓ Download complete! (Transcription skipped)")
        click.secho(f"Audio saved to: {audio_path}", fg='green')
        return

    # Step 4: Transcribe
    click.echo("\n[4/4] Transcribing audio...")
    click.echo(f"Using Whisper model: {model}")
    if diarize:
        click.echo("Speaker diarization: ENABLED")
        if not hf_token:
            click.secho("Warning: No HuggingFace token provided. Set HF_TOKEN env var or use --hf-token", fg='yellow')
    click.echo("Note: Transcription may take several minutes depending on audio length and model size.")
    click.echo("Recommendation: 'base' model is good for most cases. Use 'small' or 'medium' for better accuracy.")

    transcriber = AudioTranscriber(model_size=model, output_dir=transcript_dir, enable_diarization=diarize)
    result = transcriber.transcribe(audio_path, language=language, hf_token=hf_token)

    if not result:
        click.secho("Error: Transcription failed.", fg='red', err=True)
        raise click.Abort()

    # Save transcript
    include_timestamps = not no_timestamps
    transcript_path = transcriber.save_transcript(result, audio_path, format=output_format, include_timestamps=include_timestamps)

    if not transcript_path:
        click.secho("Error: Failed to save transcript.", fg='red', err=True)
        raise click.Abort()

    # Summary
    click.echo("\n" + "=" * 80)
    click.secho("✓ SUCCESS!", fg='green', bold=True)
    click.echo("=" * 80)
    click.echo(f"Audio saved to: {audio_path}")
    click.echo(f"Transcript saved to: {transcript_path}")
    click.echo(f"Detected language: {result.get('language', 'unknown')}")
    if diarize and 'diarization' in result:
        speakers = set(seg.get('speaker', 'Unknown') for seg in result['segments'])
        click.echo(f"Speakers detected: {len(speakers)}")
    click.echo(f"\nTranscript preview (first 500 chars):")
    click.echo("-" * 80)
    click.echo(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
    click.echo("-" * 80)


if __name__ == "__main__":
    main()
