# Specification

## Objective

Develop a tool that automatically generates an llms.txt file for a given website by analyzing its structure and content. Additionally, implement a mechanism to keep the llms.txt file updated as the website evolves.

## Background

The llms.txt file is a proposed standard designed to help Large Language Models (LLMs) better understand and interact with website content. Similar to robots.txt, which guides search engine crawlers, llms.txt provides structured information tailored for AI systems, enhancing their ability to process and utilize web data effectively.

## Assignment Tasks

Create a tool, application, or SDK that covers the following components:

1. Website Analysis and Content Extraction:
	- Develop a crawler that traverses the website to identify key pages and extract relevant metadata, such as titles, descriptions, and URLs.
2. llms.txt File Generation:
	- Structure the extracted data into the llms.txt format, adhering to the standard specifications.
3. Automated Updates:
	- Implement a monitoring system that detects changes in the website's structure or content and updates the llms.txt file accordingly.
4. Documentation:
	- Provide clear instructions on how to set up, configure, and use the tool.
    

Build a web application the user directly visits to create the llms.txt, or you might consider an SDK that could be used in popular development frameworks/tools such as Next.js/Vercel. 

## Evaluation Criteria

- Functionality: The tool should accurately generate an llms.txt file that reflects the website's structure and content.
- Automation: The update mechanism should effectively detect changes and refresh the llms.txt file without manual intervention.
- Code Quality: The code should be well-structured, readable, and maintainable.
- Documentation: Clear and comprehensive documentation should accompany the tool, facilitating easy setup and usage.
    

## Additional Resources

- llms.txt Specification:
	- [https://llmstxt.org/](https://llmstxt.org/)
- Examples:
	- [https://llmstxt.site/](https://llmstxt.site/)
- Getting Started with llms.txt:
	- [https://llmstxthub.com/guides/getting-started-llms-txt](https://llmstxthub.com/guides/getting-started-llms-txt)
## Deliverables
- Live and deployed version of the application before you present.
- Source code of the tool, including any scripts or modules developed.
- Documentation detailing the tool's functionality, setup instructions, and any dependencies.

# High-level architecture (MVP → scalable)

- **Frontend (UI)**: Next.js app (React) deployed to Vercel — fast to build, easy serverless hosting, good DX.
    
- **Backend API**: Next.js API routes for light requests + a separate background worker service for crawling and heavy tasks.
    
- **Crawler/Renderer**: Two-mode crawler:
    
    - **Fast mode**: HTTP fetch + Cheerio (no JS rendering) — used by default for speed and cost.
        
    - **JS mode (optional)**: Playwright running in a Docker container on Google Cloud Run (or AWS Fargate/Cloud Run) for sites requiring JS rendering.
        
- **Job queue & workers**: Enqueue jobs directly to Redis (Upstash for serverless-friendly Redis) and process them with a Python-based worker running on Cloud Run.
    
- **Database / Storage**: PostgreSQL (hosted via Supabase or Neon) to store projects, configs, site snapshots, hashes, and generated `llms.txt`. Use object storage (S3 / Supabase Storage) to store generated files / exported artifacts.
    
- **Scheduler / Monitoring**: Cloud cron (Google Cloud Scheduler / Vercel Cron / GitHub Actions scheduled workflow) or internal scheduler to push jobs into Redis for the Python workers to pick up; monitoring remains the same.
    
- **Hosting**: Frontend on Vercel; worker(s) in Cloud Run / AWS ECS Fargate (Docker) to allow Playwright; DB + Redis cloud-managed. CI via GitHub Actions.
    
- **Observability**: Sentry for errors, basic Prometheus-style metrics or Datadog; logs to Logflare or centralized logging.
    

Why these choices?

- Next.js + Vercel = fastest route to a deployable web UI and small API endpoints.
    
- Playwright in Docker on Cloud Run = robust JS rendering without trying to run headful browsers inside Vercel serverless functions.
    
- Supabase/Postgres + Upstash Redis = low ops and very friendly for small teams / MVP.
    
- Redis-backed worker model (e.g., RQ / Dramatiq / Celery with Redis broker) = simple, language-flexible queueing that lets you write workers in Python while keeping a serverless-friendly Redis (Upstash) as the enqueueing layer.
    

---

# Components & responsibilities

## 1) Frontend (Next.js)

Features:

- Simple form: URL, crawl depth, include/exclude patterns, follow external links? JS rendering? rate limit.
- Project dashboard: list sites, last generated `llms.txt`, diff history, change detection status, manual “generate now” button.
    
- Preview & download `llms.txt`.
    
- Webhook / publish options (save to site root by webhook, or provide file for download).
    

Tech:

- Next.js 14 (app router), React, Tailwind CSS (fast UI).
    
- Authentication (optional for MVP): Supabase Auth (email magic link) or GitHub OAuth.
    
- API calls to Next.js API or a dedicated API Gateway.
    

## 2) API surface (Next.js API or small Express/fastify microservice)

Endpoints (examples):

- `POST /api/projects` — create project (url + config).
    
- `GET /api/projects/:id` — project details.
    
- `POST /api/projects/:id/generate` — enqueue a generation run.
    
- `GET /api/projects/:id/llms.txt` — serve latest generated file (or presigned S3 link).
    
- `GET /api/projects/:id/history` — runs + diffs.
    
- `POST /webhooks/publish` — optional webhook for publishing to user's hosting.
    

Authentication: JWT via Supabase or short-lived NextAuth session.

## 3) Crawler / Parser (Worker)

Responsibilities:

- Crawl site per config (respect `robots.txt` and polite rate limits).
    
- Fetch pages (fast mode via axios/fetch; JS mode via Playwright).
    
- Extract metadata: `<title>`, meta description, canonical URL, structured data (JSON-LD), hreflang, sitemap entries.
    
- Compute canonical list of important pages (heuristic: sitemap priority + canonical + internal linking).
    
- Generate llms.txt content per specification.
    
- Store snapshots & compute content hash for change detection.
    

- Libraries:
    
- - Python 3.11+ worker (deployed to Cloud Run)
        
- - `redis-py` + a lightweight queue library (examples: RQ or Dramatiq) or Celery with Redis as broker depending on feature needs
        
- - `httpx` or `requests` for HTTP fetches
        
- - `beautifulsoup4` or `selectolax` for HTML parsing (Cheerio equivalent)
        
- - `playwright` Python bindings for JS-rendered pages (run in the same Cloud Run container when `renderJS` is required)
        
- - sitemap parsing via `python-sitemap` or a small custom parser
        
- - hashing: `hashlib` (SHA256)
    

## 4) Change detection & automated updates

Approach (robust & low-cost):

1. **Sitemap + Headers first**: If site has `sitemap.xml`, fetch and use `LastMod` / URLs; request `HEAD` for ETag/Last-Modified; if unchanged, skip heavy fetch.
    
2.  **Hash-based diff**: For fetched HTML (post-render if needed), compute SHA256 of the normalized important content (strip timestamp-like content). Save hash in DB; if changed — enqueue generation into Redis for Python workers to process.
    
3. **Adaptive polling**: Poll frequency configurable per project (e.g., daily for MVP). Use incremental strategy (frequent for small sites, less frequent for large sites).
    
4. **On-demand webhook**: Allow site owners to POST a webhook to tell the service content updated (e.g., CMS triggers), which enqueues a run immediately.
    

Scheduler:

- Use an internal scheduler in the worker or a cloud cron (Cloud Scheduler / GitHub Actions scheduled job) that enqueues runs into Redis.
    

## 5) Storage model (Postgres) — simplified schema

- `projects` (id, owner_id, url, config/json, last_run_at, status)
    
- `pages` (id, project_id, url, title, description, canonical, hash, last_fetched_at)
    
- `runs` (id, project_id, status, started_at, finished_at, llms_txt_path)
    
- `diffs` (run_id, page_id, change_type, summary)
    
- `users` (id, email, auth info)
    

Store generated `llms.txt` text in Postgres (small) and put downloadable artifact into S3 / Supabase Storage.

## 6) Generator logic (llms.txt)

- Follow the llms.txt spec (use the external spec docs as reference).
    
- Basic content blocks per spec: `Site`, `Owner`, `Pages`, `Access` rules (if any), `Capabilities`, `CrawlInstructions`, and `Notes` generated from detected metadata.
    
- Example structure (pseudo):
    

```
Site: example.com
Owner: name@example.com
Generated-At: 2025-09-10T12:34:56Z

[Pages]
/  title="Home"  desc="..."
/blog  title="Blog"  desc="..."

[Crawl-Directives]
Disallow: /private
Allow: /public
Render: static  # or js
```

- Allow user-specified overrides (e.g., mark some paths as “do not index for LLMs”, or boost certain sections).
    
- Produce a machine-readable JSON variant in DB plus final `llms.txt` formatted file.
    

---

# Concrete tech stack summary (MVP choices)

- Frontend: **Next.js** (React) on **Vercel**
- Auth & DB: **Supabase** (Postgres + Auth + Storage) — single vendor for speed
- Redis (queue): **Upstash Redis** (serverless) — enqueue jobs directly to Redis
- Queue processing: Python-based queue consumers 
- Worker runtime: **Python 3.11+** in Docker; deploy to **Google Cloud Run** (Cloud Run handles autoscaling for the Python workers; Playwright invoked only when needed)
- Object storage: Supabase Storage or AWS S3
- CI/CD: **GitHub Actions**
- Error/tracing: **Sentry**; logs to **Logflare** or provider
- Monitoring/metrics: lightweight: store metrics in Postgres or push to Datadog (optional)
- Container registry: GitHub Packages or Google Artifact Registry

---

# API & UX details (example request/response)

Create project:

```
POST /api/projects
{
  "url": "https://example.com",
  "config": {
     "crawlDepth": 2,
     "followExternal": false,
     "renderJS": false,
     "includePaths": ["/blog"],
     "excludePaths": ["/private"],
     "pollInterval": "24h"   // configurable
  }
}
```

Response:

```
{ "projectId": "p_123", "status":"queued" }
```

Generate / preview:

```
POST /api/projects/p_123/generate?preview=true
-> returns JSON { llmsTxt: "Site: ...", pages: [...] }
```

Serve file:  
`GET /api/projects/p_123/llms.txt` → returns text/plain with `llms.txt` content or 302 to presigned file in storage.

---

# Security, legality, and politeness

- **Respect `robots.txt`** by default; allow advanced users to override (but warn).
    
- Rate limiting per site: default e.g., 1 request/sec, burst=3.
    
- IP disclosure: when crawling, set a polite `User-Agent` and include contact email.
    
- Do not store or expose sensitive content scraped from password-protected areas.
    
- Provide opt-in verification for “publish to site root” flows (e.g., user proves control by adding a token file to `/.well-known/llms-generator.txt` or similar).
    

---

# Deployment model and cost-conscious MVP plan

MVP deployment suggestion:

- Frontend: Vercel Hobby (free tier) — instant deploys from GitHub.
    
- DB: Supabase free tier for prototyping.
    
- Redis: Upstash free tier.
    
- Worker: Cloud Run with 1 small instance; Playwright only invoked when needed to limit runtime cost.
    
- Storage: Supabase Storage.
    

Scaling notes:

- Migrate Postgres to a larger provider (Neon/RDS) as DB grows.
    
- Use autoscaling for Cloud Run workers; increase concurrency in workers for CPU bound tasks.
    
- For large-scale crawling consider segmenting workers by region and caching DNS.
    

---

# Example generation algorithm (step-by-step)

1. Input: `url`, config.
    
2. Fetch `robots.txt` and `sitemap.xml`.
    
3. Build initial URL set: homepage + sitemap URLs filtered by include/exclude rules.
    
4. For each URL (BFS up to crawlDepth):
    
    - If `renderJS` false: GET + parse with cheerio.
        
    - If `renderJS` true OR content seems dynamic: render via Playwright and then parse.
        
    - Extract metadata: title, meta-desc, canonical, JSON-LD, headings, internal link count.
        
    - Normalize content (strip timestamps, inline scripts).
        
    - Compute `hash = sha256(normalized_content)`.
        
    - If hash changed vs DB: mark changed.
        
5. Rank pages by importance (sitemap priority + inbound link count + heuristics).
    
6. Build `llms.txt` JSON and human-readable text per spec. Include `Generated-At` and optional `diff` notes.
    
7. Save run, publish artifact, and (optionally) call publish webhook.
    

---

# MVP scope checklist (deliverables)

-  Web form to create project + config
    
-  Backend endpoints to enqueue generation
    
-  Worker that crawls site (cheerio mode) and generates `llms.txt`
    
-  Storage and serving of generated `llms.txt` (download + preview)
    
-  Simple scheduler for periodic polling
    
-  Basic changelog/diff view for runs
    
-  Documentation/README with setup & deploy steps (include how to run Playwright worker locally)
    
-  Demo screenshots / short video

(These map to the requirements in the project brief).

---

# Extensions & future improvements

- Integrate automatic `llms.txt` deployment to site root: provide short-lived presigned upload, or use GitHub Action to push to repo if user provides repo access.
    
- Add a “site-owner verification” flow (DNS TXT or file) so verified owners can enable automatic publish.
    
- Heavier ML-powered content summarization (create short snippets for each page using an LLM) — careful with cost.
    
- Support incremental crawl webhooks and real-time update processing.
    
- Add team features, multi-tenant dashboards, and fine-grained per-path rules.
    

---

# Risks & trade-offs

- **Playwright cost/complexity**: JS rendering is expensive. MVP should keep it optional and on-demand.
    
- **Politeness & legal**: Aggressive crawling can cause load; default to conservative rate limits and honor `robots.txt`.
    
- **Accuracy of heuristics**: Heuristics for “important pages” will need tuning—provide user overrides.