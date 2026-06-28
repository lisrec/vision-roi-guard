from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from time import perf_counter
from typing import Any

from ..const import (
    DEFAULT_ANALYSIS_TIMEOUT_SEC,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_PROMPT_TEMPLATE,
    VALID_VERDICTS,
)
from ..exceptions import BackendError
from ..models import AnalysisResult
from .base import VisionBackend


def parse_codex_response(payload: str) -> AnalysisResult:
    """Parse strict JSON returned by codex."""
    try:
        data = json.loads(payload.strip())
    except json.JSONDecodeError as err:
        raise BackendError("codex_invalid_json") from err

    if not isinstance(data, dict):
        raise BackendError("codex_invalid_json")

    verdict = data.get("verdict")
    reason = data.get("reason")
    seen_objects = data.get("seen_objects", [])
    if verdict not in VALID_VERDICTS[:-1]:
        raise BackendError("codex_invalid_verdict")
    if not isinstance(reason, str) or not reason.strip():
        raise BackendError("codex_invalid_reason")
    if not isinstance(seen_objects, list) or not all(
        isinstance(item, str) and item.strip() for item in seen_objects
    ):
        raise BackendError("codex_invalid_seen_objects")

    return AnalysisResult(
        verdict=verdict,
        reason=reason.strip(),
        seen_objects=tuple(item.strip() for item in seen_objects),
        backend_name="codex_cli",
        raw_text=payload,
    )


class CodexCliBackend(VisionBackend):
    """Backend that shells out to the local Codex CLI."""

    backend_name = "codex_cli"

    def __init__(self, options: dict[str, Any]) -> None:
        self._model = str(options.get("model") or "").strip() or None
        self._prompt_template = (
            str(options.get("prompt_template") or DEFAULT_PROMPT_TEMPLATE).strip()
            or DEFAULT_PROMPT_TEMPLATE
        )
        self._max_output_tokens = int(options.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS))

    async def validate(self) -> None:
        """Validate that the codex executable is present."""
        if shutil.which("codex") is None:
            raise BackendError("codex_cli_missing")

    async def healthcheck(self) -> None:
        """Perform a lightweight executable health check."""
        await self.validate()
        process = await asyncio.create_subprocess_exec(
            "codex",
            "--help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(process.communicate(), timeout=10)
        except TimeoutError as err:
            process.kill()
            raise BackendError("codex_healthcheck_timeout") from err
        if process.returncode != 0:
            raise BackendError("codex_healthcheck_failed")

    async def analyze(
        self, image_path: str, prompt_context: dict[str, Any], timeout_sec: int
    ) -> AnalysisResult:
        """Run codex against the ROI image and parse the result."""
        prompt = (
            str(prompt_context.get("prompt_template") or self._prompt_template).strip()
            or DEFAULT_PROMPT_TEMPLATE
        )
        if timeout_sec <= 0:
            timeout_sec = DEFAULT_ANALYSIS_TIMEOUT_SEC
        if not await asyncio.to_thread(Path(image_path).is_file):
            raise BackendError("codex_image_missing")

        command = ["codex", "exec", "-i", image_path]
        if self._model:
            command.extend(["--model", self._model])
        if self._max_output_tokens:
            command.extend(["--max-output-tokens", str(self._max_output_tokens)])
        command.append(prompt)

        started = perf_counter()
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_sec)
        except TimeoutError as err:
            process.kill()
            raise BackendError("codex_timeout") from err

        if process.returncode != 0:
            stderr_text = stderr.decode(errors="replace").strip()
            if stderr_text:
                raise BackendError(f"codex_exit_{process.returncode}") from RuntimeError(
                    stderr_text
                )
            raise BackendError(f"codex_exit_{process.returncode}")

        result = parse_codex_response(stdout.decode())
        return AnalysisResult(
            verdict=result.verdict,
            reason=result.reason,
            seen_objects=result.seen_objects,
            backend_name=self.backend_name,
            duration_sec=perf_counter() - started,
            raw_text=None,
        )
