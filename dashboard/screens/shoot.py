"""Screenshot each dashboard view's section for the README: python dashboard/screens/shoot.py"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[2]; SRC = ROOT / "dashboard/dist/index.html"; OUT = ROOT / "dashboard/screens"
VIEWS = ["overview", "models", "format", "pressure", "ratings", "debates", "self-report"]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme="light")
        for v in VIEWS:
            await pg.goto(f"file://{SRC}#{v}"); await pg.wait_for_timeout(1200)
            await pg.locator(f"#v-{v}").screenshot(path=str(OUT / f"{v}.png")); print("shot", v)
        await b.close()
asyncio.run(main())
