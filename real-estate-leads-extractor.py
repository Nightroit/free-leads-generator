#!/usr/bin/env python3
"""
PDF Email Extractor (Heuristic Filter)
Extracts email addresses from PDFs and keeps only likely personal/individual ones.
Discards generic role-based addresses (hr, sales, info, etc.).

Usage:
    python real-estate-leads-extractor.py "C:\\Users\\lenovo\\Downloads"
"""

import sys
import re
import csv
from pathlib import Path
from collections import defaultdict

try:
    import pymupdf
except ImportError:
    print("Missing dependency. Run: pip install pymupdf")
    sys.exit(1)

EMAIL_REGEX = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
    re.IGNORECASE
)

DISCARD_KEYWORDS = {
    "hr", "humanresources", "human.resources",
    "sales", "sale",
    "info", "information",
    "support", "help", "helpdesk",
    "admin", "administrator",
    "contact", "enquiry", "inquiry", "enquiries",
    "marketing", "market",
    "hello", "hi", "office",
    "team", "careers", "jobs", "recruitment", "recruit",
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "accounts", "accounting", "finance", "billing",
    "press", "media", "pr",
    "webmaster", "postmaster",
}

GENERIC_PREFIXES = {
    "hr", "sales", "info", "support", "admin", "contact",
    "enquiry", "inquiry", "marketing", "hello", "office",
    "team", "careers", "jobs", "recruitment",
}

def extract_text_from_pdf(pdf_path: Path) -> str:
    text = ""
    try:
        with pymupdf.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text() or ""
    except Exception as e:
        print(f"  [WARN] Could not read {pdf_path.name}: {e}")
    return text

def looks_like_personal_name(local_part: str) -> bool:
    local = local_part.lower().strip()

    if any(kw in local for kw in DISCARD_KEYWORDS):
        return False

    for prefix in GENERIC_PREFIXES:
        if local.startswith(prefix + ".") or local.startswith(prefix + "_") or local == prefix:
            return False

    if len(local) < 3 or local.isdigit():
        return False

    has_separator = any(sep in local for sep in (".", "_", "-"))
    parts = re.split(r'[._\-]', local)
    has_multiple_parts = len(parts) >= 2

    if has_separator or has_multiple_parts:
        return True

    if re.fullmatch(r'[a-z]{4,}', local) and not any(c.isdigit() for c in local):
        return True

    return False

def process_directory(root_dir: str, output_csv: str = "useful_emails.csv"):
    # Clean the path (strip quotes, whitespace, trailing > etc.)
    cleaned = root_dir.strip().strip('"').strip("'").rstrip(">").rstrip()
    root = Path(cleaned)

    if not root.exists() or not root.is_dir():
        print(f"Directory not found: {root}")
        print("Tip: Make sure the path is correct and does not end with > or extra spaces.")
        return

    results = defaultdict(set)
    pdf_count = 0

    print(f"Scanning: {root.resolve()}")
    print("-" * 50)

    for pdf_path in root.rglob("*.pdf"):
        pdf_count += 1
        print(f"[{pdf_count}] {pdf_path.name}")

        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            continue

        for raw_email in EMAIL_REGEX.findall(text):
            email = raw_email.lower().strip()
            local = email.split("@")[0]
            if looks_like_personal_name(local):
                results[email].add(pdf_path.name)

    unique_emails = sorted(results.keys())
    print("-" * 50)
    print(f"PDFs scanned: {pdf_count}")
    print(f"Useful personal emails found: {len(unique_emails)}")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "source_pdfs"])
        for email in unique_emails:
            sources = "; ".join(sorted(results[email]))
            writer.writerow([email, sources])

    print(f"Saved to: {Path(output_csv).resolve()}")

def main():
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = input("Enter path to folder containing PDFs: ").strip()

    if not directory:
        print("No directory given.")
        return

    process_directory(directory)

if __name__ == "__main__":
    main()