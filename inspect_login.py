import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://accounts.ginee.com/?redirect_uri=https%3A%2F%2Fchat.ginee.com")
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open("login_page.html", "w") as f:
            f.write(html)
        await browser.close()

asyncio.run(main())
