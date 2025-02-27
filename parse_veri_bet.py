import re
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError
from dataclasses import dataclass

@dataclass
class Item:
    sport_league: str = ''
    event_date_utc: str = ''
    team1: str = '' 
    team2: str = '' 
    pitcher: str = ''
    period: str = ''
    line_type: str = ''
    price: str = ''
    side: str = ''     
    team: str = ''
    spread: float = 0.0
    
    async def playwright_start(self) -> None:
        # Playwright inicialization
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.page.set_default_timeout(600000)

    async def playwright_finish(self) -> None:
        # Playwright finish
        await self.context.close()
        await self.playwright.stop()
        await self.browser.close()
    
    async def _login_access(self):
        await self.page.goto("https://veri.bet/simulator", timeout=50000)

        # Access to simulator button
        await self.page.locator("button", has_text="Odds / Picks").click()
        await self.page.wait_for_selector("#odds-picks_filter")
        await self.page.wait_for_timeout(5000)

        html = await self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"class": "display no-footer dataTable"})
        lines = table.find_all("tr", {"role": "even"})

        for line in lines:
            td = line.find_all("td")
            if not td:
                continue
            print(td)

async def main() -> None:
    item = Item()
    await item.playwright_start()
    try:
        await item._login_access()
    except TimeoutError:
        raise TimeoutError("Connection error! Try again later!")
    await item.playwright_finish()

if __name__ == "__main__":
    asyncio.run(main())