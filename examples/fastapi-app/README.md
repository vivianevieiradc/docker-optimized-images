# 🚀 fastapi-example-app

Aplicação de exemplo que consome a imagem base otimizada [`python-fastapi`](https://github.com/vivikk/docker-optimized-images).

## Como funciona

```
docker-optimized-images/python-fastapi    →    Docker Hub (vivikk/imagem-base-otimizada:latest)
                                                ↓
fastapi-example-app/Dockerfile        →    FROM vivikk/imagem-base-otimizada:latest
```

A imagem base já inclui FastAPI + Uvicorn + user non-root + health check.
Este projeto só adiciona o código da aplicação e dependências extras.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Health check |
| GET | `/items` | Lista itens de exemplo |
| GET | `/docs` | Swagger UI |

## Rodar local

```bash
docker compose up
# API disponível em http://localhost:8000/docs
```

## Build manual

```bash
docker build -t fastapi-example-app .
docker run -p 8000:8000 fastapi-example-app
```
