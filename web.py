import os
import re
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request
from google import genai

ROOT = Path(__file__).parent
STORE_NAME = "OptiSigns Support Knowledge Base"
app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OptiBot Support</title><style>
body{font-family:system-ui,sans-serif;background:#f4f7fb;color:#172033;margin:0}main{max-width:760px;margin:8vh auto;padding:28px;background:white;border-radius:18px;box-shadow:0 12px 40px #17203318}h1{margin-top:0}p{color:#5c667a}textarea{width:100%;box-sizing:border-box;min-height:100px;padding:14px;border:1px solid #ccd4e0;border-radius:10px;font:inherit}button{margin-top:12px;background:#2563eb;color:white;border:0;border-radius:9px;padding:12px 20px;font-weight:600;cursor:pointer}.answer{margin-top:24px;padding:20px;background:#f8fafc;border-radius:12px;white-space:pre-wrap;line-height:1.55}.sources{margin-top:18px}.sources a{display:block;margin:8px 0;color:#2563eb;overflow-wrap:anywhere}.error{color:#b42318;margin-top:18px}</style></head>
<body><main><h1>OptiBot Support</h1><p>Ask a question about OptiSigns. Answers come from the support articles.</p>
<form id="form"><textarea id="question" placeholder="How do I add a YouTube video?" required></textarea><button>Ask OptiBot</button></form><div id="result"></div></main>
<script>form.onsubmit=async(e)=>{e.preventDefault();result.innerHTML='<p>Looking through the support articles...</p>';const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:question.value})});const d=await r.json();if(!r.ok){result.innerHTML='<p class="error">'+d.error+'</p>';return}result.innerHTML='<div class="answer">'+d.answer.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</div><div class="sources"><strong>Sources</strong>'+d.sources.map(u=>'<a href="'+u+'" target="_blank" rel="noreferrer">'+u+'</a>').join('')+'</div>'}</script></body></html>"""


def client_and_store():
    key = os.getenv("API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("API_KEY is required")
    client = genai.Client(api_key=key)
    stores = [store for store in client.file_search_stores.list() if store.display_name == STORE_NAME]
    if not stores:
        raise RuntimeError("File Search store not found")
    return client, stores[0]


def source_urls(interaction):
    urls = set()
    for step in interaction.steps or []:
        for block in getattr(step, "content", []) or []:
            for annotation in getattr(block, "annotations", []) or []:
                value = str(getattr(annotation, "model_dump", lambda **_: {})())
                urls.update(re.findall(r"https://support\.optisigns\.com/hc/en-us/articles/[0-9]+[^'\\\"\\\\r\\\\n ]*", value))
    return sorted(urls)[:3]


@app.get("/")
def home():
    return render_template_string(PAGE)


@app.post("/ask")
def ask():
    question = (request.json or {}).get("question", "").strip()
    if not question:
        return jsonify(error="Please enter a question."), 400
    try:
        client, store = client_and_store()
        instructions = (ROOT / "optibot-system-prompt.txt").read_text(encoding="utf-8").strip()
        interaction = client.interactions.create(model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"), system_instruction=instructions, input=question, tools=[{"type": "file_search", "file_search_store_names": [store.name]}])
        return jsonify(answer=interaction.output_text, sources=source_urls(interaction))
    except Exception as exc:
        return jsonify(error=str(exc)), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
