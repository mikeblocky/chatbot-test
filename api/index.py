import os
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from google import genai

ROOT = Path(__file__).resolve().parents[1]
STORE_NAME = "OptiSigns Support Knowledge Base"
app = Flask(__name__)


def get_context():
    key = os.getenv("API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    client = genai.Client(api_key=key)
    stores = [store for store in client.file_search_stores.list() if store.display_name == STORE_NAME]
    if not stores:
        raise RuntimeError("File Search store not found")
    return client, stores[0]


def urls(interaction):
    found = set()
    for step in interaction.steps or []:
        for block in getattr(step, "content", []) or []:
            for annotation in getattr(block, "annotations", []) or []:
                data = str(getattr(annotation, "model_dump", lambda **_: {})())
                found.update(re.findall(r"https://support\.optisigns\.com[^'\" ]+", data))
    return sorted(found)[:3]


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
def health():
    return send_file(ROOT / "index.html")


@app.route("/ask", methods=["POST"])
@app.route("/api/ask", methods=["POST"])
def ask():
    question = (request.json or {}).get("question", "").strip()
    if not question:
        return jsonify(error="Please enter a question."), 400
    try:
        client, store = get_context()
        instructions = (ROOT / "optibot-system-prompt.txt").read_text(encoding="utf-8").strip()
        interaction = client.interactions.create(model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"), system_instruction=instructions, input=question, tools=[{"type": "file_search", "file_search_store_names": [store.name]}])
        return jsonify(answer=interaction.output_text, sources=urls(interaction))
    except Exception as exc:
        return jsonify(error=str(exc)), 500
