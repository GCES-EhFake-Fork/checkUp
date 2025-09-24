import re

import scrapy

from spiders.base import BaseSpider
from spiders.items import URLItem


class TerraSpider(BaseSpider):
    name = "terraspider"
    start_urls = ["https://www.terra.com.br/"]
    allowed_domains = ["terra.com.br", "www.terra.com.br"]

    custom_settings = {
        **BaseSpider.custom_settings,
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36",
        },
    }
    
    #  Seções que não são notícias
    BLACKLISTED_SECTIONS = {
        "videos", "podcast", "podcasts", "blogs", "colunas", "especiais", "ao-vivo", "story", "amp"
    }

    def allow_url(self, url: str) -> bool:
        """
        Filtragem melhorada para URLs de notícias do Terra.
        """
        if not url:
            return False
        url = url.split('#', 1)[0]

        # Normaliza e filtra padrões comuns de matéria do Terra, ex.:
        # https://www.terra.com.br/noticias/brasil/...
        if not re.match(r"https?://(www\.)?terra\.com\.br/", url):
            return False
        
        # Evita áreas que não são notícias
        path = re.sub(r"https?://[^/]+", "", url)
        first = (path.strip("/").split("/") or [""])[0]
        if first in self.BLACKLISTED_SECTIONS:
            return False
        
        # Require pelo menos dois segmentos (seção + slug da notícia)
        segments = [s for s in path.split('/') if s]
        if len(segments) < 2:
            return False
        
        slug = segments[-1]

        # Heurística de slug de notícia
        if slug.count('-') >= 3 or len(slug) > 30 or slug.endswith('.html'):
            return True
        return False

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True,
                meta={"dont_redirect": True, "handle_httpstatus_list": [403]},
            )

    def parse(self, response):
        """
        Extrai apenas URLs da página inicial, sem crawling recursivo
        """
        seen = set()
        selectors = [
            "a[href*='terra.com.br/noticias']",
            "a[href*='terra.com.br/economia']",
            "a[href*='terra.com.br/esportes']",
            "a[href*='terra.com.br/vida-e-estilo']",
            "a[href*='terra.com.br/']",
        ]

        for sel in selectors:
            for entry in response.css(sel):
                href = entry.attrib.get("href")

                if not href:
                    continue
                url = response.urljoin(href).split('?', 1)[0].split('#', 1)[0]
                
                if url in seen:
                    continue
                
                if self.allow_url(url):
                    seen.add(url)
                    yield URLItem(url=url)
                    
        self.logger.info(f"Collected {len(seen)} unique news URLs from Terra")
