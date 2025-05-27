import time
from playwright.sync_api import sync_playwright, TimeoutError

from plays.base import BasePlay
from plays.items import AdItem, EntryItem
from plays.utils import get_or_none
from plog import logger


class IGPlay(BasePlay):
    name = "ig"
    n_expected_ads = 10

    @classmethod
    def match(cls, url: str) -> bool:
        return "ig.com.br" in url

    def find_items(self, html_content: str) -> AdItem:
        return AdItem(
            title=get_or_none(r'title="(.*?)"', html_content),
            url=get_or_none(r'href="(.*?)"', html_content),
            thumbnail_url=get_or_none(r'url\(&quot;(.*?)&quot;\)', html_content),
            tag=get_or_none(r'<span class="branding-inner.*?>(.*?)</span>', html_content),
            excerpt=get_or_none(r'slot="description" title="(.*?)"', html_content),
        )

    def run(self) -> EntryItem:
        with sync_playwright() as p:
            browser = self.launch_browser(p, viewport={"width": 1920, "height": 1080})
            page = browser.new_page()

            logger.info(f"[{self.name}] Opening URL '{self.url}'...")
            try:
                page.goto(self.url, timeout=180_000)
            except TimeoutError:
                logger.error(f"[{self.name}] Timeout loading page {self.url}")
                return EntryItem(title="Timeout", ads=[], url=self.url, screenshot_path="")

            logger.info(f"[{self.name}] Scrolling to load dynamic content...")
            self.scroll_down(page, 10, amount=500, wait_time=1)

            entry_screenshot_path = self.take_screenshot(page, self.url, goto=False)
            entry_title = page.title()

            logger.info(f"[{self.name}] Searching for ad elements...")
            elements = page.locator(".videoCube")
            ad_items = []

            for i in range(elements.count()):
                element = elements.nth(i)
                if not element.is_visible():
                    continue
                html_content = element.inner_html()
                ad_item = self.find_items(html_content)
                ad_items.append(ad_item)

            logger.info(f"[{self.name}] Found {len(ad_items)} ads.")

            return EntryItem(
                title=entry_title,
                ads=ad_items,
                url=self.url,
                screenshot_path=entry_screenshot_path,
            )
