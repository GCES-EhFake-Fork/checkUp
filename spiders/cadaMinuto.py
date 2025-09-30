import scrapy
from urllib.parse import urlparse
from spiders.base import BaseSpider
from spiders.items import URLItem

class CadaMinutoSpider(BaseSpider):
    name = "cadaminutospider"
    start_urls = ["https://www.cadaminuto.com.br/"]
    allowed_domains = ["cadaminuto.com.br"]

    custom_settings = {
        **BaseSpider.custom_settings,
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 2,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
    }

    def allow_url(self, url: str) -> bool:
        """
        Filtra apenas URLs de notícias válidas do Cada Minuto
        Baseado na análise do HTML: URLs seguem padrão /noticia/YYYY/MM/DD/titulo-da-noticia
        """
        p = urlparse(url)
        path = p.path.rstrip('/')
        
        # Aceitar apenas URLs que começam com /noticia/
        if not path.startswith('/noticia/'):
            return False
        
        # Verificar estrutura: /noticia/YYYY/MM/DD/titulo
        segments = [seg for seg in path.split('/') if seg]
        
        # Deve ter pelo menos 5 segmentos: ['noticia', 'YYYY', 'MM', 'DD', 'titulo']
        if len(segments) < 5:
            return False
            
        # Verificar se tem ano, mês, dia válidos
        try:
            year = int(segments[1])
            month = int(segments[2]) 
            day = int(segments[3])
            
            # Validações básicas
            if not (2020 <= year <= 2030):
                return False
            if not (1 <= month <= 12):
                return False
            if not (1 <= day <= 31):
                return False
                
        except (ValueError, IndexError):
            return False
        
        # Verificar se o slug tem formato válido (título com hífens)
        slug = segments[4] if len(segments) > 4 else ""
        if len(slug) < 10 or slug.count('-') < 2:
            return False
            
        return True

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
        Extrai URLs de notícias da página inicial do Cada Minuto
        Baseado na análise do HTML fornecido
        """
        # Seletores específicos baseados na estrutura HTML analisada
        selectors = [
            'a[href^="/noticia/"]',  # Links que começam com /noticia/
            'main a[href*="/noticia/"]',  # Links de notícia dentro da main
            'article a[href]',  # Links dentro de artigos
            'h1 a[href], h2 a[href], h3 a[href]',  # Links em títulos
        ]
        
        seen_urls = set()
        
        self.logger.info(f"Parseando página inicial: {response.url}")
        
        for selector in selectors:
            links = response.css(selector)
            self.logger.info(f"Seletor '{selector}' encontrou {len(links)} links")
            
            for link in links:
                url = link.attrib.get("href")
                if not url:
                    continue
                
                # Construir URL absoluta
                full_url = response.urljoin(url)
                full_url = full_url.split('#', 1)[0].split('?', 1)[0]
                
                # Evitar duplicatas
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                # Filtrar URLs válidos
                if self.allow_url(full_url):
                    self.logger.info(f"URL válida encontrada: {full_url}")
                    yield URLItem(url=full_url)
        
        self.logger.info(f"Total de URLs de notícias coletadas: {len(seen_urls)}")

