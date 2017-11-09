#!/bin/bash

# Migrate app
python manage.py makemigrations
python manage.py migrate

# Migrate django_sec
python manage.py makemigrations django_sec
python manage.py migrate django_sec

# Download records and fill database
python manage.py sec_import_index --start-year=2009 --end-year=$(date +"%Y")
