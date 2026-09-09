"""
Research Summarization Engine

LangGraph-based research summarization with dual Markdown/PDF output.
"""

__version__ = "2.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .config.settings import Settings
from .orchestrator import ResearchOrchestrator

__all__ = ["Settings", "ResearchOrchestrator", "__version__"]
