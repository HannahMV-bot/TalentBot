import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.connection import Base
import backend.app.database.models  # noqa: F401
from backend.app.database.models import Entrevista, RespuestaEntrevista
from backend.app.services.interview_management_service import (
    InterviewManagementError,
    evaluar_y_guardar_respuesta,
    generar_y_guardar_entrevista,
)
from backend.app.services.user_service import registrar_usuario


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def crear_usuario(db, correo="eval@example.com"):
    return registrar_usuario(
        db=db,
        nombres="Eva",
        apellidos="Tester",
        correo=correo,
        contrasena="ClaveSegura123",
    )


def test_persistencia_puntuacion_y_retroalimentacion(db_session):
    usuario = crear_usuario(db_session)
    entrevista = generar_y_guardar_entrevista(db_session, usuario, "Desarrollador Frontend")

    pregunta = "¿Qué es React y para qué se utiliza?"
    respuesta = (
        "React es una biblioteca de JavaScript para crear interfaces de usuario "
        "mediante componentes reutilizables."
    )

    resultado = evaluar_y_guardar_respuesta(
        db=db_session,
        usuario=usuario,
        id_entrevista=entrevista["id_entrevista"],
        pregunta=pregunta,
        respuesta=respuesta,
    )

    assert resultado["id_respuesta"] is not None
    assert resultado["puntuacion"] is not None
    assert 0 <= resultado["puntuacion"] <= 100
    assert isinstance(resultado["retroalimentacion"], str)
    assert resultado["retroalimentacion"].strip()

    guardada = (
        db_session.query(RespuestaEntrevista)
        .filter(RespuestaEntrevista.id == resultado["id_respuesta"])
        .first()
    )
    assert guardada is not None
    assert guardada.pregunta == pregunta
    assert guardada.respuesta == respuesta
    assert guardada.puntuacion == resultado["puntuacion"]
    assert guardada.retroalimentacion == resultado["retroalimentacion"]


def test_persistencia_pregunta_no_reconocida_sin_puntuacion(db_session):
    usuario = crear_usuario(db_session, correo="norec@example.com")
    entrevista = generar_y_guardar_entrevista(db_session, usuario, "Desarrollador Backend")

    pregunta = "¿Cuál es tu meta profesional a cinco años?"
    respuesta = "Quiero crecer técnicamente y aportar valor al equipo."

    resultado = evaluar_y_guardar_respuesta(
        db=db_session,
        usuario=usuario,
        id_entrevista=entrevista["id_entrevista"],
        pregunta=pregunta,
        respuesta=respuesta,
        guardar_no_reconocida=True,
    )

    assert resultado["puntuacion"] is None
    assert resultado["estado"] == "Pregunta no reconocida"

    guardada = (
        db_session.query(RespuestaEntrevista)
        .filter(RespuestaEntrevista.id == resultado["id_respuesta"])
        .first()
    )
    assert guardada is not None
    assert guardada.puntuacion is None
    assert guardada.retroalimentacion


def test_pregunta_no_reconocida_lanza_error_si_no_se_permite_guardar(db_session):
    usuario = crear_usuario(db_session, correo="norec2@example.com")
    entrevista = generar_y_guardar_entrevista(db_session, usuario, "Desarrollador Backend")

    with pytest.raises(InterviewManagementError) as exc:
        evaluar_y_guardar_respuesta(
            db=db_session,
            usuario=usuario,
            id_entrevista=entrevista["id_entrevista"],
            pregunta="Pregunta fuera de criterios",
            respuesta="Respuesta libre",
            guardar_no_reconocida=False,
        )

    assert exc.value.status_code == 422
    assert db_session.query(RespuestaEntrevista).count() == 0

def test_historial_entrevistas_respeta_orden_real_y_asociaciones(db_session):
    usuario = crear_usuario(db_session, correo="orden@example.com")
    entrevista = Entrevista(perfil="Desarrollador Frontend", id_usuario=usuario.id)
    db_session.add(entrevista)
    db_session.commit()
    db_session.refresh(entrevista)

    # IDs secuenciales en el orden real de la entrevista
    respuestas = [
        RespuestaEntrevista(
            id=1,
            id_entrevista=entrevista.id,
            pregunta="¿Cuál es la diferencia entre HTML, CSS y JavaScript?",
            respuesta="HTML estructura, CSS estilos y JavaScript interactividad.",
            puntuacion=100.0,
            retroalimentacion="Retro HTML/CSS/JS",
        ),
        RespuestaEntrevista(
            id=2,
            id_entrevista=entrevista.id,
            pregunta="¿Qué es React y para qué se utiliza?",
            respuesta="Biblioteca de JavaScript para crear interfaces dinámicas e interactivas.",
            puntuacion=96.0,
            retroalimentacion="Retro React",
        ),
        RespuestaEntrevista(
            id=3,
            id_entrevista=entrevista.id,
            pregunta="¿Qué es un componente en React?",
            respuesta="Pieza reutilizable de interfaz, con ejemplos.",
            puntuacion=94.0,
            retroalimentacion="Retro Componentes",
        ),
        RespuestaEntrevista(
            id=4,
            id_entrevista=entrevista.id,
            pregunta="¿Qué es el estado (state) en React?",
            respuesta="Información que cambia y actualiza la interfaz.",
            puntuacion=95.0,
            retroalimentacion="Retro State",
        ),
        RespuestaEntrevista(
            id=5,
            id_entrevista=entrevista.id,
            pregunta="¿Cómo harías que una página web sea adaptable?",
            respuesta="Responsiva",
            puntuacion=4.0,
            retroalimentacion="Retro Responsive",
        ),
    ]

    # Insertar en orden distinto para simular colección no determinista
    for r in [respuestas[0], respuestas[4], respuestas[1], respuestas[3], respuestas[2]]:
        db_session.add(r)
    db_session.commit()

    from backend.app.services.interview_management_service import obtener_historial_entrevistas
    historial = obtener_historial_entrevistas(db_session, usuario)
    assert historial["total_entrevistas"] == 1
    respuestas_historial = historial["historial"][0]["respuestas"]

    preguntas_esperadas = [
        "¿Cuál es la diferencia entre HTML, CSS y JavaScript?",
        "¿Qué es React y para qué se utiliza?",
        "¿Qué es un componente en React?",
        "¿Qué es el estado (state) en React?",
        "¿Cómo harías que una página web sea adaptable?",
    ]
    puntuaciones_esperadas = [100.0, 96.0, 94.0, 95.0, 4.0]
    retros_esperadas = [
        "Retro HTML/CSS/JS",
        "Retro React",
        "Retro Componentes",
        "Retro State",
        "Retro Responsive",
    ]

    assert [r["pregunta"] for r in respuestas_historial] == preguntas_esperadas
    assert [r["puntuacion"] for r in respuestas_historial] == puntuaciones_esperadas
    assert [r["retroalimentacion"] for r in respuestas_historial] == retros_esperadas
    # Cada evaluación asociada a su pregunta correcta
    for r, pregunta, puntuacion, retro in zip(
        respuestas_historial, preguntas_esperadas, puntuaciones_esperadas, retros_esperadas
    ):
        assert r["pregunta"] == pregunta
        assert r["puntuacion"] == puntuacion
        assert r["retroalimentacion"] == retro
