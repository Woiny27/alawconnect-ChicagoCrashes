FROM python:3.11

WORKDIR /app

COPY data_pipeline_prototype/requirements.txt .
RUN pip install -r requirements.txt

COPY data_pipeline_prototype/ .
COPY risk/ risk/

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]