# 🐍 python-fastapi

Imagem base otimizada para aplicações Python com FastAPI.

## Técnicas aplicadas

- **Multi-stage build** — separa instalação de dependências do runtime
- **python:3.12-slim** — imagem base ~45MB vs ~350MB da full
- **`--prefix=/install`** — instala deps em diretório isolado, copia só o necessário
- **Non-root user** — container roda como `appuser`
- **HEALTHCHECK** — verificação de saúde nativa do Docker
- **Layer caching** — `requirements.txt` copiado antes do código
- **PYTHONDONTWRITEBYTECODE** — evita `.pyc` desnecessários
- **PYTHONUNBUFFERED** — logs em tempo real

## Uso

```dockerfile
FROM vivikk/imagem-base-otimizada:latest

WORKDIR /app
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Build local

```bash
# Otimizado
docker build -t python-fastapi .

# Naive (para comparação)
docker build -f Dockerfile.naive -t python-fastapi-naive .
```
