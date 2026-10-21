FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt modal==1.5.3
COPY api /app/api
COPY pipeline/__init__.py pipeline/config.py /app/pipeline/
COPY pipeline/temporal /app/pipeline/temporal
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
