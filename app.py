"""Vercel entrypoint: re-export the FastAPI app from web_app."""

from web_app import app  # noqa: F401
