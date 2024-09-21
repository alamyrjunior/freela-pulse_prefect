FROM python:3.9-slim

# Defina diretório de trabalho
WORKDIR /app

# Instale o Prefect e dependências
RUN pip install -r requirements.txt
# Copie seus scripts de flow para o container
COPY . /app