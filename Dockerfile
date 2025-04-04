FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create the app directory
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy the entire project
COPY . .

# Set Python path to include the current directory and the plantbook directory
ENV PYTHONPATH="/app:/app/plantbook"
ENV DJANGO_SETTINGS_MODULE="plantbook.PlantBook.settings"

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media

# Run collectstatic
RUN cd /app && python3 manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--pythonpath", "/app", "--chdir", "/app", "plantbook.wsgi:application", "--bind", "0.0.0.0:8000"]
