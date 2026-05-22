# ══════════════════════════════════════════════════════════════
# Dockerfile — Janio Pontes SaaS (FastAPI + Jinja2 + Tailwind)
# Imagem otimizada para deploy no Google Cloud Run
# ══════════════════════════════════════════════════════════════

# --- Estágio 1: Build do CSS (Tailwind) ---
FROM node:20-alpine AS css-builder
WORKDIR /build
COPY package.json package-lock.json tailwind.config.js ./
RUN npm ci
COPY app/templates/ ./app/templates/
COPY app/static/ ./app/static/
RUN npx tailwindcss -i ./app/static/src/input.css -o ./app/static/css/output.css --minify 2>/dev/null || echo "Tailwind build skipped (input.css not found, using CDN)"

# --- Estágio 2: Aplicação Python ---
FROM python:3.12-slim

# Variáveis de ambiente para o Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Copiar CSS compilado do estágio anterior (se existir)
COPY --from=css-builder /build/app/static/css/ ./app/static/css/ 2>/dev/null || true

# Expor a porta que o Cloud Run usa
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1

# Comando de inicialização (Uvicorn com workers otimizados)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
