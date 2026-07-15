# Project review notes

## What the project does

The job collects support articles and turns them into clean Markdown files. Those files are loaded into Gemini File Search so answers can be based on the support documentation and include source links.

## Why it works this way

The support site provides a Zendesk API, so the job can request the article content directly instead of scraping menus and page layouts. Every file includes its original article URL.

Each file also gets a SHA-256 hash. On the next run, the job compares that hash with the value stored in Gemini. New files are added, changed files are replaced, and unchanged files are skipped.

## How I approached it

I started with one article and one upload, checked the real API responses, and then expanded it to the full set. After the basic flow worked, I added cleanup, change detection, tests, Docker, and the daily schedule.

## What I would improve next

- Detect deleted and renamed articles.
- Add retries and notifications when a scheduled run fails.
- Keep a small set of test questions for checking answer quality.
- Separate documents by product version or customer plan when needed.
- Send uncertain questions to a person instead of guessing.

## Things to watch

Articles can become outdated or contradict each other. Site markup can change. API limits and indexing delays can also affect a run. The most useful checks are document freshness, citation quality, unanswered questions, and scheduled-job failures.
