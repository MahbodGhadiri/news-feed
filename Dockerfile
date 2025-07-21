FROM python:3.11-slim

# Install OS dependencies if needed (optional)
RUN apt-get update && apt-get install -y curl

WORKDIR /app

# Copy everything
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
