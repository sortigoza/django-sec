FROM python:2-jessie

WORKDIR /django_sec

RUN apt-get update && apt-get install -y \
    vim python-dev libmysqlclient-dev

RUN pip install django psycopg2 lxml request mysqlclient django-sec

COPY . .

CMD ["/bin/bash", "-c", "while true; do sleep 1; done"]
#CMD ["python", "manage.py", "sec_import_index"]
