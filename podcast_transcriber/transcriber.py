"""
Module for transcribing audio files using Whisper
"""

import os
from pathlib import Path
from typing import Optional, Dict
import whisper
from datetime import datetime


class AudioTranscriber:
    """Transcribes audio files using OpenAI's Whisper model"""

    def __init__(self, model_size: str = "base", output_dir: str = "transcripts"):
        """
        Initialize the transcriber

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            output_dir: Directory to save transcripts
        """
        self.model_size = model_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = None

        print(f"Initializing Whisper model (size: {model_size})")
        print("Note: First run will download the model (may take a few minutes)")

    def load_model(self):
        """Load the Whisper model"""
        if self.model is None:
            print(f"Loading {self.model_size} model...")
            self.model = whisper.load_model(self.model_size)
            print("Model loaded successfully!")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Optional[Dict]:
        """
        Transcribe an audio file

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            Dict containing transcription result or None if failed
        """
        try:
            self.load_model()

            print(f"\nTranscribing: {audio_path}")
            print("This may take several minutes depending on the audio length...")

            # Transcribe
            result = self.model.transcribe(
                audio_path,
                language=language,
                fp16=False  # Use FP32 for better compatibility with Apple Silicon
            )

            print("\nTranscription complete!")
            return result

        except Exception as e:
            print(f"Error during transcription: {e}")
            return None

    def save_transcript(self, result: Dict, audio_filename: str, format: str = "txt") -> Optional[str]:
        """
        Save transcript to file

        Args:
            result: Whisper transcription result
            audio_filename: Original audio filename
            format: Output format (txt, srt, vtt)

        Returns:
            Path to saved transcript or None if failed
        """
        try:
            base_name = Path(audio_filename).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if format == "txt":
                output_file = self.output_dir / f"{base_name}_{timestamp}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"Transcription of: {audio_filename}\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Language: {result.get('language', 'unknown')}\n")
                    f.write("="*80 + "\n\n")
                    f.write(result['text'])

            elif format == "srt":
                output_file = self.output_dir / f"{base_name}_{timestamp}.srt"
                self._write_srt(output_file, result['segments'])

            elif format == "vtt":
                output_file = self.output_dir / f"{base_name}_{timestamp}.vtt"
                self._write_vtt(output_file, result['segments'])

            else:
                print(f"Unsupported format: {format}")
                return None

            print(f"Transcript saved to: {output_file}")
            return str(output_file)

        except Exception as e:
            print(f"Error saving transcript: {e}")
            return None

    def _write_srt(self, filepath: Path, segments: list):
        """Write SRT subtitle format"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, start=1):
                start = self._format_timestamp(segment['start'])
                end = self._format_timestamp(segment['end'])
                text = segment['text'].strip()

                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

    def _write_vtt(self, filepath: Path, segments: list):
        """Write WebVTT subtitle format"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for segment in segments:
                start = self._format_timestamp(segment['start'], vtt=True)
                end = self._format_timestamp(segment['end'], vtt=True)
                text = segment['text'].strip()

                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

    def _format_timestamp(self, seconds: float, vtt: bool = False) -> str:
        """Format timestamp for subtitles"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        if vtt:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
