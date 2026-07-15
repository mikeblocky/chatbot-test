# Chatbot Test

This project downloads support articles, converts them to Markdown, and keeps a Gemini File Search store up to date. It also includes a small chat page for asking questions against the uploaded support content.

## Run locally

Python 3.12 or newer is recommended.

```bash
git clone https://github.com/mikeblocky/chatbot-test.git
cd chatbot-test
python -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux, use `source .venv/bin/activate` instead.

Install the packages and create the local environment file:

```bash
pip install -r requirements.txt
cp .env.sample .env.local
```

In PowerShell, use `Copy-Item .env.sample .env.local` instead of `cp`.

Open `.env.local` and replace `your_gemini_api_key` with your Gemini API key. Then run:

```bash
python main.py
```

The Markdown files are saved in `articles/`. The run summary is saved to `artifacts/last-run.json` and shows how many articles were added, updated, or skipped.

## Run with Docker

```bash
docker build -t chatbot-test .
docker run --rm -e API_KEY=your_gemini_api_key -v "${PWD}/articles:/app/articles" -v "${PWD}/artifacts:/app/artifacts" chatbot-test
```

The container runs the job once and exits with code 0 when it succeeds.

## Open the chat page

Start the web interface with:

```bash
docker run --rm -p 8080:8080 -e API_KEY=your_gemini_api_key chatbot-test
```

Then open `http://localhost:8080`. DigitalOcean can run the same container as a web service on port 8080.

## Tests

```bash
python -m pytest -q
```

## Daily job

GitHub Actions runs the Docker job every day at 02:17 UTC. It can also be started manually from the Actions page. Every run provides a downloadable `scraped-support-data` artifact containing the normalized Markdown files, the run summary, and the job log.

[View job runs, logs, and last-run artifacts](https://github.com/mikeblocky/chatbot-test/actions/workflows/daily-sync.yml)

## Example answer

![Example answer with its source URL](artifacts/assistant-screenshot.png)
