"""
QA Generation Module for Academic Research Paper Q&A Generator

This module provides question generation capabilities using free, open-source language models.
"""

from .question_generator import QuestionGenerator
from .config import MODEL_CONFIG, QUESTION_CONFIG, OUTPUT_CONFIG, PROMPT_TEMPLATES

__version__ = "1.0.0"
__author__ = "Gungun Pandey"

__all__ = [
    "QuestionGenerator",
    "MODEL_CONFIG", 
    "QUESTION_CONFIG",
    "OUTPUT_CONFIG",
    "PROMPT_TEMPLATES"
] 