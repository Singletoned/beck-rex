# Podcast Transcriber

A Python tool that downloads the latest episode of any podcast and transcribes the audio using OpenAI's Whisper speech-to-text model. Optimized for Apple Silicon (M1/M2/M3/M4/M5 MacBook Pro).

## Features

- 🎙️ Download latest episode from any podcast RSS feed
- 🎯 Automatic episode detection
- 📝 Audio transcription using Whisper AI
- 👥 Speaker diarization (identify and label different speakers)
- ⏱️ Timestamps for all transcription segments
- 🌍 Multi-language support with auto-detection
- 📄 Multiple output formats (TXT, SRT, VTT) with speaker labels
- ⚡ Optimized for Apple Silicon
- 📊 Progress tracking for downloads and transcription
- 🖥️ User-friendly CLI powered by Click
- 🔄 Robust downloading with automatic retry and resume capability
- 🔐 Proper authentication handling for podcast hosts

## Prerequisites

- macOS (optimized for Apple Silicon)
- Python 3.8 or higher
- FFmpeg (required by Whisper for audio processing)

## Installation

### 1. Install FFmpeg

Using Homebrew:
```bash
brew install ffmpeg
```

### 2. Clone the repository

```bash
git clone <repository-url>
cd beck-rex
```

### 3. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

**Note:** The first time you run transcription, Whisper will download the selected model (150MB - 3GB depending on size).

### 5. (Optional) Setup Speaker Diarization

To enable speaker diarization (identifying different speakers), you need a HuggingFace token:

1. Create a free account at [HuggingFace](https://huggingface.co/join)
2. Go to [Settings > Access Tokens](https://huggingface.co/settings/tokens)
3. Create a new token with read permissions
4. Accept the terms for [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
5. Accept the terms for [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
6. Set your token as an environment variable:
   ```bash
   export HF_TOKEN="your_token_here"
   ```
   Or add it to your `~/.bashrc` or `~/.zshrc` for persistence.

## Usage

### Basic Usage

Download and transcribe the latest episode:

```bash
python3 main.py "https://feeds.example.com/podcast-rss-feed"
```

### Getting Help

View all available options:
```bash
python3 main.py --help
```

### Advanced Options

```
Usage: main.py [OPTIONS] RSS_URL

  Download and transcribe the latest episode of a podcast.

Options:
  --model [tiny|base|small|medium|large]
                                  Whisper model size. Larger = more accurate
                                  but slower.  [default: base]
                                  - tiny: Fastest, least accurate (~1GB RAM)
                                  - base: Good balance (~1GB RAM)
                                  - small: Better accuracy (~2GB RAM)
                                  - medium: High accuracy (~5GB RAM)
                                  - large: Best accuracy (~10GB RAM)

  --format [txt|srt|vtt]          Output format for transcript.  [default: txt]
                                  - txt: Plain text transcript
                                  - srt: SubRip subtitle format
                                  - vtt: WebVTT subtitle format

  --language TEXT                 Language code (e.g., 'en', 'es', 'fr').
                                  Auto-detect if not specified.

  --download-only                 Only download the audio, don't transcribe.

  --download-dir TEXT             Directory to save downloaded files.
                                  [default: downloads]

  --transcript-dir TEXT           Directory to save transcripts.
                                  [default: transcripts]

  --diarize                       Enable speaker diarization (identifies
                                  different speakers).

  --hf-token TEXT                 HuggingFace token for diarization model
                                  (or set HF_TOKEN env var).

  --no-timestamps                 Disable timestamps in text output.

  --help                          Show this message and exit.
```

### Examples

**Download and transcribe with default settings:**
```bash
python3 main.py "https://feeds.example.com/podcast"
```

**Use a more accurate model:**
```bash
python3 main.py "https://feeds.example.com/podcast" --model medium
```

**Generate subtitles in SRT format:**
```bash
python3 main.py "https://feeds.example.com/podcast" --format srt
```

**Specify language for better accuracy:**
```bash
python3 main.py "https://feeds.example.com/podcast" --language en
```

**Enable speaker diarization (requires HuggingFace token):**
```bash
# Set token as environment variable
export HF_TOKEN="your_huggingface_token"
python3 main.py "https://feeds.example.com/podcast" --diarize

# Or pass token directly
python3 main.py "https://feeds.example.com/podcast" --diarize --hf-token "your_token"
```

**Only download without transcribing:**
```bash
python3 main.py "https://feeds.example.com/podcast" --download-only
```

## Finding Podcast RSS Feeds

Most podcasts have RSS feeds. Here are some ways to find them:

1. **Apple Podcasts**: Right-click on a podcast → "Copy Link" (this is usually the RSS feed)
2. **Spotify**: Use third-party tools like Spotifeed
3. **Podcast websites**: Often have an RSS icon or link
4. **Podcast directories**: Search on sites like Podchaser or Listen Notes

Example RSS feeds to test with:
- NPR News: `https://feeds.npr.org/500005/podcast.xml`
- The Daily: `https://feeds.simplecast.com/54nAGcIl`

## Performance Notes

### Model Selection
- **tiny/base**: Fast transcription, good for quick testing
- **small**: Good balance of speed and accuracy (recommended for most use cases)
- **medium/large**: Best accuracy but slower, use for important transcriptions

### Apple Silicon Optimization
The project uses FP32 precision for better compatibility with Apple Silicon. For even better performance, you can optionally install MLX-optimized Whisper:

```bash
pip install mlx-whisper
```

### Transcription Time
Approximate times on M1/M2/M3 chips:
- 1-hour podcast with 'base' model: ~5-10 minutes
- 1-hour podcast with 'medium' model: ~15-25 minutes
- 1-hour podcast with 'large' model: ~30-45 minutes

## Project Structure

```
beck-rex/
├── main.py                      # CLI entry point (Click-based)
├── podcast_transcriber/         # Main package
│   ├── __init__.py
│   ├── podcast_fetcher.py      # RSS feed parsing (podcastparser)
│   ├── downloader.py           # Audio downloading
│   └── transcriber.py          # Whisper transcription
├── downloads/                   # Downloaded audio files
├── transcripts/                 # Generated transcripts
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Troubleshooting

### FFmpeg not found
```
Error: ffmpeg not found
```
**Solution:** Install FFmpeg with `brew install ffmpeg`

### Module not found
```
ModuleNotFoundError: No module named 'whisper'
```
**Solution:** Activate your virtual environment and reinstall dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Out of memory during transcription
**Solution:** Use a smaller model:
```bash
python3 main.py [URL] --model tiny
```

### Cannot find RSS feed
**Solution:** Verify the RSS URL in a browser. It should return an XML file with podcast information.

## Supported Audio Formats

- MP3
- M4A
- WAV
- OGG
- And any format supported by FFmpeg

## License

MIT License - Feel free to use and modify as needed.

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the transcription model
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) for speaker diarization capabilities
- [gPodder](https://gpodder.github.io/) for the robust podcast downloader with retry and resume capability
- [podcastparser](https://github.com/gpodder/podcastparser) from the gPodder project for reliable RSS/Atom podcast feed parsing
- [Click](https://click.palletsprojects.com/) for the elegant command-line interface
