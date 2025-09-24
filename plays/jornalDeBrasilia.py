import time
from playwright.sync_api import sync_playwright
from plays.base import BasePlay
from plays.items import EntryItem
from plog import logger

class CorreioPlay(BasePlay):
    name = "correio"

    @classmethod
    def match(cls, url):
        """Identifica se a URL é do Correio Braziliense"""
        return "correiobraziliense.com.br" in url

    def pre_run(self):
        """Configurações antes da execução"""
        pass

    def run(self) -> EntryItem:
        """Extrai conteúdo da notícia"""
        with sync_playwright() as p:
            browser = self.launch_browser(p, viewport={"width": 1920, "height": 1080})
            page = browser.new_page()
            
            logger.info(f"[{self.name}] Opening URL '{self.url}'...")
            page.goto(self.url, timeout=180_000)
            
            # Aguardar carregamento
            page.wait_for_selector("h1", timeout=30000)
            
            # 1. EXTRAIR TÍTULO
            title = self._extract_title(page)
            
            # 2. EXTRAIR DESCRIÇÃO
            description = self._extract_description(page)
            
            # 3. EXTRAIR CORPO
            body = self._extract_body(page)
            
            # 4. EXTRAIR TAGS
            tags = self._extract_tags(page)
            
            return EntryItem(
                title=title,
                url=self.url,
                description=description,
                body=body,
                tags=tags,
            )

    def _extract_title(self, page):
        """Extrai o título da notícia"""
        selectors = [
            "h1.title",
            "h1.headline", 
            "h1",
            ".article-title h1",
            ".post-title h1"
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    title = element.first.inner_text().strip()
                    if title:
                        logger.info(f"[{self.name}] Title extracted: {title[:50]}...")
                        return title
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract title with {selector}: {str(e)}")
                continue
        
        logger.error(f"[{self.name}] Failed to extract title")
        return ""

    def _extract_description(self, page):
        """Extrai a descrição/subtítulo da notícia"""
        selectors = [
            ".subtitle",
            ".lead",
            ".summary", 
            ".article-subtitle",
            "h2.subtitle",
            ".excerpt"
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    description = element.first.inner_text().strip()
                    if description and len(description) > 10:
                        logger.info(f"[{self.name}] Description extracted: {description[:50]}...")
                        return description
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract description with {selector}: {str(e)}")
                continue
        
        logger.info(f"[{self.name}] No description found")
        return ""

    def _extract_body(self, page):
        """Extrai o corpo da notícia"""
        selectors = [
            ".article-content",
            ".post-content",
            ".content",
            ".article-body",
            ".text",
            "article .content",
            ".entry-content"
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    # Remover elementos indesejados
                    element.locator("script, style, .ad, .advertisement").evaluate_all("el => el.remove()")
                    
                    body = element.inner_text().strip()
                    if body and len(body) > 100:  # Garantir que tem conteúdo substancial
                        logger.info(f"[{self.name}] Body extracted ({len(body)} chars)")
                        return body
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract body with {selector}: {str(e)}")
                continue
        
        logger.error(f"[{self.name}] Failed to extract body")
        return ""

    def _extract_tags(self, page):
        """Extrai as tags da notícia"""
        selectors = [
            ".tags a",
            ".categories a",
            ".post-tags a", 
            ".article-tags a",
            ".keywords a",
            "[rel='tag']"
        ]
        
        tags = []
        
        for selector in selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    for i in range(elements.count()):
                        tag_text = elements.nth(i).inner_text().strip()
                        if tag_text and tag_text not in tags:
                            tags.append(tag_text)
                    
                    if tags:
                        logger.info(f"[{self.name}] Tags extracted: {tags}")
                        break
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract tags with {selector}: {str(e)}")
                continue
        
        return tags