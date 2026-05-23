"""Google Gemini client helpers for Corpus Forge."""

from __future__ import annotations

import json
import importlib
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

genai = importlib.import_module("google.generativeai")


_client_initialized = False
_model: Any = None
_usage = {"total_requests": 0, "total_tokens": 0}


def init_client():
	"""Load `GOOGLE_API_KEY` from the environment and initialize Gemini."""
	global _client_initialized, _model

	load_dotenv()
	api_key = os.getenv("GOOGLE_API_KEY")
	if not api_key:
		raise RuntimeError("GOOGLE_API_KEY is not set in the environment.")

	genai.configure(api_key=api_key)
	_model = genai.GenerativeModel("gemini-1.5-flash")
	_client_initialized = True
	return _model


def _get_model() -> Any:
	if not _client_initialized or _model is None:
		return init_client()
	return _model


def _record_usage(response: Any):
	usage_metadata = getattr(response, "usage_metadata", None)
	_usage["total_requests"] += 1

	if usage_metadata is None:
		return

	total_tokens = getattr(usage_metadata, "total_token_count", None)
	if total_tokens is None:
		total_tokens = getattr(usage_metadata, "total_tokens", None)
	if total_tokens is None and isinstance(usage_metadata, dict):
		total_tokens = usage_metadata.get("total_token_count") or usage_metadata.get("total_tokens")

	if isinstance(total_tokens, (int, float)):
		_usage["total_tokens"] += int(total_tokens)


def _response_text(response: Any) -> str:
	text = getattr(response, "text", None)
	if text:
		return str(text)

	candidates = getattr(response, "candidates", None)
	if candidates:
		parts = []
		for candidate in candidates:
			content = getattr(candidate, "content", None)
			if content is None:
				continue
			chunk_parts = getattr(content, "parts", None) or []
			for part in chunk_parts:
				part_text = getattr(part, "text", None)
				if part_text:
					parts.append(str(part_text))
		if parts:
			return "".join(parts)

	return ""


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
	cleaned = text.strip()
	if cleaned.startswith("```"):
		cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
		cleaned = re.sub(r"\s*```$", "", cleaned)

	try:
		parsed = json.loads(cleaned)
	except json.JSONDecodeError:
		start = cleaned.find("[")
		end = cleaned.rfind("]")
		if start != -1 and end != -1 and end > start:
			parsed = json.loads(cleaned[start : end + 1])
		else:
			raise

	if isinstance(parsed, dict) and "items" in parsed and isinstance(parsed["items"], list):
		return parsed["items"]
	if not isinstance(parsed, list):
		raise ValueError("Expected a JSON list from Gemini.")
	return parsed


def _call_model(prompt: str, *, response_mime_type: Optional[str] = None) -> Any:
	model = _get_model()
	generation_config: Dict[str, Any] = {"temperature": 0.4}
	if response_mime_type:
		generation_config["response_mime_type"] = response_mime_type

	response = model.generate_content(prompt, generation_config=generation_config)
	_record_usage(response)
	return response


def chat(context: str, question: str, audience: str, tone: str) -> str:
	"""Answer a question using retrieved context and the requested style."""
	prompt = (
		"You are Corpus Forge, an assistant that answers using only the provided context when possible.\n\n"
		f"Audience level: {audience}.\n"
		f"Tone: {tone}.\n\n"
		"Context:\n"
		f"{context}\n\n"
		"Question:\n"
		f"{question}\n\n"
		"Write a clear answer that matches the audience level and tone. If the context is insufficient, say what is missing."
	)
	response = _call_model(prompt)
	return _response_text(response)


def generate_flashcards(context: str, count: int):
	"""Generate flashcards as a JSON list of objects with `front` and `back`."""
	prompt = (
		"Generate flashcards from the context below.\n"
		f"Create exactly {count} flashcards.\n"
		"Return only valid JSON as a list of objects with keys `front` and `back`.\n\n"
		f"Context:\n{context}"
	)
	response = _call_model(prompt, response_mime_type="application/json")
	return _extract_json_array(_response_text(response))


def generate_quiz(context: str, count: int):
	"""Generate multiple choice questions as a JSON list."""
	prompt = (
		"Generate a multiple-choice quiz from the context below.\n"
		f"Create exactly {count} questions.\n"
		"Return only valid JSON as a list of objects with keys `question`, `options`, and `answer`.\n"
		"Each `options` value must be a list of exactly 4 strings.\n"
		"The `answer` must match one of the options exactly.\n\n"
		f"Context:\n{context}"
	)
	response = _call_model(prompt, response_mime_type="application/json")
	return _extract_json_array(_response_text(response))


def review_code(code_text: str) -> str:
	"""Generate a code review report for the provided code."""
	prompt = (
		"Review the following code and provide a concise but useful code review.\n"
		"Focus on correctness, security, maintainability, readability, and any notable improvements.\n\n"
		f"Code:\n{code_text}"
	)
	response = _call_model(prompt)
	return _response_text(response)


def get_usage() -> Dict[str, int]:
	"""Return accumulated request and token counts across API calls."""
	return dict(_usage)
