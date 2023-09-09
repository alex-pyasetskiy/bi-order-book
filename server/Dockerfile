FROM python:3.10
WORKDIR /
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1
COPY ./requirements.txt /app/requirements.txt
RUN echo /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

EXPOSE 8888


CMD start.sh

