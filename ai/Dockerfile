FROM python:3.10-slim

WORKDIR /src

# Instala dependências
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código para DENTRO de uma pasta 'ai'
COPY . ./ai

# Avisa o Python para procurar módulos na pasta /src
ENV PYTHONPATH=/src

CMD ["uvicorn", "ai.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
