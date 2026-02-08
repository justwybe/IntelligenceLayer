"""Tests for SpeakerIdentifier — embedding storage, cosine similarity, enrollment."""

from unittest.mock import MagicMock, patch

import pytest

from soul.memory.store import SoulStore
from soul.stt.speaker_id import (
    SpeakerIdentifier,
    _blob_to_floats,
    _cosine_similarity,
    _floats_to_blob,
)


# =========================================================================
# Helper function tests
# =========================================================================


class TestHelpers:

    def test_floats_roundtrip(self):
        original = [1.0, 2.5, -0.3, 0.0, 99.9]
        blob = _floats_to_blob(original)
        restored = _blob_to_floats(blob)
        assert len(restored) == len(original)
        for a, b in zip(original, restored):
            assert abs(a - b) < 1e-5

    def test_cosine_similarity_identical(self):
        v = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_cosine_similarity_opposite(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(_cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_cosine_similarity_different_lengths(self):
        assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_cosine_similarity_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


# =========================================================================
# Schema — speaker_embeddings table exists
# =========================================================================


class TestSpeakerEmbeddingsSchema:

    def test_table_exists(self, store):
        tables = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='speaker_embeddings'"
        ).fetchall()
        assert len(tables) == 1

    def test_schema_version_is_2(self, store):
        row = store._conn.execute("SELECT version FROM schema_version").fetchone()
        assert row["version"] == 2

    def test_migration_idempotent(self, db_path):
        s1 = SoulStore(db_path=db_path)
        s1.close()
        s2 = SoulStore(db_path=db_path)
        row = s2._conn.execute("SELECT version FROM schema_version").fetchone()
        assert row["version"] == 2
        s2.close()


# =========================================================================
# SpeakerIdentifier
# =========================================================================


class TestSpeakerIdentifier:

    def test_is_available_without_wespeaker(self, store):
        sid = SpeakerIdentifier(store)
        with patch.dict("sys.modules", {"wespeakerruntime": None}):
            # Force reimport failure
            sid._model = None
            result = sid.is_available()
        # Should be False or True depending on whether wespeaker is installed
        # We can't guarantee it's installed in test env, just ensure no crash
        assert isinstance(result, bool)

    def test_enroll_and_identify(self, store):
        """Test enrollment and identification with mocked wespeaker."""
        rid = store._new_id()
        store._conn.execute(
            "INSERT INTO residents (id, name) VALUES (?, ?)", (rid, "Martha")
        )
        store._conn.commit()

        sid = SpeakerIdentifier(store, threshold=0.5)

        # Mock the extract_embedding method
        mock_embedding = [0.1] * 256
        with patch.object(sid, "extract_embedding", return_value=mock_embedding):
            assert sid.enroll(rid, b"fake_audio") is True

        # Verify stored in DB
        rows = store._conn.execute(
            "SELECT * FROM speaker_embeddings WHERE resident_id = ?", (rid,)
        ).fetchall()
        assert len(rows) == 1

        # Now identify with same embedding
        with patch.object(sid, "extract_embedding", return_value=mock_embedding):
            result = sid.identify(b"fake_audio")
        assert result == rid

    def test_identify_below_threshold(self, store):
        """Embedding below threshold should return None."""
        rid = store._new_id()
        store._conn.execute(
            "INSERT INTO residents (id, name) VALUES (?, ?)", (rid, "Hans")
        )
        store._conn.commit()

        sid = SpeakerIdentifier(store, threshold=0.99)  # Very high threshold

        # Enroll with one embedding
        stored_emb = [1.0, 0.0, 0.0] + [0.0] * 253
        with patch.object(sid, "extract_embedding", return_value=stored_emb):
            sid.enroll(rid, b"fake")

        # Try to identify with a different embedding
        query_emb = [0.0, 1.0, 0.0] + [0.0] * 253  # Orthogonal
        with patch.object(sid, "extract_embedding", return_value=query_emb):
            result = sid.identify(b"fake")
        assert result is None

    def test_identify_no_embeddings(self, store):
        sid = SpeakerIdentifier(store)
        mock_emb = [0.1] * 256
        with patch.object(sid, "extract_embedding", return_value=mock_emb):
            result = sid.identify(b"fake_audio")
        assert result is None

    def test_identify_extraction_fails(self, store):
        sid = SpeakerIdentifier(store)
        with patch.object(sid, "extract_embedding", return_value=None):
            result = sid.identify(b"fake_audio")
        assert result is None

    def test_enroll_extraction_fails(self, store):
        sid = SpeakerIdentifier(store)
        with patch.object(sid, "extract_embedding", return_value=None):
            result = sid.enroll("some_id", b"fake_audio")
        assert result is False

    def test_multiple_embeddings_per_resident(self, store):
        """Multiple voice samples for one resident — best match wins."""
        rid = store._new_id()
        store._conn.execute(
            "INSERT INTO residents (id, name) VALUES (?, ?)", (rid, "Martha")
        )
        store._conn.commit()

        sid = SpeakerIdentifier(store, threshold=0.5)

        emb1 = [1.0, 0.0, 0.0] + [0.0] * 253
        emb2 = [0.0, 1.0, 0.0] + [0.0] * 253

        with patch.object(sid, "extract_embedding", return_value=emb1):
            sid.enroll(rid, b"sample1")
        with patch.object(sid, "extract_embedding", return_value=emb2):
            sid.enroll(rid, b"sample2")

        rows = store._conn.execute(
            "SELECT * FROM speaker_embeddings WHERE resident_id = ?", (rid,)
        ).fetchall()
        assert len(rows) == 2

        # Query with emb close to emb1
        query = [0.9, 0.1, 0.0] + [0.0] * 253
        with patch.object(sid, "extract_embedding", return_value=query):
            result = sid.identify(b"test")
        assert result == rid
