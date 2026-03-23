# A imagem base já tem fastapi + uvicorn instalados
# Aqui só adicionamos dependências extras da app
FROM vivikk/imagem-base-otimizada:latest

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
