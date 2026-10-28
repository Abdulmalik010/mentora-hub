"""Shared Flask extensions, instantiated once and attached in the app factory."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
