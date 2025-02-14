FROM python:3.13
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV FLASK_APP=flask_task_api.py
ENV FLASK_ENV=production

EXPOSE 5000

# Command to run the Flask application
CMD ["python", "main.py"]
