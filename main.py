import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from markdownify import markdownify

ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "articles"
ARTIFACTS_DIR = ROOT / "artifacts"
BASE_URL = "https://support.optisigns.com"
API_URL = f"{BASE_URL}/api/v2/help_center/en-us/articles.json?per_page=100"
STORE_NAME = "OptiSigns Support Knowledge Base"
REQUIRED_IDS = {"360051014713"}
LIMIT = int(os.getenv("ARTICLE_LIMIT", "40"))
MAX_TOKENS = 512
OVERLAP_TOKENS = 128


def slugify(value):
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:90] or "article"


def filename(article):
    return f"{article['id']}-{slugify(article['title'])}.md"


def fetch_json(url):
    response = requests.get(url, timeout=30, headers={"User-Agent": "daily-doc-sync/1.0"})
    response.raise_for_status()
    return response.json()


def fetch_articles():
    articles = []
    url = API_URL
    while url and len(articles) < LIMIT:
        page = fetch_json(url)
        articles.extend(page["articles"])
        url = page.get("next_page")
    articles = articles[:LIMIT]
    known = {str(article["id"]) for article in articles}
    for article_id in REQUIRED_IDS - known:
        item = fetch_json(f"{BASE_URL}/api/v2/help_center/en-us/articles/{article_id}.json")
        articles.append(item["article"])
    return articles


def local_link(href, files_by_id):
    parsed = urlparse(urljoin(BASE_URL, href))
    if parsed.netloc != "support.optisigns.com":
        return href
    match = re.search(r"/articles/(\d+)", parsed.path)
    if not match or match.group(1) not in files_by_id:
        return href
    return f"./{files_by_id[match.group(1)]}{('#' + parsed.fragment) if parsed.fragment else ''}"


def clean_markdown(article, files_by_id):
    soup = BeautifulSoup(article.get("body") or "", "html.parser")
    for element in soup.select("script, style, nav, header, footer, form"):
        element.decompose()
    for link in soup.select("a[href]"):
        link["href"] = local_link(link["href"], files_by_id)
    body = markdownify(str(soup), heading_style="ATX", bullets="-")
    body = body.replace("\u00a0", " ")
    body = re.sub(r"[ \t]+$", "", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return f"# {article['title']}\n\nArticle URL: {article['html_url']}\n\n{body}\n"


def scrape():
    articles = fetch_articles()
    files_by_id = {str(article["id"]): filename(article) for article in articles}
    records = []
    ARTICLES_DIR.mkdir(exist_ok=True)
    for article in articles:
        content = clean_markdown(article, files_by_id)
        path = ARTICLES_DIR / files_by_id[str(article["id"])]
        path.write_text(content, encoding="utf-8")
        records.append({
            "article_id": str(article["id"]),
            "filename": path.name,
            "source_url": article["html_url"],
            "updated_at": article["updated_at"],
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "path": path,
        })
    return records


def metadata(document):
    result = {}
    for item in document.custom_metadata or []:
        value = getattr(item, "string_value", None)
        if value is not None:
            result[item.key] = value
    return result


def get_store(client):
    stores = [store for store in client.file_search_stores.list() if store.display_name == STORE_NAME]
    if stores:
        return stores[0]
    return client.file_search_stores.create(config={
        "display_name": STORE_NAME,
        "embedding_model": "models/gemini-embedding-2",
    })


def wait_for(client, operation):
    while not operation.done:
        time.sleep(3)
        operation = client.operations.get(operation)
    if getattr(operation, "error", None):
        raise RuntimeError(str(operation.error))


def upload(client, store, record):
    operation = client.file_search_stores.upload_to_file_search_store(
        file=str(record["path"]),
        file_search_store_name=store.name,
        config={
            "display_name": record["filename"],
            "custom_metadata": [
                {"key": "article_id", "string_value": record["article_id"]},
                {"key": "content_hash", "string_value": record["content_hash"]},
                {"key": "source_url", "string_value": record["source_url"]},
            ],
            "chunking_config": {
                "white_space_config": {
                    "max_tokens_per_chunk": MAX_TOKENS,
                    "max_overlap_tokens": OVERLAP_TOKENS,
                }
            },
        },
    )
    wait_for(client, operation)


def sync(records):
    key = os.getenv("API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("API_KEY is required")
    client = genai.Client(api_key=key)
    store = get_store(client)
    documents = list(client.file_search_stores.documents.list(parent=store.name))
    by_id = {}
    by_name = {}
    for document in documents:
        values = metadata(document)
        if values.get("article_id"):
            by_id[values["article_id"]] = document
        by_name[document.display_name] = document
    counts = {"added": 0, "updated": 0, "skipped": 0}
    for record in records:
        document = by_id.get(record["article_id"]) or by_name.get(record["filename"])
        if document and metadata(document).get("content_hash") == record["content_hash"]:
            counts["skipped"] += 1
            continue
        if document:
            client.file_search_stores.documents.delete(name=document.name, config={"force": True})
            counts["updated"] += 1
        else:
            counts["added"] += 1
        upload(client, store, record)
    return store.name, counts


def save_report(store_name, counts, total):
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "store": store_name,
        "scraped": total,
        **counts,
    }
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    path = ARTIFACTS_DIR / "last-run.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


def main():
    load_dotenv(ROOT / ".env.local")
    records = scrape()
    store_name, counts = sync(records)
    save_report(store_name, counts, len(records))


if __name__ == "__main__":
    main()
