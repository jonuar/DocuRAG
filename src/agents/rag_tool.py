import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.generation.chain import query
from src.ingestion.pipeline import get_stats
from loguru import logger


def query_docs(question: str, technology: str) -> str:
    """
    Busca respuestas en la documentación técnica oficial indexada.

    Args:
        question: Pregunta técnica en lenguaje natural
        technology: Tecnología a consultar. Valores válidos: 'fastapi', 'python'

    Returns:
        Respuesta basada en la documentación con fuentes incluidas
    """
    logger.info(f"query_docs called | tech={technology} | q={question[:60]}")

    try:
        result = query(question)
        answer = result["answer"]

        # Añadir fuentes al final de la respuesta
        if result["sources"]:
            sources_text = "\n\nFuentes consultadas:"
            for src in result["sources"]:
                label = src["section"] or src["url"]
                sources_text += f"\n- {label}: {src['url']}"
            answer += sources_text

        logger.info(f"query_docs completed | sources={len(result['sources'])}")
        return answer

    except Exception as e:
        logger.error(f"query_docs error: {e}")
        return f"Error al consultar la documentación: {str(e)}"


def list_technologies() -> str:
    """
    Lista las tecnologías disponibles en la base de conocimiento.

    Returns:
        Lista de tecnologías indexadas con cantidad de chunks
    """
    stats = get_stats()

    if stats["total_chunks"] == 0:
        return "No hay tecnologías indexadas todavía."

    lines = [f"Total chunks indexados: {stats['total_chunks']}\n"]
    lines.append("Tecnologías disponibles:")
    for tech, count in stats["by_technology"].items():
        lines.append(f"  - {tech}: {count} chunks")

    return "\n".join(lines)