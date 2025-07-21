FROM python:3.11-slim

# Install OS dependencies if needed (optional)
RUN apt-get update && apt-get install -y curl

WORKDIR /app

# Copy everything
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
