"""Mengambil screenshot UI untuk README. Prasyarat: backend :8000 (sudah di-seed) dan frontend :5173 berjalan.
Pakai: pip install playwright && playwright install chromium && python scripts/capture_screenshots.py"""
import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets" / "screens"
BASE, API = "http://localhost:5173", "http://localhost:8000/api"


def get(path):
    return json.load(urllib.request.urlopen(API + path))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fid = get("/failures?failure_type=document_version_mismatch&page_size=1")["items"][0]["id"]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

        def shot(name, path, h=900, full=False, before=None):
            pg.set_viewport_size({"width": 1440, "height": h})
            pg.goto(BASE + path, wait_until="networkidle")
            if before:
                before()
            pg.wait_for_timeout(1200)
            pg.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
            print("ok", name)

        shot("dashboard", "/", 1000)

        def play():
            pg.locator("select").last.select_option("v1")
            pg.get_by_role("button", name="Jalankan query").click()
            pg.wait_for_selector("text=Generated answer")

        shot("playground", "/playground", 1250, before=play)
        shot("failure-detail", f"/failures/{fid}", 1250)
        shot("hard-negatives", "/hard-negatives", 820)
        shot("training-center", "/training", 1000)
        shot("ab-testing", "/ab-testing", 900)
        shot("experiments", "/experiments", 1000)
        shot("documents", "/documents", 800)
        b.close()


main()
