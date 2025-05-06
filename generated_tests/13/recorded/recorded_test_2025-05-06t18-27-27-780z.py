from playwright.async_api import async_playwright
import asyncio

async def test_recorded_actions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://mail.google.com/')
        await page.fill('#identifierId', 'j')
        await page.fill('#identifierId', 'jj')
        await page.fill('#identifierId', 'jjj')
        await page.click('.VfPpkd-vQzf8d')
        await browser.close()
asyncio.run(test_recorded_actions())