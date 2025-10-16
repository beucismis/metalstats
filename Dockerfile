FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV SPOTIFY_REDIRECT_URI=http://localhost:8000/callback
ENV METALSTATS_DATA_DIR=/data

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir .

COPY . .

RUN mkdir -p ${METALSTATS_DATA_DIR}

EXPOSE 8000

CMD ["uvicorn", "metalstats.main:app", "--host", "0.0.0.0", "--port", "8000"]
