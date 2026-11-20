PREGUNTAS_POR_PERFIL = {
    "Desarrollador Backend": [
        "¿Qué es una API REST y para qué se utiliza?",
        "¿Cuál es la diferencia entre GET y POST?",
        "¿Qué es una clave primaria en SQL?",
        "¿Qué son las operaciones CRUD?",
        "¿Cómo manejarías los errores en una aplicación backend?"
    ],

    "Desarrollador Frontend": [
        "¿Cuál es la diferencia entre HTML, CSS y JavaScript?",
        "¿Qué es React y para qué se utiliza?",
        "¿Qué es un componente en React?",
        "¿Qué es el estado (state) en React?",
        "¿Cómo harías que una página web sea adaptable?"
    ],

    "Analista de Datos": [
        "¿Qué es el análisis de datos?",
        "¿Para qué se utiliza SQL?",
        "¿Cuál es la diferencia entre una tabla y un gráfico?",
        "¿Qué es Power BI?",
        "¿Cómo identificarías datos inconsistentes?"
    ],

    "Especialista en Machine Learning": [
        "¿Qué es Machine Learning?",
        "¿Cuál es la diferencia entre aprendizaje supervisado y no supervisado?",
        "¿Qué es un conjunto de entrenamiento?",
        "¿Qué es el sobreajuste (overfitting)?",
        "¿Para qué se utiliza Scikit-learn?"
    ]
}


def generar_preguntas(perfil: str) -> dict:
    """
    Genera preguntas de entrevista según
    el perfil profesional del candidato.
    """

    preguntas = PREGUNTAS_POR_PERFIL.get(perfil)

    if preguntas is None:
        return {
            "perfil": perfil,
            "preguntas": [],
            "estado": "No existen preguntas para este perfil"
        }

    return {
        "perfil": perfil,
        "total_preguntas": len(preguntas),
        "preguntas": preguntas,
        "estado": "Preguntas generadas correctamente"
    }
