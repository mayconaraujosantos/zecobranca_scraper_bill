# Etapa base: Python + dependências
FROM python:3.13-slim

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Chrome, utilitários e dependências
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxrender1 \
    libxext6 \
    libxi6 \
    libxcursor1 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libdbus-1-3 \
    xdg-utils \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Instalar Google Chrome (stable)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Instalar pipenv
RUN pip install pipenv

# Definir diretório de trabalho
WORKDIR /app

# Copiar Pipfile e Pipfile.lock primeiro (para cache de dependências)
COPY Pipfile Pipfile.lock ./

# Instalar dependências do projeto no sistema (sem venv interna)
RUN pipenv install --deploy --system

# Copiar código do projeto
COPY . .

# Variável para rodar o Chrome em headless dentro do container
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER=/usr/local/bin/chromedriver

# Rodar aplicação
CMD ["pipenv", "run", "python", "main.py"]
