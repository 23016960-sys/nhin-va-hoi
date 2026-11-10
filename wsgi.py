"""Production entry point. Run with one Gunicorn worker: sessions live in RAM."""
from app import create_app

app = create_app()
