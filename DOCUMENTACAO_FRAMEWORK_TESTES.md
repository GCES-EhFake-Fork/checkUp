# Documentação do Framework de Testes Automatizados - Check-up

## 1. Visão Geral

O projeto Check-up implementa um framework de testes automatizados baseado no **pytest 8.2.0** para garantir a qualidade e confiabilidade do sistema de extração de notícias. O framework fornece testes unitários para componentes críticos e integração completa com pipeline de CI/CD.

## 2. Estrutura dos Testes

### 2.1 Organização de Diretórios

```
tests/
├── __init__.py               # Inicialização do módulo de testes
├── plays/                    # Testes para módulos de extração de conteúdo
│   ├── __init__.py          
│   ├── test_base.py         # Testes do BasePlay (núcleo do sistema)
│   └── test_uol.py          # Testes específicos do UOLPlay
```

### 2.2 Configuração

- **Arquivo de configuração**: `pytest.ini`
- **Padrão de arquivos**: `test_*.py`
- **Framework**: pytest 8.2.0
- **Ambiente**: Docker containers com PostgreSQL e MinIO

## 3. Dependências de Teste

### 3.1 Bibliotecas Utilizadas

- **pytest**: 8.2.0 - Framework principal
- **freezegun**: 1.5.1 - Manipulação de tempo para testes determinísticos
- **flake8**: Linting e verificação de qualidade de código

### 3.2 Infraestrutura

- **Docker**: Containerização para isolamento de testes
- **PostgreSQL**: Banco de dados para testes
- **MinIO**: Storage para arquivos de teste

## 4. Testes Implementados

### 4.1 BasePlay (`test_base.py`)

O arquivo contém 14 métodos de teste que cobrem as funcionalidades centrais do sistema.

#### **Testes de Seleção de Scrapers**

Validam se o sistema escolhe o scraper correto baseado na URL fornecida:

```python
def test_return_correct_scraper_folha(self):
    """Verifica se o sistema retorna o scraper correto para URLs da Folha"""
    url = "https://www1.folha.uol.com.br/mundo/2024/05/entry-slug"
    scraper = BasePlay.get_scraper(url)
    assert isinstance(scraper, FolhaPlay)
    assert scraper.url == url
```

**Portais cobertos pelos testes**:
- Folha de S.Paulo
- Estadão  
- Veja
- UOL
- Globo
- Terra
- Metrópoles
- ClicRBS (Gaúcha Zero Hora)
- IG
- R7

#### **Testes de Gerenciamento de Sessão**

```python
@freeze_time("2024-05-15 12:00:00")
def test_get_session(self):
    """Testa o gerenciamento de diretório de sessão personalizado"""
    url = "https://entry-url.com"
    scraper = BasePlay(url, session_dir="/tmp/session")
    assert scraper.get_session_dir() == "/tmp/session"

@freeze_time("2024-05-15 12:00:00")  
def test_get_session_when_not_given(self):
    """Testa o diretório padrão quando não especificado"""
    url = "https://entry-url.com"
    scraper = BasePlay(url)
    assert scraper.get_session_dir() == "./sessions/base_session/"
```

#### **Testes de Tratamento de Erros**

```python
def test_raise_error_if_no_scraper_is_found(self):
    """Verifica se exceção é lançada para URLs não suportadas"""
    url = "https://any.com.br"
    with pytest.raises(ScraperNotFoundError):
        BasePlay.get_scraper(url)
```

### 4.2 UOL (`test_uol.py`)

Testes específicos para o portal UOL:

```python
class TestUOLPlay:
    def test_match(self):
        """Testa o matching de URLs específicas do UOL"""
        assert UOLPlay.match("https://noticias.uol.com.br/colunas/") is True
        assert UOLPlay.match("https://www.uol.com.br/colunas/") is True
```

## 5. Estratégias de Teste

### 5.1 Time Mocking

Utiliza `freezegun` para garantir testes determinísticos:

```python
@freeze_time("2024-05-15 12:00:00")
def test_get_session(self):
    # Teste com tempo fixo para evitar variações
```

### 5.2 Exception Testing

Usa `pytest.raises()` para validar exceções:

```python
with pytest.raises(ScraperNotFoundError):
    BasePlay.get_scraper(url)
```

### 5.3 Pattern Matching

Testa padrões de URL para cada portal:

```python
assert PortalPlay.match("https://portal.com/noticia/") is True
```

## 6. Pipeline de CI/CD

### 6.1 Automação GitHub Actions

O arquivo `.github/workflows/ci.yml` executa os testes automaticamente:

```yaml
- name: Run tests
  run: pytest -xvs tests/
```

**Flags utilizadas**:
- `-x`: Para na primeira falha
- `-v`: Saída verbosa  
- `-s`: Não captura stdout

### 6.2 Etapas do Pipeline

1. **Lint**: Verificação de código com flake8
2. **Backend**: Testes de healthcheck da API
3. **Frontend**: Build e lint do client React  
4. **Docker Test**: Testes em ambiente containerizado
5. **Database Test**: Inicialização e validação de banco

### 6.3 Setup de Banco

```python
# create_db_ci.py - Script para CI
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/test_healthcheck"
engine = create_engine(DATABASE_URL)

# Criação das tabelas para teste
Portal.metadata.create_all(engine)
Entry.metadata.create_all(engine)
Advertisement.metadata.create_all(engine)
URLQueue.metadata.create_all(engine)
QueueStatus.metadata.create_all(engine)
```

## 7. Cobertura Atual

### 7.1 Funcionalidades Testadas

- **Seleção de Scrapers**: 10 portais cobertos (100% dos implementados)
- **Gerenciamento de Sessão**: Cenários padrão e customizados
- **Tratamento de Erros**: Exceção `ScraperNotFoundError`
- **URL Matching**: Padrões de URL validados para cada portal

### 7.2 Estatísticas

- **Total de arquivos de teste**: 8
- **Métodos de teste no BasePlay**: 14
- **Portais com testes de matching**: 10
- **Portais com testes específicos**: 1 (UOL)

## 8. Execução dos Testes

### 8.1 Comandos Disponíveis

```bash
# Executar todos os testes
pytest tests/

# Executar com verbosidade
pytest -v tests/

# Executar teste específico
pytest tests/plays/test_base.py::TestBasePlay::test_return_correct_scraper_folha

# No container Docker
make bash
pytest tests/
```

### 8.2 Ambientes de Execução

- **Local**: Diretamente com pytest
- **Docker**: Dentro do container `scraper`
- **CI/CD**: Automaticamente no GitHub Actions

## 9. Padrões e Convenções

### 9.1 Nomenclatura

- **Arquivos**: `test_*.py`
- **Classes**: `TestNomeDoModulo`  
- **Métodos**: `test_descricao_do_cenario`

### 9.2 Estrutura Padrão

```python
class TestBasePlay:
    def test_return_correct_scraper_portal(self):
        # Arrange - Preparar dados
        url = "https://portal.com/noticia"
        
        # Act - Executar ação
        scraper = BasePlay.get_scraper(url)
        
        # Assert - Verificar resultado
        assert isinstance(scraper, PortalPlay)
        assert scraper.url == url
```

### 9.3 Uso de Fixtures

- **Time mocking**: `@freeze_time()` para testes determinísticos
- **Exception testing**: `pytest.raises()` para validação de erros

## 10. Integração com Makefile

### 10.1 Comandos Relacionados

Os testes não possuem comando específico no Makefile. A execução acontece via:

- **CI/CD**: GitHub Actions (automático)
- **Container**: `make bash` + `pytest tests/`
- **Setup**: `make setup` (inclui ambiente de teste)

### 10.2 Ambiente de Desenvolvimento

```bash
# Configurar ambiente completo
make setup

# Acessar container para testes manuais
make bash
pytest tests/
```

## 11. Debugging e Troubleshooting

### 11.1 Logs

- **GitHub Actions**: Logs completos no pipeline
- **Local**: Output verboso com flag `-v`
- **Debug**: Flag `-s` para ver prints durante execução

### 11.2 Problemas Comuns

- **Timeout de banco**: Aguardar inicialização do PostgreSQL
- **Dependências**: Verificar instalação via pipenv
- **Containers**: Cleanup automático após execução

## 12. Adição de Novos Portais

### 12.1 Processo Padrão

Para cada novo portal, criar:

1. **Teste de matching** em `test_base.py`
2. **Arquivo específico** `test_novoPortal.py`
3. **Validação de URLs** suportadas

### 12.2 Exemplo de Implementação

```python
# Em test_base.py
def test_return_correct_scraper_novo_portal(self):
    url = "https://novoportal.com.br/noticia/exemplo"
    scraper = BasePlay.get_scraper(url)
    assert isinstance(scraper, NovoPortalPlay)
    assert scraper.url == url

# Em test_novo_portal.py
class TestNovoPortalPlay:
    def test_match(self):
        assert NovoPortalPlay.match("https://novoportal.com.br/noticia/") is True
        assert NovoPortalPlay.match("https://novoportal.com.br/artigos/") is True
```

## 13. Configuração Técnica

### 13.1 Arquivo pytest.ini

```ini
[pytest]
python_files = test_*.py
```

### 13.2 Dependências (Pipfile)

- `pytest = "==8.2.0"`
- `freezegun = "==1.5.1"`
- Executado em ambiente Python 3.12

### 13.3 Triggers CI/CD

- Push para branches `main` ou `develop`
- Pull requests para branches principais
- Execução em Ubuntu latest com containers Docker

---

## 📚 Referências

- **Configuração**: `pytest.ini` - Configuração do framework
- **Pipeline**: `.github/workflows/ci.yml` - Automação CI/CD
- **Código**: `tests/` - Diretório com arquivos de teste
- **Dependências**: `Pipfile` - Bibliotecas de teste utilizadas