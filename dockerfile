# Use imagem base oficial do Python
FROM python:latest

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Get and downloads 
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY main.py .
# Comando padrão ao iniciar o container

CMD ["python", "main.py"]