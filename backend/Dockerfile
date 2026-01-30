FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema se necessário
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expõe a porta (ajuste se seu app.main rodar em outra porta, padrão uvicorn é 8000)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]