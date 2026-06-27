import logging
from typing import Any

from app.utils.topic_analysis import build_consolidated_analysis

logger = logging.getLogger(__name__)


def analyze_pyq_local(content: str, subject: str | None = None) -> dict[str, Any]:
    """Topic-focused PYQ analysis across all uploaded papers."""
    num_documents = max(1, len(content.split("---")))
    return build_consolidated_analysis(
        content,
        subject=subject,
        num_documents=num_documents,
    )
