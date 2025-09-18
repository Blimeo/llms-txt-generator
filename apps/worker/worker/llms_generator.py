# apps/worker/worker/llms_generator.py
"""Generate LLMS.txt formatted content from crawl results."""

from datetime import datetime
from typing import Dict, Any, List


def generate_llms_text(crawl_result: Dict[str, Any], job_id: str) -> str:
    """
    Generate a textual artifact representing crawl results in LLMS.txt format.
    Returns txt_content as string in memory.
    """
    pages: List[Dict[str, Any]] = crawl_result.get("pages", [])
    
    # Extract project information from the start page (first page or homepage)
    start_page = None
    for page in pages:
        if page.get("url") == crawl_result.get("start_url"):
            start_page = page
            break
    
    # If no start page found, use the first page
    if not start_page and pages:
        start_page = pages[0]
    
    # Get project name from start page title or URL
    project_name = "Website"
    if start_page:
        title = start_page.get("title", "").strip()
        if title:
            project_name = title
        else:
            # Fallback to domain name from start URL
            start_url = crawl_result.get("start_url", "")
            if start_url:
                from urllib.parse import urlparse
                parsed = urlparse(start_url)
                project_name = parsed.netloc or start_url
    
    # Get project description from start page
    project_description = ""
    if start_page:
        desc = start_page.get("description", "").strip()
        if desc:
            project_description = desc
        else:
            # Fallback to a generic description
            project_description = f"Website content from {crawl_result.get('start_url', '')}"
    
    # Build LLMS.txt content
    lines = []
    
    # H1 with project name
    lines.append(f"# {project_name}")
    lines.append("")
    
    # Blockquote with project description
    lines.append(f"> {project_description}")
    lines.append("")
    
    # H2 for pages section
    lines.append("## Pages")
    lines.append("")
    
    # Add pages as markdown links
    for page in pages:
        url = page.get("url", "")
        title = page.get("title", "").strip()
        description = page.get("description", "").strip()
        
        if not url:
            continue
            
        # Use title if available, otherwise use URL
        link_title = title if title else url
        
        # Format as markdown link
        if description:
            lines.append(f"- [{link_title}]({url}): {description}")
        else:
            lines.append(f"- [{link_title}]({url})")
    
    # Generate content in memory
    txt_content = "\n".join(lines)
    
    return txt_content
