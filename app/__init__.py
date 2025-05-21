# app/__init__.py
from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

    @app.route("/")
    def home():
        return "Hello from Capybara Clinic!"

    return app