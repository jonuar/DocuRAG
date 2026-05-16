import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.generation.chain import query
from src.ingestion.pipeline import get_stats
from loguru import logger
from typing import Optional


def smart_search(question: str) -> str:
    """
    Búsqueda inteligente que automáticamente:
    1. Detecta palabras clave en la pregunta
    2. Busca en TODAS las tecnologías disponibles
    3. Ranquea por relevancia
    4. Sintetiza respuesta comparativa si aplica
    
    Args:
        question: Pregunta del usuario (sin especificar tecnología)
    
    Returns:
        Respuesta con fuentes de múltiples tecnologías si aplica
    """
    logger.info(f"smart_search called | q={question[:60]}")
    
    stats = get_stats()
    available_techs = list(stats["by_technology"].keys())
    
    if not available_techs:
        return "No hay tecnologías indexadas. Por favor, ingesta documentación primero."
    
    # Mapeo: palabras clave → tecnologías relevantes
    KEYWORD_TECH_MAP = {
        "fastapi": ["fastapi", "python"],
        "python": ["python"],
        "async": ["python", "fastapi"],
        "request": ["fastapi", "python"],
        "response": ["fastapi", "python"],
        "database": ["python"],
        "orm": ["python"],
        "validation": ["fastapi", "python"],
        "dependency": ["fastapi", "python"],
        "middleware": ["fastapi", "python"],
        "decorator": ["python", "fastapi"],
        "class": ["python"],
        "function": ["python"],
        "loop": ["python"],
        "type": ["python", "fastapi"],
        "model": ["fastapi", "python"],
    }
    
    # Detectar tecnologías relevantes
    relevant_techs = set()
    question_lower = question.lower()
    
    for keyword, techs in KEYWORD_TECH_MAP.items():
        if keyword in question_lower:
            relevant_techs.update(techs)
    
    # Si no detectó nada, busca en todas
    if not relevant_techs:
        relevant_techs = set(available_techs)
    
    # Filtrar solo las disponibles
    relevant_techs = [t for t in relevant_techs if t in available_techs]
    logger.info(f"Detected relevant technologies: {relevant_techs}")
    
    # Buscar en cada tecnología relevante
    all_results = {}
    for tech in relevant_techs:
        try:
            result = query(question, technology=tech)
            all_results[tech] = {
                "answer": result["answer"],
                "sources": result["sources"],
                "confidence": result.get("confidence", 0.0)
            }
        except Exception as e:
            logger.warning(f"Error searching {tech}: {e}")
            all_results[tech] = {"answer": "", "sources": [], "confidence": 0.0}
    
    # Sintetizar respuesta
    response = _synthesize_response(question, all_results)
    
    logger.info(f"smart_search completed | techs_searched={len([r for r in all_results.values() if r['answer']])}")
    return response


def _synthesize_response(question: str, all_results: dict) -> str:
    """
    Sintetiza resultados de múltiples fuentes.
    Si hay info de una sola tech, retorna simple.
    Si hay de múltiples, hace análisis comparativo.
    """
    
    # Filtrar resultados con contenido
    valid_results = {
        tech: data for tech, data in all_results.items()
        if data["answer"].strip()
    }
    
    if not valid_results:
        return "No encontré información relevante en la documentación indexada."
    
    if len(valid_results) == 1:
        # Respuesta simple de una tecnología
        tech = list(valid_results.keys())[0]
        data = valid_results[tech]
        response = data["answer"]
        
        if data["sources"]:
            response += f"\n\n**Fuentes ({tech.upper()}):**"
            for src in data["sources"]:
                label = src.get("section") or src["url"]
                response += f"\n- {label}"
        
        return response
    
    else:
        # Respuesta comparativa / múltiples fuentes
        response = "Encontré información en múltiples documentaciones:\n\n"
        
        for tech, data in valid_results.items():
            response += f"### {tech.upper()}\n{data['answer']}\n"
            
            if data["sources"]:
                response += "\n**Fuentes:**\n"
                for src in data["sources"]:
                    label = src.get("section") or src["url"]
                    response += f"- {label}\n"
            
            response += "\n---\n"
        
        return response.rstrip()


def list_technologies() -> str:
    """Lista tecnologías disponibles."""
    stats = get_stats()
    
    if stats["total_chunks"] == 0:
        return "No hay tecnologías indexadas."
    
    lines = [f"**Total chunks:** {stats['total_chunks']}\n"]
    lines.append("**Tecnologías disponibles:**")
    for tech, count in stats["by_technology"].items():
        lines.append(f"- {tech}: {count} chunks")
    
    return "\n".join(lines)
