"""Speaker identification via voice embeddings (wespeakerruntime).

Provides automatic resident identification by comparing a new audio sample
against stored speaker embeddings using cosine similarity.

Requires the optional ``wespeakerruntime`` package. When not installed the
module degrades gracefully — ``is_available()`` returns False.
"""

from __future__ import annotations

import logging
import struct
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soul.memory.store import SoulStore

logger = logging.getLogger(__name__)


class SpeakerIdentifier:
    """Voice-based resident identification using wespeaker ONNX models."""

    def __init__(self, store: SoulStore, threshold: float = 0.55):
        self._store = store
        self._threshold = threshold
        self._model = None

    def _get_model(self):
        """Lazy-load wespeaker ONNX model."""
        if self._model is None:
            import wespeakerruntime as wespeaker

            self._model = wespeaker.Speaker(lang="en")
        return self._model

    def is_available(self) -> bool:
        """Check whether wespeakerruntime is installed and model loads."""
        try:
            self._get_model()
            return True
        except ImportError:
            return False
        except Exception as exc:
            logger.warning("wespeaker model failed to load: %s", exc)
            return False

    def extract_embedding(self, audio_data: bytes) -> list[float] | None:
        """Extract a speaker embedding from raw audio bytes (WAV format)."""
        model = self._get_model()
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                tmp.write(audio_data)
                tmp.flush()
                embedding = model.extract_embedding(tmp.name)
                if embedding is not None:
                    return list(embedding)
        except Exception as exc:
            logger.warning("Embedding extraction failed: %s", exc)
        return None

    def identify(self, audio_data: bytes) -> str | None:
        """Compare audio against stored embeddings, return resident_id or None."""
        embedding = self.extract_embedding(audio_data)
        if embedding is None:
            return None

        rows = self._store._conn.execute(
            "SELECT resident_id, embedding FROM speaker_embeddings"
        ).fetchall()
        if not rows:
            return None

        best_id = None
        best_score = -1.0

        for row in rows:
            stored = _blob_to_floats(row["embedding"])
            score = _cosine_similarity(embedding, stored)
            if score > best_score:
                best_score = score
                best_id = row["resident_id"]

        if best_score >= self._threshold:
            logger.info(
                "Speaker identified as %s (score=%.3f)", best_id, best_score
            )
            return best_id

        logger.debug("No speaker match above threshold (best=%.3f)", best_score)
        return None

    def enroll(self, resident_id: str, audio_data: bytes) -> bool:
        """Store a voice sample embedding for a resident."""
        embedding = self.extract_embedding(audio_data)
        if embedding is None:
            return False

        emb_id = self._store._new_id()
        blob = _floats_to_blob(embedding)
        with self._store._transaction():
            self._store._conn.execute(
                "INSERT INTO speaker_embeddings (id, resident_id, embedding) "
                "VALUES (?, ?, ?)",
                (emb_id, resident_id, blob),
            )
        logger.info("Enrolled voice for resident %s (id=%s)", resident_id, emb_id)
        return True


# -- helper functions --------------------------------------------------------


def _floats_to_blob(floats: list[float]) -> bytes:
    """Pack a list of floats into a compact binary blob."""
    return struct.pack(f"{len(floats)}f", *floats)


def _blob_to_floats(blob: bytes) -> list[float]:
    """Unpack a binary blob back into a list of floats."""
    n = len(blob) // 4  # 4 bytes per float32
    return list(struct.unpack(f"{n}f", blob))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
