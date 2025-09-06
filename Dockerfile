FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install hatchling
RUN pip install .

EXPOSE 8000
CMD ["uvicorn", "metalstats.main:app", "--host", "0.0.0.0", "--port", "8000"]