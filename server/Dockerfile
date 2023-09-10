FROM python:3.10
WORKDIR /
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1
COPY ./requirements.txt /app/requirements.txt
RUN echo /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

WORKDIR /app
EXPOSE 8888

#ENTRYPOINT ["/bin/sh", "start.sh"]
ENTRYPOINT ["uvicorn", "app.main:APP", "--log-config=log_config.yaml", "--proxy-headers", "--reload", "--host", "0.0.0.0", "--port", "8888"]