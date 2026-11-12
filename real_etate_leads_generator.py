"""
Bing PDF Downloader (more aggressive)
Searches Bing and downloads anything that looks like a PDF.
"""

import argparse
import os
import re
import time
from urllib.parse import urlparse, quote_plus
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def download_pdf(url: str, save_dir: str) -> str | None:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=30, stream=True, allow_redirects=True)
        content_type = resp.headers.get("content-type", "").lower()
        final_url = resp.url.lower()

        is_pdf = (
            "pdf" in content_type or
            final_url.endswith(".pdf") or
            "pdf" in final_url
        )

        if resp.status_code == 200 and is_pdf:
            parsed = urlparse(resp.url)
            filename = os.path.basename(parsed.path) or "document.pdf"
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            # clean filename
            filename = re.sub(r'[^\w\s.-]', '_', filename)
            filepath = os.path.join(save_dir, filename)
            base, ext = os.path.splitext(filepath)
            counter = 1
            while os.path.exists(filepath):
                filepath = f"{base}_{counter}{ext}"
                counter += 1
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return filepath
        else:
            print(f"    [skip] Not a PDF (content-type={content_type[:40]}, url={final_url[:60]})")
    except Exception as e:
        print(f"[!] Download failed for {url}: {e}")
    return None

def scrape_bing_pdfs(keyword: str, max_results: int = 20, headless: bool = True) -> list[str]:
    query = f'"{keyword}" filetype:pdf'
    encoded = quote_plus(query)
    search_url = f"https://www.bing.com/search?q={encoded}&count=10&setlang=en"

    pdf_urls = []
    seen = set()

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        print(f"[*] Searching Bing for: {query}")
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        try:
            page.wait_for_selector("li.b_algo", timeout=15000)
        except:
            print("[!] Results did not load. Try running with --no-headless to see the page.")
            browser.close()
            return pdf_urls

        page_num = 0
        while len(pdf_urls) < max_results and page_num < 4:
            # All result links
            links = page.query_selector_all("li.b_algo h2 a, li.b_algo a")
            print(f"[*] Page {page_num + 1}: found {len(links)} links")

            for link in links:
                href = link.get_attribute("href")
                text = (link.inner_text() or "").lower()
                if not href or not href.startswith("http"):
                    continue
                if href in seen:
                    continue

                # Loose PDF check
                if (".pdf" in href.lower() or
                    "filetype=pdf" in href.lower() or
                    "pdf" in text or
                    "[pdf]" in text):
                    seen.add(href)
                    pdf_urls.append(href)
                    print(f"    + {href[:90]}")
                    if len(pdf_urls) >= max_results:
                        break

            if len(pdf_urls) >= max_results:
                break

            next_btn = page.query_selector("a.sb_pagN, a[title='Next page'], .b_pag a:has-text('Next')")
            if next_btn:
                next_btn.click()
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2.5 + page_num)
                page_num += 1
            else:
                break

        browser.close()

    print(f"[*] Total PDF candidates: {len(pdf_urls)}")
    return pdf_urls

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", help="Search keyword")
    parser.add_argument("--max", type=int, default=10, help="Max PDFs to try downloading")
    parser.add_argument("--no-headless", action="store_true", help="Show browser")
    args = parser.parse_args()

    keyword = args.keyword.strip()
    if not keyword:
        print("Keyword cannot be empty.")
        return

    safe_name = re.sub(r'[^\w\s-]', '', keyword).strip().replace(" ", "_")
    folder = f"pdfs_{safe_name}"
    os.makedirs(folder, exist_ok=True)
    print(f"[*] Saving to: {folder}/")

    pdf_urls = scrape_bing_pdfs(keyword, max_results=args.max, headless=not args.no_headless)

    downloaded = 0
    for i, url in enumerate(pdf_urls, 1):
        print(f"\n[{i}/{len(pdf_urls)}] Trying: {url[:80]}...")
        path = download_pdf(url, folder)
        if path:
            downloaded += 1
            print(f"    SAVED -> {path}")
        time.sleep(1)

    print(f"\n[+] Finished. Downloaded {downloaded} PDFs into {folder}/")

if __name__ == "__main__":
    main()