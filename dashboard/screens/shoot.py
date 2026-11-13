"""Screenshot each dashboard view's section for the README: python dashboard/screens/shoot.py"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[2]; SRC = ROOT / "dashboard/dist/index.html"; OUT = ROOT / "dashboard/screens"
VIEWS = ["overview", "models", "format", "pressure", "ratings", "debates", "self-report", "name-or-text", "reference"]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for v in VIEWS:   # fresh page per view, so no page transition is running during the shot
            pg = await b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme="light")
            await pg.goto(f"file://{SRC}#{v}", wait_until="networkidle"); await pg.add_style_tag(content=".navbar{position:static !important}"); await pg.wait_for_timeout(1500)   # the menu bar stays at the top of the page, not over the section
            await pg.locator(f"#v-{v}").screenshot(path=str(OUT / f"{v}.png")); print("shot", v); await pg.close()
        await b.close()
asyncio.run(main())
