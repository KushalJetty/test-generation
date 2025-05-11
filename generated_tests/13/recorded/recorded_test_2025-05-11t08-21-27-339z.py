from playwright.async_api import async_playwright
import asyncio

async def test_recorded_actions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://www.wikipedia.org')
        await page.fill('#searchInput', 'english')
        await page.click('.sprite.svg-search-icon')
        await browser.close()
asyncio.run(test_recorded_actions())