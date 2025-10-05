"""
FastAPI-based REST API for Brain Swarm

Provides REST endpoints for task submission, monitoring, and management.
"""

from .main import app

__all__ = ['app']