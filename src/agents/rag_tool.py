"""
DEPRECATED: Use src.agents.smart_retriever instead.

This module is kept for backward compatibility only.
All functionality has been moved to smart_retriever.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.smart_retriever import smart_search, list_technologies
from loguru import logger

# Backward compatibility alias
def query_docs(question: str, technology: str) -> str:
    """
    DEPRECATED: Use smart_search() instead.
    This function is maintained for backward compatibility only.
    """
    logger.warning("query_docs() is deprecated, use smart_search() instead")
    return smart_search(question)


__all__ = ["smart_search", "list_technologies", "query_docs"]

