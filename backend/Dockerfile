FROM python:3.10-slim

WORKDIR /src

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código para DENTRO de uma pasta 'backend'
COPY . ./backend

# Avisa o Python para procurar módulos na pasta /src
ENV PYTHONPATH=/src

# Inicia usando o caminho completo do módulo
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
