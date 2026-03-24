# 📚 Guia Passo a Passo — Docker Optimized Images

Tutorial completo de tudo que foi feito neste projeto, explicado para estudo.

---

## Parte 1 — Entendendo o problema

### Por que otimizar imagens Docker?

Quando você faz um `Dockerfile` simples assim:

```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "app.main:app"]
```

O resultado é uma imagem de **~1.17GB**. Isso causa:
- Deploy lento (imagem grande = mais tempo pra baixar)
- Mais espaço em disco no registry (Docker Hub, ECR)
- Superfície de ataque maior (mais pacotes = mais vulnerabilidades)
- Build lento na CI/CD

### O que é o Base Image Pattern (Golden Image)?

Em vez de cada projeto instalar tudo do zero, você cria uma **imagem base centralizada** com tudo que é comum:

```
┌─────────────────────────────┐
│  Imagem Base (golden image) │  ← build pesado, feito 1x
│  Python + FastAPI + Uvicorn │
│  Non-root user, healthcheck │
└──────────────┬──────────────┘
               │ FROM
    ┌──────────┴──────────┐
    │                     │
┌───▼───┐           ┌────▼────┐
│ App A │           │  App B  │  ← só COPY + CMD, build rápido
│ COPY. │           │  COPY.  │
└───────┘           └─────────┘
```

Benefícios:
- Build dos projetos consumidores fica em **segundos**
- **Padronização** — todos usam a mesma base
- **Segurança** — atualiza a base e todos herdam
- **Menos duplicação** de Dockerfile

---

## Parte 2 — Criando a estrutura do projeto

### 2.1 Criar as pastas

```bash
mkdir -p docker-optimized-images/{python-fastapi,node-api,.github/workflows,examples/fastapi-app/app}
cd docker-optimized-images
```

Estrutura:
```
docker-optimized-images/
├── python-fastapi/       # imagem base otimizada
├── node-api/             # placeholder para futuro
├── examples/
│   └── fastapi-app/      # app que consome a imagem base
└── .github/
    └── workflows/        # CI/CD
```

### 2.2 Criar o .gitignore

```bash
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/
*.egg-info/
dist/
build/
.DS_Store
EOF
```

### 2.3 Definir as dependências da imagem base

```bash
cat > python-fastapi/requirements.txt << 'EOF'
fastapi==0.115.0
uvicorn[standard]==0.30.6
EOF
```

> Essas são as dependências que **toda app FastAPI** vai precisar.
> Dependências específicas de cada app ficam no requirements.txt do projeto consumidor.

---

## Parte 3 — Dockerfile Naive (sem otimização)

Esse Dockerfile serve como **baseline para comparação**. É o jeito "normal" que a maioria faz:

```bash
cat > python-fastapi/Dockerfile.naive << 'EOF'
# ❌ Dockerfile SEM otimizações — apenas para comparação de tamanho
FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

### Problemas desse Dockerfile:

| Problema | Impacto |
|----------|---------|
| `python:3.12` (imagem full) | ~350MB só a base, com compiladores e ferramentas desnecessárias |
| Sem multi-stage | Lixo do pip (cache, headers) fica na imagem final |
| Roda como root | Se o container for comprometido, atacante tem acesso root |
| Sem healthcheck | Docker/orquestrador não sabe se a app tá saudável |
| Sem .dockerignore | `.git/`, `__pycache__/`, `*.md` entram no build context |

### Buildar e ver o tamanho:

```bash
cd python-fastapi/
docker build -f Dockerfile.naive -t python-fastapi-naive .
docker images python-fastapi-naive
# RESULTADO: ~1.17GB
```

---

## Parte 4 — Dockerfile Otimizado (com todas as boas práticas)

Agora o Dockerfile otimizado, explicando **cada linha**:

```bash
cat > python-fastapi/Dockerfile << 'DOCKERFILE'
# ============================================================
# Stage 1: Builder — instala dependências
# ============================================================
FROM python:3.12-slim AS builder
#
# python:3.12-slim = ~50MB (vs ~350MB da full)
# "AS builder" = dá um nome pra esse stage, usado no COPY --from depois

WORKDIR /build

COPY requirements.txt .
#
# Copia ANTES do código da app.
# Se o requirements.txt não mudar, o Docker usa cache dessa layer.
# Isso é "layer caching" — evita reinstalar deps toda vez que muda código.

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
#
# --no-cache-dir = não guarda cache do pip (economia de espaço)
# --prefix=/install = instala tudo em /install/ em vez do sistema
#   Isso permite copiar APENAS /install/ pro stage final
#   Sem precisar saber o path exato do site-packages

# ============================================================
# Stage 2: Runtime — imagem final mínima
# ============================================================
FROM python:3.12-slim
#
# Começa uma imagem NOVA e limpa.
# Nada do stage 1 vem junto automaticamente.
# Só o que a gente copiar com COPY --from=builder

LABEL org.opencontainers.image.title="python-fastapi-base" \
      org.opencontainers.image.description="Optimized Python/FastAPI base image" \
      org.opencontainers.image.source="https://github.com/vivianevieiradc/docker-optimized-images"
#
# Labels OCI = metadata padrão da imagem
# Aparece no Docker Hub e em ferramentas de inspeção

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
#
# Cria um usuário sem privilégios para rodar a app
# -r = system user (sem home dir desnecessário)
# -s /sbin/nologin = não pode fazer login (segurança)

WORKDIR /app

COPY --from=builder /install/lib /usr/local/lib
COPY --from=builder /install/bin /usr/local/bin
#
# Copia APENAS as dependências instaladas do stage builder
# /install/lib = pacotes Python (fastapi, uvicorn, etc)
# /install/bin = binários (uvicorn CLI)
# Todo o resto do builder (cache, pip, ferramentas) fica pra trás

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
#
# PYTHONDONTWRITEBYTECODE=1 = não gera arquivos .pyc (desnecessário em container)
# PYTHONUNBUFFERED=1 = print() e logs aparecem imediatamente no docker logs
#   Sem isso, Python faz buffer e você não vê os logs em tempo real

USER appuser
#
# A partir daqui, tudo roda como appuser (não root)
# Se alguém invadir o container, não tem acesso root

EXPOSE 8000
#
# Documenta qual porta a app usa
# Não abre a porta sozinho — é só metadata

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
#
# Docker verifica a cada 30s se a app tá respondendo
# Se falhar 3x seguidas, marca o container como "unhealthy"
# Orquestradores (ECS, Swarm) podem reiniciar automaticamente
# --start-period=10s = espera 10s antes de começar a checar (tempo da app subir)

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
#
# Comando padrão — pode ser sobrescrito pelo projeto consumidor
DOCKERFILE
```

### Buildar e comparar:

```bash
docker build -t python-fastapi-optimized .
docker images | grep python-fastapi
# python-fastapi-naive       1.17GB
# python-fastapi-optimized   158MB
# Redução de ~86%!
```

---

## Parte 5 — .dockerignore

```bash
cat > python-fastapi/.dockerignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/
.git/
.github/
*.md
Dockerfile*
.dockerignore
.gitignore
EOF
```

### Por que isso importa?

Quando você roda `docker build`, o Docker envia **todo o conteúdo da pasta** (build context) pro daemon. Sem `.dockerignore`:
- `.git/` pode ter centenas de MB
- `__pycache__/` é lixo
- `*.md` e `Dockerfile*` não precisam estar dentro da imagem
- `.env` pode ter **secrets** — nunca deve entrar na imagem!

---

## Parte 6 — App de exemplo consumindo a imagem base

### 6.1 Código da API

```bash
cat > examples/fastapi-app/app/__init__.py << 'EOF'
EOF

cat > examples/fastapi-app/app/main.py << 'EOF'
from fastapi import FastAPI

app = FastAPI(title="Example App")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return [
        {"id": 1, "name": "Item A"},
        {"id": 2, "name": "Item B"},
    ]
EOF
```

### 6.2 Dockerfile do projeto consumidor

```bash
cat > examples/fastapi-app/Dockerfile << 'EOF'
# A imagem base já tem fastapi + uvicorn instalados
FROM vivikk/imagem-base-otimizada:latest

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

> Percebe como é simples? Toda a parte pesada (Python, FastAPI, Uvicorn, user, healthcheck) já tá na imagem base. O projeto só copia o código.

### 6.3 docker-compose para desenvolvimento

```bash
cat > examples/fastapi-app/docker-compose.yml << 'EOF'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
    environment:
      - ENV=development
EOF
```

> O `volumes: ./app:/app/app` faz com que mudanças no código local reflitam no container sem precisar rebuildar. Ideal para desenvolvimento.

---

## Parte 7 — GitHub Actions (CI/CD)

### 7.1 O workflow

```bash
cat > .github/workflows/build-push.yml << 'EOF'
name: Build and Push Base Images

on:
  push:
    branches: [main]
    paths:
      - 'python-fastapi/**'
      - 'node-api/**'
#
# Só roda quando:
# 1. Push na branch main
# 2. Algum arquivo dentro de python-fastapi/ ou node-api/ mudou
# Se mudar só o README.md da raiz, NÃO dispara

env:
  DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      python-fastapi: ${{ steps.filter.outputs.python-fastapi }}
      node-api: ${{ steps.filter.outputs.node-api }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            python-fastapi:
              - 'python-fastapi/**'
            node-api:
              - 'node-api/**'
#
# dorny/paths-filter = detecta QUAL pasta mudou
# Saída: python-fastapi=true/false, node-api=true/false
# Isso permite buildar APENAS a imagem que mudou

  build-python-fastapi:
    needs: detect-changes
    if: needs.detect-changes.outputs.python-fastapi == 'true'
#   ↑ Só roda se python-fastapi/ teve mudança
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3
#       ↑ Configura BuildKit (builder avançado do Docker)
#         Necessário para cache entre builds

      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
#       ↑ Faz login no Docker Hub usando os secrets do repo

      - uses: docker/build-push-action@v6
        with:
          context: ./python-fastapi
          push: true
          tags: |
            ${{ env.DOCKERHUB_USERNAME }}/imagem-base-otimizada:latest
            ${{ env.DOCKERHUB_USERNAME }}/imagem-base-otimizada:${{ github.sha }}
#         ↑ Pusha com 2 tags:
#           - latest = sempre a versão mais recente
#           - sha do commit = versão específica (pra rollback)
          cache-from: type=gha
          cache-to: type=gha,mode=max
#         ↑ Usa cache do GitHub Actions entre builds
#           Primeiro build: ~12min (sem cache)
#           Builds seguintes: ~2min (com cache)
EOF
```

### 7.2 Configurar os secrets no GitHub

1. Vai em **Settings** → **Secrets and variables** → **Actions**
2. Clica **New repository secret**
3. Adiciona:
   - `DOCKERHUB_USERNAME` → seu user do Docker Hub
   - `DOCKERHUB_TOKEN` → gera em https://hub.docker.com/settings/security → **New Access Token** (permissão Read & Write)

### 7.3 Como funciona o fluxo

```
git push (altera python-fastapi/Dockerfile)
    ↓
GitHub Actions detecta mudança em python-fastapi/
    ↓
dorny/paths-filter confirma: python-fastapi=true
    ↓
Job build-python-fastapi roda:
    1. Checkout do código
    2. Setup BuildKit
    3. Login no Docker Hub
    4. Build da imagem
    5. Push para vivikk/imagem-base-otimizada:latest
    ↓
Imagem disponível no Docker Hub!
```

---

## Parte 8 — Publicando no GitHub

```bash
cd docker-optimized-images

# Inicializa o git
git init
git branch -m main

# Adiciona e commita
git add .
git commit -m "feat: docker optimized base images with CI/CD"

# Conecta ao repo remoto (crie antes em github.com/new)
git remote add origin git@github.com:SEU_USER/docker-optimized-images.git

# Push
git push -u origin main
```

---

## Resumo das técnicas

| Técnica | O que faz | Impacto |
|---------|-----------|---------|
| Multi-stage build | Separa build de runtime | Imagem final sem lixo |
| python:3.12-slim | Imagem base menor | ~50MB vs ~350MB |
| `--prefix=/install` | Instala deps em dir isolado | Copia só o necessário |
| Non-root user | Roda como appuser | Segurança |
| HEALTHCHECK | Verifica saúde da app | Auto-restart |
| Layer caching | requirements.txt antes do código | Build rápido |
| .dockerignore | Exclui arquivos do build | Build menor e seguro |
| ENV PYTHONDONTWRITEBYTECODE | Sem .pyc | Menos lixo |
| ENV PYTHONUNBUFFERED | Logs em tempo real | Melhor debug |
| Base Image Pattern | Imagem base centralizada | Padronização + velocidade |
| GHA cache | Cache entre builds na CI | 12min → 2min |

---

## Próximos passos (Parte 2 — Segurança)

- [ ] Trivy scan na pipeline
- [ ] Docker Scout
- [ ] Read-only filesystem
- [ ] Pinning de versão com hash
- [ ] Remover shell da imagem final
- [ ] COPY --chmod
