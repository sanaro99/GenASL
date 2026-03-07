"""Tests for GenAI gloss translation pipeline modules.

Tests are designed to work without an actual OpenAI API key by mocking
the LLM calls.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# GlossTranslator tests (mocked LLM)
# ---------------------------------------------------------------------------

class TestGlossTranslator:
    """Tests for src.gloss.translator.GlossTranslator."""

    @patch("src.gloss.translator.GlossTranslator.__init__", return_value=None)
    def test_translate_parses_response(self, mock_init):
        """translate() splits LLM response into uppercase gloss list."""
        from src.gloss.translator import GlossTranslator

        translator = GlossTranslator.__new__(GlossTranslator)
        # Set up mock client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "LIBRARY WHERE"
        translator._client = MagicMock()
        translator._client.chat.completions.create.return_value = mock_response
        translator._model = "gpt-4o-mini"
        translator._system_prompt = "test prompt"
        translator._system_as_user = False

        result = translator.translate("Where is the library?")
        assert result == ["LIBRARY", "WHERE"]

    @patch("src.gloss.translator.GlossTranslator.__init__", return_value=None)
    def test_translate_segments_enriches_all(self, mock_init):
        """translate_segments() adds gloss_sequence and gloss_text to each segment."""
        from src.gloss.translator import GlossTranslator

        translator = GlossTranslator.__new__(GlossTranslator)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "HAPPY TODAY"
        translator._client = MagicMock()
        translator._client.chat.completions.create.return_value = mock_response
        translator._model = "gpt-4o-mini"
        translator._system_prompt = "test"
        translator._system_as_user = False

        segments = [
            {"segment_id": "SEG_001", "text": "She is very happy today."},
        ]
        result = translator.translate_segments(segments)
        assert len(result) == 1
        assert result[0]["gloss_sequence"] == ["HAPPY", "TODAY"]
        assert result[0]["gloss_text"] == "HAPPY TODAY"

    @patch("src.gloss.translator.GlossTranslator.__init__", return_value=None)
    def test_translate_handles_api_error_gracefully(self, mock_init):
        """translate_segments() returns empty gloss on API error."""
        from src.gloss.translator import GlossTranslator

        translator = GlossTranslator.__new__(GlossTranslator)
        translator._client = MagicMock()
        translator._client.chat.completions.create.side_effect = RuntimeError("API down")
        translator._model = "gpt-4o-mini"
        translator._system_prompt = "test"
        translator._system_as_user = False

        segments = [{"segment_id": "SEG_001", "text": "Hello world."}]
        result = translator.translate_segments(segments)
        assert result[0]["gloss_sequence"] == []
        assert result[0]["gloss_text"] == ""


# ---------------------------------------------------------------------------
# WordLookup tests
# ---------------------------------------------------------------------------

class TestWordLookup:
    """Tests for src.gloss.word_lookup.WordLookup."""

    @pytest.fixture
    def mock_manifest(self, tmp_path):
        """Create a temporary word manifest with test data."""
        manifest = {
            "version": "1.0",
            "words": [
                {
                    "word_id": "W001",
                    "gloss": "HAPPY",
                    "source": "wlasl",
                    "file_path": "assets/words/W001_HAPPY.mp4",
                    "duration_ms": 1200,
                },
                {
                    "word_id": "W002",
                    "gloss": "TODAY",
                    "source": "wlasl",
                    "file_path": "assets/words/W002_TODAY.mp4",
                    "duration_ms": 900,
                },
                {
                    "word_id": "W003",
                    "gloss": "MISSING",
                    "source": "placeholder",
                    "file_path": "assets/words/W003_MISSING.mp4",
                    "duration_ms": 500,
                },
            ],
        }
        manifest_path = tmp_path / "word_manifest.json"
        with open(manifest_path, "w") as fh:
            json.dump(manifest, fh)
        return manifest_path

    def test_available_glosses_excludes_placeholders(self, mock_manifest):
        from src.gloss.word_lookup import WordLookup
        wl = WordLookup(manifest_path=mock_manifest)
        assert "HAPPY" in wl.available_glosses
        assert "TODAY" in wl.available_glosses
        assert "MISSING" not in wl.available_glosses

    def test_lookup_returns_entry(self, mock_manifest):
        from src.gloss.word_lookup import WordLookup
        wl = WordLookup(manifest_path=mock_manifest)
        entry = wl.lookup("HAPPY")
        assert entry is not None
        assert entry["word_id"] == "W001"

    def test_lookup_returns_none_for_missing(self, mock_manifest):
        from src.gloss.word_lookup import WordLookup
        wl = WordLookup(manifest_path=mock_manifest)
        assert wl.lookup("NONEXISTENT") is None

    def test_lookup_sequence_marks_found_and_missing(self, mock_manifest):
        from src.gloss.word_lookup import WordLookup
        wl = WordLookup(manifest_path=mock_manifest)
        results = wl.lookup_sequence(["HAPPY", "NONEXISTENT", "TODAY"])
        assert results[0]["found"] is True
        assert results[0]["gloss"] == "HAPPY"
        assert results[1]["found"] is False
        assert results[1]["gloss"] == "NONEXISTENT"
        assert results[2]["found"] is True
        assert results[2]["gloss"] == "TODAY"

    def test_lookup_case_insensitive(self, mock_manifest):
        from src.gloss.word_lookup import WordLookup
        wl = WordLookup(manifest_path=mock_manifest)
        assert wl.lookup("happy") is not None
        assert wl.lookup("Happy") is not None


# ---------------------------------------------------------------------------
# Chainer tests (mocked FFmpeg)
# ---------------------------------------------------------------------------

class TestChainer:
    """Tests for src.gloss.chainer.chain_clips."""

    def test_no_found_clips_returns_none(self):
        from src.gloss.chainer import chain_clips
        entries = [
            {"gloss": "FOO", "found": False, "abs_path": None, "duration_ms": 0},
        ]
        result = chain_clips(entries, "SEG_001")
        assert result is None

    def test_single_clip_copies_file(self, tmp_path):
        from src.gloss.chainer import chain_clips

        # Create a fake clip file
        clip_path = tmp_path / "W001_HAPPY.mp4"
        clip_path.write_bytes(b"\x00" * 100)

        entries = [
            {
                "gloss": "HAPPY",
                "found": True,
                "abs_path": str(clip_path),
                "duration_ms": 1200,
            },
        ]
        result = chain_clips(entries, "SEG_001", output_dir=tmp_path / "out")
        assert result is not None
        assert result["clip_count"] == 1
        assert result["glosses"] == ["HAPPY"]
        assert result["duration_ms"] == 1200
        assert os.path.isfile(result["path"])


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestConfig:
    """Test that config.yaml has the new GenAI settings."""

    def test_llm_section_exists(self):
        import yaml
        cfg_path = _PROJECT_ROOT / "config.yaml"
        with open(cfg_path) as fh:
            cfg = yaml.safe_load(fh)
        assert "llm" in cfg
        assert "provider" in cfg["llm"]
        assert cfg["llm"]["provider"] in ("ollama", "gemini", "openai")

    def test_ollama_config(self):
        import yaml
        cfg_path = _PROJECT_ROOT / "config.yaml"
        with open(cfg_path) as fh:
            cfg = yaml.safe_load(fh)
        assert "ollama" in cfg["llm"]
        assert "model" in cfg["llm"]["ollama"]

    def test_gemini_config(self):
        import yaml
        cfg_path = _PROJECT_ROOT / "config.yaml"
        with open(cfg_path) as fh:
            cfg = yaml.safe_load(fh)
        assert "gemini" in cfg["llm"]
        assert "model" in cfg["llm"]["gemini"]

    def test_test_videos_configured(self):
        import yaml
        cfg_path = _PROJECT_ROOT / "config.yaml"
        with open(cfg_path) as fh:
            cfg = yaml.safe_load(fh)
        videos = cfg.get("test_videos", [])
        assert len(videos) == 4
        ids = [v["id"] for v in videos]
        assert "I_tRSrPru94" in ids
        assert "31y2Bq1RYQA" in ids
        assert "on_1sS6Ii8M" in ids
        assert "bq6GBbh3uhU" in ids
