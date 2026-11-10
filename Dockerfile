# Используем легковесный образ Python
FROM python:3.11-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Отключаем буферизацию вывода, чтобы логи CLI отображались мгновенно
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Копируем файлы проекта
COPY main.py inventory.py storage.py ./
COPY data/ ./data/

# Создаем папку data, если её нет (для гарантии работы storage.py)
RUN mkdir -p data

# Запускаем скрипт (через python, так как это консольное приложение)
CMD ["python", "main.py"]