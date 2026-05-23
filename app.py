"""Flask application for Corpus Forge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

import ai_client
import database
import ingestor
import retriever


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
TEMPLATE_FOLDER = BASE_DIR / "templates"

ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "py", "js"}

app = Flask(__name__, template_folder=str(TEMPLATE_FOLDER))
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)


def _ensure_upload_folder() -> None:
	UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def _allowed_file(filename: str) -> bool:
	return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _normalize_doc_ids(doc_ids: Optional[List[Any]]) -> List[str]:
	if not doc_ids:
		return []
	return [str(doc_id) for doc_id in doc_ids if doc_id is not None and str(doc_id).strip()]


def _get_document_by_id(document_id: int) -> Optional[Dict[str, Any]]:
	for document in database.get_all_documents():
		if int(document["id"]) == int(document_id):
			return document
	return None


def _get_context_from_doc_ids(doc_ids: List[Any], question: str = "") -> str:
	normalized_doc_ids = _normalize_doc_ids(doc_ids)
	if not normalized_doc_ids:
		return ""
	return retriever.query(question or "Summarize the most relevant information.", normalized_doc_ids)


def _request_json() -> Dict[str, Any]:
	payload = request.get_json(silent=True)
	return payload if isinstance(payload, dict) else {}


@app.route("/", methods=["GET"])
def index():
	return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_document():
	_ensure_upload_folder()

	if "file" not in request.files:
		return jsonify({"error": "No file provided."}), 400

	file = request.files["file"]
	if not file or file.filename == "":
		return jsonify({"error": "Empty filename."}), 400

	raw_filename = file.filename
	if raw_filename is None:
		return jsonify({"error": "Empty filename."}), 400

	if not _allowed_file(raw_filename):
		return jsonify({"error": "Unsupported file type."}), 400

	filename = secure_filename(raw_filename)
	file_path = UPLOAD_FOLDER / filename
	file.save(file_path)

	try:
		text = ingestor.ingest_file(str(file_path))
		document_id = database.insert_document(
			filename=filename,
			filetype=file_path.suffix.lstrip(".").lower(),
			content=text,
		)
		retriever.add_document(str(document_id), text, filename)
	except Exception as exc:
		if file_path.exists():
			file_path.unlink(missing_ok=True)
		return jsonify({"error": str(exc)}), 500

	document = {
		"id": document_id,
		"filename": filename,
		"filetype": file_path.suffix.lstrip(".").lower(),
		"content": text,
		"upload_date": None,
		"is_active": 1,
	}
	return jsonify({"message": "Document uploaded successfully.", "document": document}), 201


@app.route("/documents", methods=["GET"])
def list_documents():
	documents = database.get_all_documents()
	return jsonify(documents)


@app.route("/documents/<int:document_id>/toggle", methods=["POST"])
def toggle_document(document_id: int):
	toggled = database.toggle_document_active(document_id)
	if not toggled:
		return jsonify({"error": "Document not found."}), 404
	document = _get_document_by_id(document_id)
	return jsonify({"message": "Document status updated.", "document": document})


@app.route("/documents/<int:document_id>", methods=["DELETE"])
def delete_document(document_id: int):
	document = _get_document_by_id(document_id)
	if document is None:
		return jsonify({"error": "Document not found."}), 404

	deleted = database.delete_document(document_id)
	if not deleted:
		return jsonify({"error": "Document not found."}), 404

	try:
		retriever.delete_document(str(document_id))
	except Exception:
		pass

	file_path = UPLOAD_FOLDER / str(document["filename"])
	if file_path.exists():
		file_path.unlink()

	return jsonify({"message": "Document deleted successfully.", "document_id": document_id})


@app.route("/chat", methods=["POST"])
def chat():
	payload = _request_json()
	question = payload.get("question", "")
	doc_ids = payload.get("doc_ids", [])
	audience = payload.get("audience", "intermediate")
	tone = payload.get("tone", "formal")

	if not question:
		return jsonify({"error": "question is required."}), 400

	context = _get_context_from_doc_ids(doc_ids, question)
	answer = ai_client.chat(context, question, audience, tone)
	return jsonify({"answer": answer})


@app.route("/flashcards", methods=["POST"])
def flashcards():
	payload = _request_json()
	doc_ids = payload.get("doc_ids", [])
	count = int(payload.get("count", 5))

	context = _get_context_from_doc_ids(doc_ids)
	cards = ai_client.generate_flashcards(context, count)

	primary_document_id = int(doc_ids[0]) if doc_ids else None
	if primary_document_id is not None:
		database.insert_artifact("flashcard", {"items": cards}, primary_document_id)

	return jsonify({"flashcards": cards})


@app.route("/quiz", methods=["POST"])
def quiz():
	payload = _request_json()
	doc_ids = payload.get("doc_ids", [])
	count = int(payload.get("count", 5))

	context = _get_context_from_doc_ids(doc_ids)
	quiz_items = ai_client.generate_quiz(context, count)

	primary_document_id = int(doc_ids[0]) if doc_ids else None
	if primary_document_id is not None:
		database.insert_artifact("quiz", {"items": quiz_items}, primary_document_id)

	return jsonify({"quiz": quiz_items})


@app.route("/code-review", methods=["POST"])
def code_review():
	payload = _request_json()
	doc_ids = payload.get("doc_ids", [])

	context = _get_context_from_doc_ids(doc_ids)
	report = ai_client.review_code(context)

	primary_document_id = int(doc_ids[0]) if doc_ids else None
	if primary_document_id is not None:
		database.insert_artifact("code_review", {"report": report}, primary_document_id)

	return jsonify({"report": report})


@app.route("/usage", methods=["GET"])
def usage():
	return jsonify(ai_client.get_usage())


def _initialize_app() -> None:
	_ensure_upload_folder()
	database.init_database()
	retriever.init_chroma()
	ai_client.init_client()


_initialize_app()


if __name__ == "__main__":
	app.run(debug=True)
