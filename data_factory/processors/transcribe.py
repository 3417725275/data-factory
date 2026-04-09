"""Video transcription processor. Priority: Whisper API → Local Whisper → Platform subtitle."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from data_factory.core.config import AppConfig
from data_factory.core.schema import FetchResult
from data_factory.core.storage import load_meta, update_meta, write_json
from data_factory.processors.base import Processor

log = logging.getLogger(__name__)


def fetch_platform_subtitle(result: FetchResult, output_dir: Path) -> dict | None:
    meta = load_meta(output_dir) or {}
    platform = meta.get("platform", "")
    url = meta.get("url", "")

    from data_factory.core.opencli import run_opencli, OpencliError

    try:
        if platform == "youtube":
            data = run_opencli("youtube", "transcript", [url])
            text = "\n".join(row.get("text", row.get("content", "")) for row in data) if isinstance(data, list) else str(data)
            return {"method": "platform", "language": "", "text": text, "segments": data if isinstance(data, list) else []}
        elif platform == "bilibili":
            bvid = meta.get("id", "")
            data = run_opencli("bilibili", "subtitle", [bvid])
            text = "\n".join(row.get("content", "") for row in data) if isinstance(data, list) else str(data)
            return {"method": "platform", "language": "zh", "text": text, "segments": data if isinstance(data, list) else []}
    except OpencliError:
        log.debug("Platform subtitle not available for %s", url)
    return None


class TranscribeProcessor(Processor, processor_name="transcribe"):

    def should_run(self, result: FetchResult, output_dir: Path) -> bool:
        if result.content_type != "video":
            return False
        meta = load_meta(output_dir)
        if not meta:
            return False
        return not meta.get("transcript_completed", False)

    def process(self, result: FetchResult, output_dir: Path, config: AppConfig) -> None:
        tc = config.transcribe
        transcript = None

        if tc.whisper_api.enabled and tc.whisper_api.api_key:
            transcript = self._whisper_api(result, output_dir, tc)

        if transcript is None and tc.whisper_local.enabled:
            transcript = self._whisper_local(result, output_dir, tc)

        if transcript is None and tc.platform_subtitle.enabled:
            transcript = fetch_platform_subtitle(result, output_dir)

        if transcript:
            write_json(output_dir / "transcript.json", transcript)
            update_meta(output_dir, {
                "transcript_completed": True,
                "status": "complete",
            })
            log.info("Transcription complete: %s (method=%s)", output_dir.name, transcript.get("method"))
        else:
            log.warning("No transcription method succeeded for %s", output_dir.name)

    def _get_audio(self, result: FetchResult, output_dir: Path) -> Path | None:
        audio_path = output_dir / "assets" / "audio.mp3"
        if audio_path.exists():
            return audio_path
        if result.audio_path and result.audio_path.exists():
            return result.audio_path
        meta = load_meta(output_dir) or {}
        url = meta.get("url", "")
        if not url:
            return None
        try:
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "mp3", "-o", str(audio_path), url],
                capture_output=True, timeout=300,
            )
            return audio_path if audio_path.exists() else None
        except Exception as e:
            log.error("Failed to extract audio: %s", e)
            return None

    def _whisper_api(self, result: FetchResult, output_dir: Path, tc) -> dict | None:
        audio = self._get_audio(result, output_dir)
        if not audio:
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=tc.whisper_api.api_key, base_url=tc.whisper_api.base_url)
            with open(audio, "rb") as f:
                resp = client.audio.transcriptions.create(model=tc.whisper_api.model, file=f, response_format="verbose_json")
            return {
                "method": "whisper_api",
                "language": getattr(resp, "language", ""),
                "text": resp.text,
                "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in (resp.segments or [])],
            }
        except Exception as e:
            log.error("Whisper API failed: %s", e)
            return None

    def _whisper_local(self, result: FetchResult, output_dir: Path, tc) -> dict | None:
        audio = self._get_audio(result, output_dir)
        if not audio:
            return None
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(tc.whisper_local.model_size, device=tc.whisper_local.device)
            segments, info = model.transcribe(str(audio))
            seg_list = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
            return {
                "method": "whisper_local",
                "language": info.language,
                "text": " ".join(s["text"] for s in seg_list),
                "segments": seg_list,
            }
        except Exception as e:
            log.error("Local Whisper failed: %s", e)
            return None
