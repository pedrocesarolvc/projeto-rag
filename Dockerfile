# Etapa 7 — imagem única: build do frontend + app Python, para que
# "docker compose up" seja o único comando que alguém avaliando o
# projeto precisa rodar (seção 7.6).

FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
WORKDIR /app

# psycopg[binary] e pymupdf já trazem wheels pré-compiladas; nenhuma
# dependência de sistema extra é necessária para instalar via pip.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY --from=frontend /frontend/dist/ frontend/dist/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
