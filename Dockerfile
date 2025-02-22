FROM docker.gh-proxy.com/library/python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    pip install -r requirements.txt gunicorn

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]
