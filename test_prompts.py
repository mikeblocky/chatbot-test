import json
import os
from datetime import datetime, timezone
from pathlib import Path

from google import genai

ROOT = Path(__file__).parent
STORE_NAME = "OptiSigns Support Knowledge Base"
PROMPTS = [
    "How do I add a YouTube video?",
    "What do I get with the free plan?",
    "How do I connect Microsoft Teams Rooms to digital signage?",
]


def citations(interaction):
    items = []
    for step in interaction.steps or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for block in getattr(step, "content", []) or []:
            for annotation in getattr(block, "annotations", []) or []:
                if getattr(annotation, "type", None) == "file_citation":
                    items.append(annotation.model_dump(mode="json"))
    return items


def main():
    key = os.getenv("API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("API_KEY is required")
    client = genai.Client(api_key=key)
    stores = [store for store in client.file_search_stores.list() if store.display_name == STORE_NAME]
    if not stores:
        raise RuntimeError("File Search store not found")
    instructions = (ROOT / "optibot-system-prompt.txt").read_text(encoding="utf-8").strip()
    results = []
    for prompt in PROMPTS:
        interaction = client.interactions.create(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            system_instruction=instructions,
            input=prompt,
            tools=[{
                "type": "file_search",
                "file_search_store_names": [stores[0].name],
            }],
        )
        result = {
            "prompt": prompt,
            "answer": interaction.output_text,
            "citations": citations(interaction),
            "interaction_id": interaction.id,
        }
        results.append(result)
        print(json.dumps({
            "prompt": prompt,
            "answer": interaction.output_text,
            "citation_count": len(result["citations"]),
        }, ensure_ascii=False))
    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        "store": stores[0].name,
        "tests": results,
    }
    path = ROOT / "artifacts" / "prompt-test-results.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
