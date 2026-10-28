"""Session transcription (stub; wired to Muse Voice Transcribe later).

Target: speaker-attributed transcripts of consented session recordings, via
the Meta Model API speech-to-text endpoints. This module fixes the interface
now so the recording step has a stable contract to build against.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    """One speaker-attributed transcript segment."""

    speaker: str
    start_s: float
    end_s: float
    text: str


@dataclass(frozen=True)
class Transcript:
    """Full transcription result."""

    segments: tuple[Segment, ...]
    full_text: str


def transcribe(
    audio_path: str | Path, *, num_speakers: int | None = None
) -> Transcript:
    """Transcribe a recording; raises until the Voice Transcribe call is built."""
    raise NotImplementedError(
        "transcription not implemented (Muse Voice Transcribe wiring pending)"
    )
