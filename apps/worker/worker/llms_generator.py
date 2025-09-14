# apps/worker/worker/llms_generator.py
import json
from datetime import datetime
from typing import Dict, Any, List
import os


def generate_llms_text(crawl_result: Dict[str, Any], job_id: str) -> tuple[str, str]:
    """
    Generate a textual artifact representing crawl results.
    Returns tuple of (txt_content, json_content) as strings in memory.
    """
    now = datetime.utcnow().isoformat() + "Z"
    header = {
        "generated_at": now,
        "job_id": job_id,
        "start_url": crawl_result.get("start_url"),
        "pages_crawled": crawl_result.get("pages_crawled"),
    }

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

    # Generate content in memory
    txt_content = "\n".join(lines)
    json_content = json.dumps({"meta": header, "pages": pages}, indent=2, ensure_ascii=False)

    return txt_content, json_content
