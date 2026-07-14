#!/usr/bin/env bash
# Выход при любой ошибке
set -o errexit

# Установка зависимостей
pip install -r requirements.txt

# Сборка статики (CSS/JS) в одну папку
python manage.py collectstatic --no-input

# Применение миграций базы данных
python manage.py migrate