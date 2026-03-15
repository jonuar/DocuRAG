import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from src.generation.chain import query

preguntas = [
    "¿Qué es FastAPI y para qué sirve?",
    "¿Cómo declaro un path parameter en FastAPI?",
    "¿Cómo valido el tipo de datos en un endpoint?",
    "¿Qué diferencia hay entre query params y path params?",
    "¿Cómo instalo Django?",  # <- esta debería decir que no sabe
]

for p in preguntas:
    print(f"\n{'='*60}")
    print(f"PREGUNTA: {p}")
    print(f"{'='*60}")
    result = query(p)
    print(f"RESPUESTA:\n{result['answer']}")
    print(f"\nFUENTES:")
    for s in result['sources']:
        print(f"  - {s['url']}")