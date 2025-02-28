from datetime import datetime, timezone
import re
import asyncio
from zoneinfo import ZoneInfo
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
    
    async def _login_access(self) -> list:
        listagem = []
        await self.page.goto("https://veri.bet/simulator", timeout=50000)

        # Access to simulator button
        await self.page.locator("button", has_text="Odds / Picks").click()
        await self.page.wait_for_selector("#odds-picks_filter")
        await self.page.wait_for_timeout(5000)

        # Selecte the upcoming option
        await self.page.get_by_role("link", name="upcoming").click(timeout=10000)
        await self.page.wait_for_selector("#odds-picks_filter")

        html = await self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table", {"style": "margin-top: 12px; margin-bottom: 15px;"})

        for table in tables:
            lines = table.find_all("tr")
            league = re.search(r"sport=(.*?)\"", str(table), re.S).group(1)
            teams = re.findall(r"betting-trends.*?font-size:\s\.\d*rem\;\">(.*?)<", str(table), re.S)
            
            # Date conversion to timestamp
            game_date = re.search(r"(\d:\d*\s.*?\))", str(table), re.S).group(1)
           
            hour = re.search(r"(\d*\:\d*\s\w{2})", str(game_date), re.S)[1]
            date = re.search(r"(\d*\/\d*\/\d{4})", str(game_date), re.S)[1].replace("0:00 AM", "12:00 AM") 
        
            # Converting to date time
            date = datetime.strptime(f'{hour} {date}', "%I:%M %p %m/%d/%Y").replace(tzinfo=ZoneInfo("America/New_York"))

            # Converting to UTC
            dt_utc = date.astimezone(ZoneInfo("UTC"))

            # Parsin to ISO
            date_iso = dt_utc.date().isoformat()

            for line in lines[1:]:
                span = line.find_all("span")
                try:
                    spread = re.search(r"(.*?)\s*\(", span[2].text.strip(), re.S).group(1)
                    item = Item(
                        sport_league=league,
                        event_date_utc=date_iso,
                        team1=teams[0],
                        team2=teams[1],
                        pitcher="",
                        period="FULL GAME",
                        line_type="moneyline",
                        price=span[1].text.strip(),
                        side=span[0].text.strip(),
                        team=span[0].text.strip(),
                        spread=float(spread),
                    )
                    print(item)
                    print('==========')
                except (IndexError, AttributeError):
                    continue
                listagem.append(item)
        return listagem
            
async def main() -> None:
    item = Item()
    await item.playwright_start()
    for _ in range(3):
        try:
            await item._login_access()
        except TimeoutError:
            continue
    await item.playwright_finish()

if __name__ == "__main__":
    asyncio.run(main())