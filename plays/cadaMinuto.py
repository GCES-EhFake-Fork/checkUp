import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from plays.base import BasePlay
from plays.items import EntryItem
from plog import logger


class CadaMinutoPlay(BasePlay):
    name = "cadaminuto"

    @classmethod
    def match(cls, url):
        return "cadaminuto.com.br" in url

    def pre_run(self):
        pass

    def run(self) -> EntryItem:
        with sync_playwright() as p:
            browser = self.launch_browser(p, viewport={"width": 1920, "height": 1080})
            page = browser.new_page()
            
            logger.info(f"[{self.name}] Opening URL '{self.url}'...")
            page.goto(self.url, timeout=180_000)
            
            # Aguardar carregamento do conteúdo principal
            try:
                page.wait_for_selector("h2", timeout=30000)
            except Exception as e:
                logger.warning(f"[{self.name}] Timeout aguardando h2: {e}")
            
            # Extrair título da notícia
            title = ""
            title_selectors = [
                "h2.text-\\[1\\.5rem\\]",  # Seletor específico baseado no HTML
                "h1", "h2",  # Fallback genérico
            ]
            
            for selector in title_selectors:
                title_element = page.query_selector(selector)
                if title_element:
                    title = title_element.inner_text().strip()
                    if title:
                        logger.info(f"[{self.name}] Título encontrado com '{selector}': {title[:50]}...")
                        break
            
            # Extrair data e categoria
            description = ""
            meta_info = ""
            date_category_selector = "div.text-\\[0\\.875rem\\].leading-\\[1\\.026rem\\].text-gray-400"
            date_elements = page.query_selector_all(date_category_selector)
            
            if date_elements and len(date_elements) >= 1:
                # Primeiro elemento geralmente tem data e categoria
                meta_info = date_elements[0].inner_text().strip()
                logger.info(f"[{self.name}] Meta info: {meta_info}")
                
                # Se houver informações de autor
                if len(date_elements) >= 2:
                    author_info = date_elements[1].inner_text().strip()
                    if "Por" in author_info:
                        description = f"Autor: {author_info.replace('Por ', '')}"
            
            # Extrair corpo da notícia
            body = ""
            body_selectors = [
                ".text-\\[1\\.1rem\\].post-content",  # Seletor específico identificado
                ".post-content",
                "div[class*='post-content']",
                "article div",  # Fallback
            ]
            
            for selector in body_selectors:
                body_element = page.query_selector(selector)
                if body_element:
                    # Remover elementos publicitários e scripts
                    ads_to_remove = [
                        'div[id*="google_ads"]',
                        'div[id*="taboola"]',
                        'iframe[id*="google_ads"]',
                        'script',
                        'style',
                        'div[id*="supertag"]',
                        'div.grecaptcha-badge'
                    ]
                    
                    for ad_selector in ads_to_remove:
                        ads = body_element.query_selector_all(ad_selector)
                        for ad in ads:
                            ad.evaluate("element => element.remove()")
                    
                    body = body_element.inner_text().strip()
                    if body and len(body) > 100:  # Garantir que há conteúdo substancial
                        logger.info(f"[{self.name}] Corpo encontrado com '{selector}': {len(body)} caracteres")
                        break
            
            # Extrair tags/categorias
            tags = []
            
            # Tentar extrair categoria da meta info
            if meta_info and " - " in meta_info:
                parts = meta_info.split(" - ")
                if len(parts) >= 2:
                    category = parts[1].strip()
                    if category:
                        tags.append(category)
            
            # Adicionar tag baseada na URL (seção do site)
            parsed_url = urlparse(self.url)
            url_parts = parsed_url.path.strip('/').split('/')
            if len(url_parts) >= 2 and url_parts[0] == "noticia":
                # URL formato: /noticia/2025/10/03/titulo-da-noticia
                # Adicionar ano como tag
                try:
                    year = url_parts[1]
                    if year.isdigit() and len(year) == 4:
                        tags.append(f"Ano {year}")
                except:
                    pass
            
            # Limpar conteúdo
            if body:
                # Remover linhas em branco excessivas
                body = '\n'.join([line.strip() for line in body.split('\n') if line.strip()])
                
            # Log dos resultados
            logger.info(f"[{self.name}] Extração concluída:")
            logger.info(f"[{self.name}] - Título: {len(title)} chars")
            logger.info(f"[{self.name}] - Descrição: {len(description)} chars") 
            logger.info(f"[{self.name}] - Corpo: {len(body)} chars")
            logger.info(f"[{self.name}] - Tags: {tags}")
            
            # Validar se extraiu conteúdo mínimo
            if not title or len(body) < 100:
                logger.error(f"[{self.name}] Conteúdo insuficiente extraído")
                logger.error(f"[{self.name}] Título: '{title}'")
                logger.error(f"[{self.name}] Corpo: {len(body)} chars")
                raise Exception(f"Falha ao extrair conteúdo mínimo da notícia")
            
            # Criar EntryItem
            entry_item = EntryItem(
                url=self.url,
                title=title,
                description=description,
                body=body,
                tags=tags
            )
            
            return entry_item
