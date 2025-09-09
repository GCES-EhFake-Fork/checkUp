# Exemplo Prático: Atualizando R7 Spider e Play

## 📄 Situação Atual vs Nova Implementação

### 🕷️ SPIDER R7 - Antes e Depois

#### ❌ ANTES (spiders/r7.py):
```python
import re
import scrapy
from spiders.base import BaseSpider
from spiders.items import URLItem

class R7Spider(BaseSpider):
    name = "r7spider"
    start_urls = ["https://www.r7.com/"]
    allowed_domains = ["r7.com"]

    def allow_url(self, entry_url):
        return (
            entry_url.startswith("https://")
            and len(entry_url) > 100
            and re.match(
                r"https://(entretenimento|esportes|record|noticias)\.r7\.com", entry_url
            )
        )

    def parse(self, response):
        seen = set()
        for entry in response.css("a"):
            url = entry.attrib.get("href")
            if url and url not in seen and self.allow_url(url):
                seen.add(url)
                yield URLItem(url=url)
                yield scrapy.Request(url=url, callback=self.parse)  # ← PROBLEMA: Crawling recursivo
```

#### ✅ DEPOIS (spiders/r7.py atualizado):
```python
import re
import scrapy
from spiders.base import BaseSpider
from spiders.items import URLItem
from urllib.parse import urlparse

class R7Spider(BaseSpider):
    name = "r7spider"
    start_urls = ["https://www.r7.com/"]
    allowed_domains = ["r7.com"]

    custom_settings = {
        **BaseSpider.custom_settings,
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 3,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
    }

    def allow_url(self, url: str) -> bool:
        """
        Filtragem melhorada para URLs de notícias do R7
        """
        if not url.startswith("https://"):
            return False
            
        # Verificar se é de um subdomínio válido do R7
        if not re.match(r"https://(noticias|entretenimento|esportes|record)\.r7\.com", url):
            return False
        
        p = urlparse(url)
        path = p.path.rstrip('/')
        
        # Blacklist de seções que não são notícias
        blacklisted_sections = {
            "/videos", "/ao-vivo", "/podcasts", "/newsletters", 
            "/especiais", "/opiniao", "/blogs", "/colunas"
        }
        
        if any(path.startswith(section) for section in blacklisted_sections):
            self.logger.info(f"Blacklisted URL: {url}")
            return False
        
        # Require pelo menos dois segmentos (seção + slug da notícia)
        segments = [seg for seg in path.split('/') if seg]
        if len(segments) < 2:
            return False
            
        slug = segments[-1]
        
        # URLs de notícias do R7 geralmente têm:
        # - Pelo menos 3 hífens no slug OU
        # - Slug com mais de 30 caracteres OU  
        # - Termina com números (padrão do R7)
        if (slug.count('-') >= 3 or 
            len(slug) > 30 or 
            re.search(r'-\d+$', slug)):
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
        
        # Focar em links de notícias principais
        news_links = response.css("a[href*='noticias.r7.com'], a[href*='entretenimento.r7.com'], a[href*='esportes.r7.com'], a[href*='record.r7.com']")
        
        for link in news_links:
            url = link.attrib.get("href")
            if not url or url in seen:
                continue
                
            # Construir URL absoluta e limpar
            full_url = response.urljoin(url)
            full_url = full_url.split('#', 1)[0].split('?', 1)[0]
            
            if self.allow_url(full_url):
                seen.add(full_url)
                yield URLItem(url=full_url)
                
        self.logger.info(f"Collected {len(seen)} unique news URLs from R7")
```

### 🎭 PLAY R7 - Antes e Depois

#### ❌ ANTES (plays/r7.py):
```python
import time
from playwright.sync_api import sync_playwright
from plays.base import BasePlay
from plays.items import AdItem, EntryItem
from plays.utils import get_or_none
from plog import logger

class R7Play(BasePlay):
    name = "r7"
    n_expected_ads = 20  # ← Focado em anúncios

    @classmethod
    def match(cls, url):
        return "r7.com" in url

    def find_items(self, html_content) -> AdItem:  # ← Código para anúncios
        def clean(text):
            return text.strip() if text else None

        return AdItem(
            title=clean(get_or_none(r'title="(.*?)"', html_content)),
            url=clean(get_or_none(r'href="(.*?)"', html_content)),
            thumbnail_url=clean(get_or_none(r'url\(&quot;(.*?)&quot;\)', html_content)),
            tag=clean(get_or_none(r'<span class="branding-inner".*?>(.*?)<\/span>', html_content)),
            excerpt=clean(get_or_none(r'slot="description" title="(.*?)"', html_content)),
        )

    def run(self) -> EntryItem:
        with sync_playwright() as p:
            browser = self.launch_browser(p)
            page = browser.new_page()
            logger.info(f"[{self.name}] Opening URL '{self.url}'...")
            page.goto(self.url, timeout=180_000)
            logger.info(f"[{self.name}] Searching for ads...")

            entry_screenshot_path = self.take_screenshot(page, self.url, goto=False)  # ← Screenshot desnecessário
            entry_title = page.locator("head title").inner_text()

            # Código complexo para encontrar anúncios
            self.scroll_down(page, 10, 400, wait_time=1)
            
            try:
                page.locator("#taboola-below-article-thumbnails").click()
                page.locator("#taboola-below-article-thumbnails").scroll_into_view_if_needed()
            except Exception:
                logger.warning(f"[{self.name}] Timeout or missing 'taboola-below-article-thumbnails'")

            time.sleep(self.wait_time)
            self.scroll_down(page, 30, 400, wait_time=1)

            elements = page.locator(".videoCube")
            ad_items = []
            # ... mais código para anúncios

            return EntryItem(
                title=entry_title,
                ads=ad_items,  # ← Focado em anúncios
                url=self.url,
                screenshot_path=entry_screenshot_path,  # ← Screenshot
            )
```

#### ✅ DEPOIS (plays/r7.py atualizado):
```python
import time
from playwright.sync_api import sync_playwright
from plays.base import BasePlay
from plays.items import EntryItem
from plog import logger

class R7Play(BasePlay):
    name = "r7"

    @classmethod
    def match(cls, url):
        return "r7.com" in url

    def pre_run(self):
        pass

    def run(self) -> EntryItem:
        with sync_playwright() as p:
            browser = self.launch_browser(p, viewport={"width": 1920, "height": 1080})
            page = browser.new_page()
            logger.info(f"[{self.name}] Opening URL '{self.url}'...")
            page.goto(self.url, timeout=180_000)
            
            # Aguardar carregamento do conteúdo
            page.wait_for_selector("h1", timeout=30000)
            
            # 1. EXTRAIR TÍTULO
            entry_title = ""
            try:
                # R7 usa diferentes estruturas para título
                title_selectors = [
                    "h1.title",
                    "h1",
                    ".article-title h1",
                    ".content-head h1"
                ]
                
                for selector in title_selectors:
                    try:
                        title_element = page.locator(selector)
                        if title_element.count() > 0:
                            entry_title = title_element.first.inner_text()
                            if entry_title.strip():
                                logger.info(f"[{self.name}] Extracted title using: {selector}")
                                break
                    except Exception:
                        continue
                        
                if not entry_title.strip():
                    # Fallback para tag title
                    entry_title = page.locator("head title").inner_text()
                    
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract title: {str(e)}")
            
            # 2. EXTRAIR DESCRIÇÃO/SUBTÍTULO
            description = ""
            try:
                desc_selectors = [
                    ".article-subtitle",
                    ".content-head .subtitle", 
                    ".lead",
                    ".article-summary",
                    "h2.subtitle"
                ]
                
                for selector in desc_selectors:
                    try:
                        desc_element = page.locator(selector)
                        if desc_element.count() > 0:
                            description = desc_element.first.inner_text()
                            if description.strip():
                                logger.info(f"[{self.name}] Extracted description using: {selector}")
                                break
                    except Exception:
                        continue
                        
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract description: {str(e)}")
            
            # 3. EXTRAIR CORPO DA NOTÍCIA
            body = ""
            try:
                # R7 tem diferentes estruturas de conteúdo
                content_selectors = [
                    ".article-content",
                    ".content-text",
                    ".post-content",
                    ".article-body",
                    "#article-content",
                    ".texto"
                ]
                
                for selector in content_selectors:
                    try:
                        content_element = page.locator(selector)
                        if content_element.count() > 0:
                            body = content_element.first.inner_text()
                            if body.strip() and len(body) > 100:  # Garantir que tem conteúdo substancial
                                logger.info(f"[{self.name}] Extracted body using: {selector}")
                                break
                    except Exception:
                        continue
                        
                if not body.strip():
                    logger.warning(f"[{self.name}] Failed to extract article body")
                    
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract article body: {str(e)}")
            
            # 4. EXTRAIR TAGS
            tags = []
            try:
                tag_selectors = [
                    ".tags a",
                    ".article-tags a",
                    ".post-tags a", 
                    ".categories a",
                    "[rel='tag']"
                ]
                
                for selector in tag_selectors:
                    try:
                        tag_elements = page.locator(selector)
                        if tag_elements.count() > 0:
                            for i in range(tag_elements.count()):
                                tag_text = tag_elements.nth(i).inner_text().strip()
                                if tag_text and tag_text not in tags:
                                    tags.append(tag_text)
                            if tags:
                                logger.info(f"[{self.name}] Extracted {len(tags)} tags using: {selector}")
                                break
                    except Exception:
                        continue
                        
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract tags: {str(e)}")

            # Log de resultados
            logger.info(f"[{self.name}] Extraction summary:")
            logger.info(f"  - Title: {'✓' if entry_title else '✗'}")
            logger.info(f"  - Description: {'✓' if description else '✗'}")
            logger.info(f"  - Body: {'✓' if body else '✗'} ({len(body)} chars)")
            logger.info(f"  - Tags: {'✓' if tags else '✗'} ({len(tags)} tags)")

            return EntryItem(
                title=entry_title,
                url=self.url,
                description=description,
                body=body,
                tags=tags,
            )
```

## 🔍 Principais Mudanças Implementadas

### Spider R7:
1. ✅ **Removido crawling recursivo** - Não há mais `yield scrapy.Request` 
2. ✅ **Melhorada filtragem de URLs** - Lógica mais robusta baseada no padrão do gazetaDoPovo
3. ✅ **Adicionados custom_settings** - Headers mais realistas
4. ✅ **Foco na página inicial** - Coleta apenas URLs da home
5. ✅ **Logs informativos** - Para debug e monitoramento

### Play R7:
1. ✅ **Removido take_screenshot** - Não precisamos mais de imagens
2. ✅ **Removido código de anúncios** - `find_items`, `n_expected_ads`, etc.
3. ✅ **Implementada extração de conteúdo** - Título, descrição, corpo e tags
4. ✅ **Multiple fallbacks** - Vários seletores para maior robustez
5. ✅ **Logs detalhados** - Para acompanhar o que foi extraído
6. ✅ **Validação de conteúdo** - Verifica se body tem conteúdo substancial

## 🚀 Como Aplicar em Outros Portais

### Para atualizar outros spiders:
1. Copie a estrutura de `allow_url()` do R7 atualizado
2. Adapte os regexes para o domínio específico
3. Ajuste as seções blacklisted para o portal
4. Remova todos os `yield scrapy.Request` recursivos
5. Foque nos seletores CSS específicos da página inicial

### Para atualizar outros plays:
1. Remova todo código relacionado a anúncios
2. Implemente os 4 tipos de extração: título, descrição, corpo, tags
3. Use múltiplos seletores como fallback
4. Adicione logs detalhados para debug
5. Valide se o conteúdo extraído faz sentido

## 📝 Teste da Implementação

Para testar o R7 atualizado:

```bash
# Testar o spider
scrapy crawl r7spider -s LOG_LEVEL=INFO

# Testar o play com uma URL específica
python -c "
from plays.r7 import R7Play
play = R7Play('https://noticias.r7.com/exemplo-noticia')
result = play.execute()
print(f'Title: {result.title}')
print(f'Description: {result.description}')
print(f'Body: {len(result.body)} chars')
print(f'Tags: {result.tags}')
"
```

## ✅ Checklist de Validação

### Spider R7:
- [x] Remove `yield scrapy.Request` recursivo  
- [x] Implementa `allow_url()` com boa filtragem
- [x] Coleta apenas URLs da página inicial
- [x] URLs coletados são realmente de notícias
- [x] Logs informativos habilitados

### Play R7:
- [x] Remove `take_screenshot()` e variáveis relacionadas
- [x] Remove código de anúncios (`find_items`, `n_expected_ads`, etc.)
- [x] Extrai título da notícia
- [x] Extrai descrição (quando disponível)
- [x] Extrai corpo completo da notícia  
- [x] Extrai tags (quando disponível)
- [x] Retorna `EntryItem` com os dados corretos
- [x] Múltiplos seletores como fallback
- [x] Logs detalhados para debug
</rewritten_file> 