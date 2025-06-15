#!/usr/bin/env python3
"""
Single-file CLI tool to ingest predefined HTML sources and local PDFs into JSON records for your knowledge base.

Dependencies (install once):
  pip install requests beautifulsoup4 pdfminer.six typer

Usage:
  python cli.py scrape-html <start_url> [--list-sel <selector>] [--link-sel <selector>]
  python cli.py scrape-pdf <path_to_pdf>
  python cli.py scrape-all
"""

import os
import uuid
import json
import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
import typer

app = typer.Typer()

# Hardcoded sources
PREDEFINED_SOURCES = [
    {
        "name": "interviewing_blog",
        "type": "html",
        "start_url": "https://interviewing.io/blog",
        "list_sel": "h1",
        "link_sel": "a"
    },
    {
        "name": "company_guides",
        "type": "html",
        "start_url": "https://interviewing.io/topics#companies",
        "list_sel": ".markdown-content",
        "link_sel": "a[href*='/topics/']"
    },
    {
        "name": "interview_guides",
        "type": "html",
        "start_url": "https://interviewing.io/learn#interview-guides",
        "list_sel": ".markdown-content",
        "link_sel": "a[href*='/learn/']"
    },
    {
        "name": "nil_dsablog",
        "type": "html",
        "start_url": "https://nilmamano.com/blog/category/dsa",
        "list_sel": "article",
        "link_sel": "a"
    }
]
PDF_FOLDER = "data/pdfs"


class BaseScraper:
    """Abstract base for scrapers."""

    def list_pages(self):
        raise NotImplementedError

    def fetch_page(self, url):
        raise NotImplementedError

    def parse_items(self, page_content):
        raise NotImplementedError

    def extract_content(self, item_url):
        raise NotImplementedError

    def run(self):
        for page in self.list_pages():
            content = self.fetch_page(page)
            for item in self.parse_items(content):
                yield self.extract_content(item)


class HtmlScraper(BaseScraper):
    def __init__(self, start_url: str, list_selector: str, link_selector: str):
        self.start_url = start_url
        self.list_selector = list_selector
        self.link_selector = link_selector

    def list_pages(self):
        return [self.start_url]

    def fetch_page(self, url):
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text

    def parse_items(self, page_content):
        soup = BeautifulSoup(page_content, "html.parser")
        items = []
        for a in soup.select(f"{self.list_selector} {self.link_selector}"):
            href = a.get("href")
            if href:
                items.append(href if href.startswith("http")
                             else requests.compat.urljoin(self.start_url, href))
        return items

    def extract_content(self, item_url):
        html = self.fetch_page(item_url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1").get_text(
            strip=True) if soup.find("h1") else None
        date = None
        time_tag = soup.find("time")
        if time_tag and time_tag.has_attr("datetime"):
            date = time_tag["datetime"]
        author = soup.select_one(".author").get_text(
            strip=True) if soup.select_one(".author") else None
        paragraphs = [p.get_text(strip=True) for p in soup.select(
            "article p, .post-content p, .content p")]
        content = "\n\n".join(paragraphs)
        return {
            "id":      str(uuid.uuid4()),
            "source":  self.start_url,
            "url":     item_url,
            "title":   title,
            "author":  author,
            "date":    date,
            "content": content
        }


class PDFScraper(BaseScraper):
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def list_pages(self):
        return [self.pdf_path]

    def fetch_page(self, path):
        with open(path, "rb") as f:
            return f.read()

    def parse_items(self, page_content):
        return [self.pdf_path]

    def extract_content(self, item):
        text = extract_text(item)
        return {
            "id":      str(uuid.uuid4()),
            "source":  os.path.basename(item),
            "content": text
        }


@app.command()
def scrape_html(
    start_url: str = typer.Argument(..., help="Landing page URL"),
    list_sel:   str = typer.Option(
        "article", "--list-sel", help="CSS selector for list container"),
    link_sel:   str = typer.Option(
        "a",       "--link-sel", help="CSS selector for item links")
):
    """Scrape HTML-based blog or guide into JSON records."""
    scraper = HtmlScraper(start_url, list_sel, link_sel)
    for rec in scraper.run():
        typer.echo(json.dumps(rec, ensure_ascii=False))


@app.command()
def scrape_pdf(
    pdf_path: str = typer.Argument(..., help="Path to PDF file")
):
    """Scrape a local PDF into JSON record."""
    scraper = PDFScraper(pdf_path)
    for rec in scraper.run():
        typer.echo(json.dumps(rec, ensure_ascii=False))


@app.command()
def scrape_all():
    """Scrape all predefined HTML sources and local PDFs."""
    # HTML sources
    for src in PREDEFINED_SOURCES:
        typer.echo(f"--- SCRAPING {src['name']} ({src['start_url']}) ---")
        scraper = HtmlScraper(
            src["start_url"], src["list_sel"], src["link_sel"])
        for rec in scraper.run():
            typer.echo(json.dumps(rec, ensure_ascii=False))
    # PDF sources
    if os.path.isdir(PDF_FOLDER):
        for fname in sorted(os.listdir(PDF_FOLDER)):
            if fname.lower().endswith(".pdf"):
                path = os.path.join(PDF_FOLDER, fname)
                typer.echo(f"--- SCRAPING PDF {fname} ---")
                scraper = PDFScraper(path)
                for rec in scraper.run():
                    typer.echo(json.dumps(rec, ensure_ascii=False))
    else:
        typer.echo(f"PDF folder not found: {PDF_FOLDER}")


if __name__ == "__main__":
    app()


# run python cli.py scrape-all > full_ingest.jsonl

# it should work bruh but i need to go touch grass, so if it doesn't, oh well you know i tried g
