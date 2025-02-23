FROM python:3.10

WORKDIR /Task

COPY . .


RUN pip install --upgrade pip
RUN pip install -r requirements.txt


EXPOSE 8000

# Run migrations and start Django server
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
