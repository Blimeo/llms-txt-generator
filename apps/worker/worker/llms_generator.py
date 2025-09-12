# apps/worker/worker/llms_generator.py
import json
from datetime import datetime
from typing import Dict, Any, List
import os


def generate_llms_text(crawl_result: Dict[str, Any], job_id: str) -> str:
    """
    Generate a textual artifact representing crawl results.
    Returns path to the generated file (local path).
    """
    now = datetime.utcnow().isoformat() + "Z"
    header = {
        "generated_at": now,
        "job_id": job_id,
        "start_url": crawl_result.get("start_url"),
        "pages_crawled": crawl_result.get("pages_crawled"),
    }

    filename = f"llms_{job_id}.txt"
    outpath = os.path.abspath(os.path.join(os.getcwd(), filename))

    lines = []
    lines.append("# llms.txt generated artifact")
    lines.append(json.dumps(header))
    lines.append("")  # blank
    pages: List[Dict[str, Any]] = crawl_result.get("pages", [])
    for i, p in enumerate(pages, start=1):
        lines.append(f"--- PAGE {i} ---")
        lines.append(f"URL: {p.get('url')}")
        lines.append(f"Status: {p.get('status_code')}")
        title = p.get("title", "")
        if title:
            lines.append(f"Title: {title}")
        desc = p.get("description", "")
        if desc:
            lines.append(f"Description: {desc}")
        headings = p.get("headings", [])
        if headings:
            lines.append("Headings:")
            for h in headings[:10]:
                lines.append(f"  - {h}")
        snippet = p.get("snippet", "")
        if snippet:
            lines.append("Snippet:")
            lines.append(snippet)
        lines.append("")  # blank

    # Also write a JSON variant for machine parsing
    jsonpath = os.path.abspath(os.path.join(os.getcwd(), f"llms_{job_id}.json"))
    with open(outpath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    with open(jsonpath, "w", encoding="utf-8") as fj:
        json.dump({"meta": header, "pages": pages}, fj, indent=2, ensure_ascii=False)

    # return both paths as a tuple or choose outpath
    return outpath, jsonpath
