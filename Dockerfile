# ======================
# Builder
# ======================
FROM python:3.11-slim as builder

# Instala dependências de build necessárias para compilar pacotes Python nativos
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instala o gerenciador de dependências Pipenv
RUN pip install pipenv

# Define que o ambiente virtual ficará no diretório do projeto
ENV PIPENV_VENV_IN_PROJECT=1

WORKDIR /usr/src

# Copia os arquivos de dependências
COPY Pipfile Pipfile.lock ./

# Instala as dependências do projeto no ambiente virtual
RUN pipenv install --deploy --dev

# Copia todo o código-fonte para a imagem
COPY . .

# ======================
# Runtime
# ======================
FROM python:3.11-slim as runtime

# Instala bibliotecas de sistema necessárias para execução do Python e do navegador Firefox usado pelo Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    wget \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src

# Copia o ambiente virtual criado na fase de build
COPY --from=builder /usr/src/.venv/ /usr/src/.venv/

# Adiciona o ambiente virtual ao PATH
ENV PATH=/usr/src/.venv/bin:$PATH

# Instala os navegadores necessários para o Playwright funcionar
RUN playwright install --with-deps firefox

# Configurações para otimizar o comportamento do Python no container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalação explícita do cliente MinIO
RUN pip install minio==7.2.15

CMD ["ipython"]