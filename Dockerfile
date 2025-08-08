FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ollama_compliant.py .

EXPOSE 6000

CMD ["python", "ollama_compliant.py"]