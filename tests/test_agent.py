import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.assistant_agent import run_agent

preguntas = [
    "¿Qué tecnologías tienes disponibles?",
    "¿Cómo declaro un path parameter opcional en FastAPI?",
    "Compara cómo se manejan las listas en Python con cómo se usan como body en FastAPI",
]

for pregunta in preguntas:
    print(f"\n{'='*70}")
    print(f"PREGUNTA: {pregunta}")
    print(f"{'='*70}")
    respuesta = run_agent(pregunta)
    print(f"\nRESPUESTA FINAL:\n{respuesta}")
    print()