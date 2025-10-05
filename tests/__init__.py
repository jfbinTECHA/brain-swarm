"""
Brain Swarm Testing Suite

This module contains comprehensive tests for the Brain Swarm multi-agent system.
Tests are organized by component and functionality.

Test Categories:
- unit: Individual component tests
- integration: Multi-component interaction tests
- api: REST API endpoint tests
- performance: Load and performance tests
- memory: Memory system tests
- federation: Multi-node tests

Usage:
    # Run all tests
    pytest

    # Run specific category
    pytest -m unit

    # Run with coverage
    pytest --cov=brain_swarm

    # Run specific test file
    pytest brain_swarm/tests/test_coordinator.py
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import MagicMock, AsyncMock

# Test utilities and fixtures
from .conftest import *

__all__ = [
    'pytest',
    'asyncio',
    'MagicMock',
    'AsyncMock'
]