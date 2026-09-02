"""
Research Summarization Engine

A professional-grade research summarization engine built with LangChain and LCEL.
This package provides autonomous web research capabilities with local LLM support.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .config.settings import Settings
from .orchestrator import ResearchOrchestrator

__all__ = ["Settings", "ResearchOrchestrator", "__version__"]
