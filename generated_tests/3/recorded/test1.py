from playwright.async_api import async_playwright
import asyncio

async def test_recorded_actions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://www.wikipedia.org')
        await page.click('#searchInput')
        await page.fill('#searchInput', 'kannada')
        await page.click('.pure-button.pure-button-primary-progressive')
        await page.click('#searchInput')
        await page.click('.cdx-button.cdx-button--action-default.cdx-button--weight-normal.cdx-button--size-medium.cdx-button--framed.cdx-search-input__end-button')
        await page.fill('[name="search"]', 'german')
        await page.click('.cdx-button.cdx-button--action-default.cdx-button--weight-normal.cdx-button--size-medium.cdx-button--framed.cdx-search-input__end-button')
        await browser.close()
asyncio.run(test_recorded_actions())