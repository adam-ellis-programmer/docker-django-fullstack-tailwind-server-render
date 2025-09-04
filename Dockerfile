# Stage 1: Build Tailwind CSS
FROM node:18-alpine AS css-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify

# Stage 2: Python application
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . /app/

# Copy built CSS from the CSS builder stage
COPY --from=css-builder /app/static/css/output.css ./static/css/output.css

# Collect static files for production
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Use gunicorn for production instead of runserver
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]