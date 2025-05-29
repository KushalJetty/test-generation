from playwright.async_api import async_playwright
import asyncio

async def test_recorded_actions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://test.teamstreamz.com')
        await page.click('#Username')
        await page.fill('#Username', 'kushal.jetty@teamstreamz.com')
        await page.fill('#Password', 'Test@123')
        await page.click('.btn.signin-btn.bg-primary.ng-tns-c813547932-0')
        await page.click('span')
        await page.click('h5')
        await browser.close()
asyncio.run(test_recorded_actions())