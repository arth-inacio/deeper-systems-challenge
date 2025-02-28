from datetime import datetime
import pytz
import re
import asyncio
import json
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError
from dataclasses import asdict, dataclass
from typing import List

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
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.page.set_default_timeout(600000)

    async def playwright_finish(self) -> None:
        # Playwright finish
        await self.context.close()
        await self.playwright.stop()
        await self.browser.close()
    
    async def _login_access(self) -> list:
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

        return  await self._table_extraction(tables)

    async def _table_extraction(self, tables) -> list:
        listing_information = []
        for table in tables:
            lines = table.find_all("tr")
            league = re.search(r"sport=(.*?)\"", str(table), re.S).group(1)
            teams = re.findall(r"betting-trends.*?font-size:\s\.\d*rem\;\">(.*?)<", str(table), re.S)
            
            # Date conversion to timestamp
            try:
                game_date = re.search(r"(\d:\d*\s.*?\))", str(table), re.S).group(1)
                iso_format = await self._timezone_ajust(game_date)
            except(TypeError, AttributeError, ValueError):
                continue

            for line in lines[1:]:
                span = line.find_all("span")
                try:
                    side = span[0].text.strip()
                    if re.search(r"DRAW", str(table), re.S):
                        side = "DRAW"
                    spread = re.search(r"(.*?)\s*\(", span[2].text.strip(), re.S).group(1)

                    if not spread or spread == "0.00":
                        line_type = "moneyline"
                    elif re.search(r"(\d+\.?\d*)", str(spread), re.S):
                        line_type = "over/under"
                    elif re.search(r"([-+]?\d+\.?\d*)", str(spread), re.S):
                        line_type = "spread"

                    item = Item(
                        sport_league=league,
                        event_date_utc=iso_format,
                        team1=teams[0],
                        team2=teams[1],
                        pitcher="",
                        period="FULL GAME",
                        line_type=line_type,
                        price=span[1].text.strip(),
                        side=side,
                        team=side,
                        spread=float(spread),
                    )
                    listing_information.append(item)
                except (IndexError, AttributeError):
                    continue
                break
            print(item)
            print('======')
        return listing_information

    async def _timezone_ajust(self, date: str) -> str:
        hour = re.search(r"(\d*\:\d*\s\w{2})", str(date), re.S)[1]
        date_reg = re.search(r"(\d*\/\d*\/\d{4})", str(date), re.S)[1] 

        # Creates an datetime by string
        et_tz = pytz.timezone("America/New_York")  # ET (Eastern Time)
        utc_tz = pytz.utc  # UTC

        # Converts to datetimew with timezone
        event_datetime = datetime.strptime(f"{date_reg} {hour}", "%m/%d/%Y %I:%M %p")
        event_datetime = et_tz.localize(event_datetime)  # ET defined

        # Convertion to UTC
        event_datetime_utc = event_datetime.astimezone(utc_tz)

        # Parsing to ISO 8601
        iso_format = event_datetime_utc.strftime("%Y-%m-%dT%H:%M:%S%z")
        iso_format = iso_format[:-2] + ":" + iso_format[-2:]
        return iso_format

async def main() -> None:
    items: List[Item] = []
    item = Item()
    await item.playwright_start()
    for _ in range(3):
        try:
            data = await item._login_access()
            items.extend(data)
        except TimeoutError:
            continue
        break
    await item.playwright_finish()
    
    # Convert items to a list of dictionaries
    data_dicts = [asdict(item) for item in items]
    print(json.dumps(data_dicts, indent=4))

if __name__ == "__main__":
    asyncio.run(main())