
import re

def extract_form_key2(js_text: str) -> str | None:
    match = re.search(r'key:"initUploader".*?d\s*=\s*"([A-Za-z0-9]+)"', js_text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'd\s*=\s*"([A-Za-z0-9]{10,})"', js_text)
    return match.group(1) if match else None

def extract_all_js_urls(html: str):
    return re.findall(r'<script[^>]+src="([^"]*\.js[^"]*)"', html)
