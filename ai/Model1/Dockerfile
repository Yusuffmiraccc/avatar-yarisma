FROM python:3.12-slim
WORKDIR /app
COPY Model1/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY Model1/app ./Model1/app
COPY Model2/sql ./Model2/sql
ENV PYTHONPATH=/app/Model1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
