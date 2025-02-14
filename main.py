from flask import Flask, request, jsonify, send_file
import os
import subprocess
import openai
import json
import datetime
import shutil
import sqlite3
import requests
import markdown
import duckdb
import calendar
from PIL import Image
import librosa
import numpy as np
import pandas as pd
import bs4
import locale
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Retrieve OpenAI API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

DATA_DIR = "/data"

def validate_path(path):
    real_path = os.path.realpath(path)
    if not real_path.startswith(os.path.realpath(DATA_DIR)):
        raise ValueError("Access outside /data is not allowed")
    return real_path

def extract_text_from_html(html_content):
    """Extracts text from an HTML page using BeautifulSoup."""
    soup = bs4.BeautifulSoup(html_content, 'html.parser')
    return soup.get_text()

def interpret_task(task):
    """Uses an LLM to interpret the task description and determine the required steps."""
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Parse this task into a structured JSON format: {task}"}],
        api_key=OPENAI_API_KEY
    )
    task_details = json.loads(response["choices"][0]["message"]["content"].strip())
    
    allowed_actions = {"count_weekday", "fetch_api", "clone_git", "run_sql", "scrape_website", "resize_image", "transcribe_audio", "convert_markdown", "filter_csv"}
    if task_details.get("action") not in allowed_actions:
        raise ValueError("Invalid action detected in task.")
    
    return task_details

def count_weekday_in_year(year, weekday):
    """Counts occurrences of a specific weekday in a given year."""
    try:
        count = sum(1 for month in range(1, 13)
                    for day in range(1, calendar.monthrange(year, month)[1] + 1)
                    if datetime.date(year, month, day).weekday() == weekday)
        return jsonify({"status": "success", "message": f"{count} {datetime.date(year, 1, 1).strftime('%A')}(s) in {year}", "count": count}), 200
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date encountered"}), 400

def resize_image(input_path, output_path, width, height):
    try:
        with Image.open(input_path) as img:
            img = img.resize((width, height))
            img.save(output_path)
        return jsonify({"status": "success", "message": "Image resized"}), 200
    except (IOError, ValueError) as e:
        return jsonify({"status": "error", "message": str(e)}), 400

def scrape_website(url, output):
    response = requests.get(url)
    if response.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to fetch website"}), 400
    text_content = extract_text_from_html(response.text)
    with open(output, "w") as f:
        f.write(text_content)
    return jsonify({"status": "success", "message": "Website scraped"}), 200

def execute_task(task):
    try:
        task_details = interpret_task(task)
        action = task_details.get("action")
        params = task_details.get("params", {})
        
        if action == "count_weekday":
            return count_weekday_in_year(int(params.get("year")), params.get("weekday"))
        elif action == "scrape_website":
            return scrape_website(params.get("url"), validate_path(params.get("output")))
        elif action == "resize_image":
            return resize_image(validate_path(params.get("file")), validate_path(params.get("output")), params.get("width"), params.get("height"))
        else:
            return jsonify({"status": "error", "message": "Unknown task action"}), 400
    except Exception as e:
        return jsonify({"status": "agent_error", "error": str(e)}), 500

@app.route('/run', methods=['POST'])
def run_task():
    data = request.get_json()
    task = data.get("task") if data else None
    if not task:
        return jsonify({"error": "No task provided"}), 400
    return execute_task(task)

@app.route('/read', methods=['GET'])
def read_file():
    path = validate_path(request.args.get('path'))
    if not os.path.exists(path):
        return "", 404
    return send_file(path, mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)
