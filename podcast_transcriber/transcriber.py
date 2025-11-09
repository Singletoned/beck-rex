"""
Module for transcribing audio files using Whisper with speaker diarization
"""

import os
from pathlib import Path
from typing import Optional, Dict, List
import whisper
from datetime import datetime


class AudioTranscriber:
    """Transcribes audio files using OpenAI's Whisper model with optional speaker diarization"""

    def __init__(self, model_size: str = "base", output_dir: str = "transcripts", enable_diarization: bool = False):
        """
        Initialize the transcriber

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            output_dir: Directory to save transcripts
            enable_diarization: Enable speaker diarization (requires HuggingFace token)
        """
        self.model_size = model_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.enable_diarization = enable_diarization
        self.diarization_pipeline = None

        print(f"Initializing Whisper model (size: {model_size})")
        if enable_diarization:
            print("Speaker diarization enabled")
        print("Note: First run will download the model (may take a few minutes)")

    def load_model(self):
        """Load the Whisper model"""
        if self.model is None:
            print(f"Loading {self.model_size} model...")
            self.model = whisper.load_model(self.model_size)
            print("Model loaded successfully!")

    def load_diarization_pipeline(self, hf_token: Optional[str] = None):
        """Load the speaker diarization pipeline"""
        if self.diarization_pipeline is None and self.enable_diarization:
            try:
                from pyannote.audio import Pipeline
                import torch

                print("Loading speaker diarization model...")
                print("Note: This requires accepting pyannote/speaker-diarization terms on HuggingFace")

                # Try to load from environment variable if not provided
                if hf_token is None:
                    hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')

                if hf_token:
                    self.diarization_pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=hf_token
                    )
                    # Use GPU if available, otherwise CPU
                    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                    if device.type == "cpu" and torch.backends.mps.is_available():
                        device = torch.device("mps")  # Use Apple Silicon GPU
                    self.diarization_pipeline.to(device)
                    print(f"Diarization model loaded successfully! Using device: {device}")
                else:
                    print("Warning: HuggingFace token not found. Diarization disabled.")
                    print("Set HF_TOKEN environment variable or pass --hf-token parameter")
                    self.enable_diarization = False
            except Exception as e:
                print(f"Warning: Could not load diarization model: {e}")
                print("Continuing without speaker diarization...")
                self.enable_diarization = False

    def transcribe(self, audio_path: str, language: Optional[str] = None, hf_token: Optional[str] = None) -> Optional[Dict]:
        """
        Transcribe an audio file with optional speaker diarization

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')
            hf_token: Optional HuggingFace token for diarization

        Returns:
            Dict containing transcription result or None if failed
        """
        try:
            self.load_model()

            print(f"\nTranscribing: {audio_path}")
            print("This may take several minutes depending on the audio length...")

            # Transcribe with word-level timestamps for diarization
            result = self.model.transcribe(
                audio_path,
                language=language,
                fp16=False,  # Use FP32 for better compatibility with Apple Silicon
                word_timestamps=self.enable_diarization  # Enable word timestamps for diarization
            )

            print("\nTranscription complete!")

            # Perform speaker diarization if enabled
            if self.enable_diarization:
                self.load_diarization_pipeline(hf_token)
                if self.diarization_pipeline is not None:
                    print("\nPerforming speaker diarization...")
                    diarization = self.diarization_pipeline(audio_path)
                    result['diarization'] = self._format_diarization(diarization)
                    result = self._assign_speakers_to_segments(result)
                    print("Speaker diarization complete!")

            return result

        except Exception as e:
            print(f"Error during transcription: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _format_diarization(self, diarization) -> List[Dict]:
        """Format diarization results into a list of speaker segments"""
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        return segments

    def _assign_speakers_to_segments(self, result: Dict) -> Dict:
        """Assign speakers to transcription segments based on timing overlap"""
        if 'diarization' not in result or not result['diarization']:
            return result

        diarization = result['diarization']

        # Assign speakers to each segment
        for segment in result['segments']:
            segment_mid = (segment['start'] + segment['end']) / 2

            # Find the speaker at the midpoint of this segment
            for dia_seg in diarization:
                if dia_seg['start'] <= segment_mid <= dia_seg['end']:
                    segment['speaker'] = dia_seg['speaker']
                    break

            # If no speaker found, use the closest one
            if 'speaker' not in segment:
                closest = min(diarization,
                            key=lambda x: min(abs(x['start'] - segment_mid),
                                            abs(x['end'] - segment_mid)))
                segment['speaker'] = closest['speaker']

        return result

    def save_transcript(self, result: Dict, audio_filename: str, format: str = "txt", include_timestamps: bool = True) -> Optional[str]:
        """
        Save transcript to file

        Args:
            result: Whisper transcription result
            audio_filename: Original audio filename
            format: Output format (txt, srt, vtt)
            include_timestamps: Include timestamps in text format

        Returns:
            Path to saved transcript or None if failed
        """
        try:
            base_name = Path(audio_filename).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            has_speakers = 'diarization' in result and result['diarization']

            if format == "txt":
                suffix = "_diarized" if has_speakers else ""
                output_file = self.output_dir / f"{base_name}_{timestamp}{suffix}.txt"
                self._write_txt(output_file, result, audio_filename, include_timestamps)

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
            import traceback
            traceback.print_exc()
            return None

    def _write_txt(self, filepath: Path, result: Dict, audio_filename: str, include_timestamps: bool):
        """Write plain text format with optional speakers and timestamps"""
        has_speakers = 'diarization' in result and result['diarization']

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Transcription of: {audio_filename}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Language: {result.get('language', 'unknown')}\n")
            if has_speakers:
                speakers = set(seg.get('speaker', 'Unknown') for seg in result['segments'])
                f.write(f"Speakers detected: {len(speakers)}\n")
            f.write("="*80 + "\n\n")

            if include_timestamps or has_speakers:
                # Write with timestamps and/or speakers
                current_speaker = None
                for segment in result['segments']:
                    speaker = segment.get('speaker', 'Unknown')
                    start_time = self._format_time_readable(segment['start'])

                    # Add speaker header if speaker changed
                    if has_speakers and speaker != current_speaker:
                        f.write(f"\n[{speaker}]\n")
                        current_speaker = speaker

                    # Write timestamp and text
                    if include_timestamps:
                        f.write(f"[{start_time}] {segment['text'].strip()}\n")
                    else:
                        f.write(f"{segment['text'].strip()}\n")
            else:
                # Write plain text only
                f.write(result['text'])

    def _write_srt(self, filepath: Path, segments: list):
        """Write SRT subtitle format with optional speaker labels"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, start=1):
                start = self._format_timestamp(segment['start'])
                end = self._format_timestamp(segment['end'])
                text = segment['text'].strip()

                # Add speaker label if available
                if 'speaker' in segment:
                    text = f"[{segment['speaker']}] {text}"

                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

    def _write_vtt(self, filepath: Path, segments: list):
        """Write WebVTT subtitle format with optional speaker labels"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for segment in segments:
                start = self._format_timestamp(segment['start'], vtt=True)
                end = self._format_timestamp(segment['end'], vtt=True)
                text = segment['text'].strip()

                # Add speaker label if available
                if 'speaker' in segment:
                    speaker = segment['speaker']
                    f.write(f"{start} --> {end}\n")
                    f.write(f"<v {speaker}>{text}</v>\n\n")
                else:
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

    def _format_time_readable(self, seconds: float) -> str:
        """Format timestamp in readable format (HH:MM:SS)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
