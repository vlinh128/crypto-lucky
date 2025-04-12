FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ .

# Expose port
EXPOSE 8888

# Use Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8888", "--workers", "4", "--timeout", "120", "web_server:app"] 