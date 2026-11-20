import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fitz
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.connection import Base
import backend.app.database.models  # noqa: F401
from backend.app.database.models import Entrevista, RespuestaEntrevista, Usuario
from backend.app.services.cv_management_service import analizar_y_guardar_cv
from backend.app.services.interview_management_service import obtener_historial_entrevistas
from backend.app.services.interview_simulator import generar_preguntas
from backend.app.services.telegram_account_service import vincular_telegram_a_usuario
from backend.app.services.user_service import registrar_usuario
from telegram_bot import auth as telegram_auth
from telegram_bot.auth import AUTH_USER_ID_KEY
from telegram_bot.handlers import (
    cancelar,
    entrevista_inicio,
    entrevista_responder,
)
from telegram_bot.states import ENTREVISTA_RESPUESTA
from telegram_bot.utils import mensaje_no_autenticado


@pytest.fixture
def db_session_factory(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(telegram_auth, "SessionLocal", TestingSessionLocal)
    yield TestingSessionLocal
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def make_update(text="", telegram_id=1001, chat_type="private"):
    message = SimpleNamespace(
        text=text,
        reply_text=AsyncMock(),
        delete=AsyncMock(),
        document=None,
    )
    chat = SimpleNamespace(type=chat_type)
    user = SimpleNamespace(id=telegram_id)
    return SimpleNamespace(
        message=message,
        effective_message=message,
        effective_chat=chat,
        effective_user=user,
    )


def make_context(user_data=None):
    return SimpleNamespace(user_data=user_data if user_data is not None else {})


def crear_usuario_y_vinculo(db, telegram_id, correo, contrasena="ClaveSegura123", nombres="Ana", apellidos="Pérez"):
    usuario = registrar_usuario(
        db=db,
        nombres=nombres,
        apellidos=apellidos,
        correo=correo,
        contrasena=contrasena,
    )
    vincular_telegram_a_usuario(db, telegram_id, usuario)
    db.refresh(usuario)
    return usuario


def crear_pdf_bytes(texto):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), texto)
    contenido = doc.tobytes()
    doc.close()
    return contenido


def crear_analisis(db, usuario, texto, nombre_archivo="cv.pdf"):
    return analizar_y_guardar_cv(db, usuario, nombre_archivo, crear_pdf_bytes(texto))


def textos_respuesta(update):
    return [call.args[0] for call in update.message.reply_text.await_args_list]


def test_usuario_no_autenticado(db_session_factory):
    update = make_update("6. Practicar entrevista laboral", telegram_id=9001)
    context = make_context()
    result = asyncio.run(entrevista_inicio(update, context))
    assert result == -1
    args, _ = update.message.reply_text.await_args
    assert args[0] == mensaje_no_autenticado()


def test_usuario_sin_analisis_de_cv(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9002, correo="int1@example.com")
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    update = make_update("6. Practicar entrevista laboral", telegram_id=9002)
    result = asyncio.run(entrevista_inicio(update, context))

    assert result == -1
    combinado = "\n".join(textos_respuesta(update))
    assert "3. Analizar mi hoja de vida" in combinado


def test_inicio_correcto_y_generacion_de_preguntas(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9003, correo="int2@example.com")
        # Perfil Backend
        crear_analisis(db, usuario, "Habilidades: Python FastAPI SQL Node.js Django Git Docker")
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    update = make_update("6. Practicar entrevista laboral", telegram_id=9003)
    state = asyncio.run(entrevista_inicio(update, context))

    assert state == ENTREVISTA_RESPUESTA
    assert context.user_data.get("entrevista_id") is not None
    assert context.user_data.get("entrevista_perfil") == "Desarrollador Backend"
    preguntas = context.user_data.get("entrevista_preguntas") or []
    assert len(preguntas) == 5
    assert context.user_data.get("entrevista_indice") == 0

    combinado = "\n".join(textos_respuesta(update))
    assert "Pregunta 1 de 5" in combinado
    assert preguntas[0] in combinado

    db = db_session_factory()
    try:
        entrevistas = db.query(Entrevista).filter(Entrevista.id_usuario == uid).all()
        assert len(entrevistas) == 1
        assert entrevistas[0].perfil == "Desarrollador Backend"
    finally:
        db.close()


def test_respuestas_pregunta_por_pregunta_y_evaluacion_correcta(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9004, correo="int3@example.com")
        crear_analisis(db, usuario, "Habilidades: Python FastAPI SQL Node.js Django Git Docker")
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    asyncio.run(entrevista_inicio(make_update("6. Practicar entrevista laboral", telegram_id=9004), context))

    # Primera pregunta (Backend): API REST - respuesta evaluable
    resp1 = make_update(
        "Una API REST permite la comunicación entre un cliente y un servidor mediante solicitudes HTTP.",
        telegram_id=9004,
    )
    state = asyncio.run(entrevista_responder(resp1, context))
    assert state == ENTREVISTA_RESPUESTA
    assert context.user_data.get("entrevista_indice") == 1
    txt1 = "\n".join(textos_respuesta(resp1))
    assert "Puntuación:" in txt1
    assert "Retroalimentación:" in txt1
    assert "Pregunta 2 de 5" in txt1

    # Completar el resto de preguntas
    respuestas_restantes = [
        "GET se usa para obtener datos y POST para enviar datos al servidor.",
        "Una clave primaria es un identificador único de cada registro en una tabla de base de datos.",
        "CRUD significa crear, leer, actualizar y eliminar registros.",
        "Uso try y except para manejar excepciones y validación de errores.",
    ]
    for i, texto in enumerate(respuestas_restantes, start=2):
        upd = make_update(texto, telegram_id=9004)
        state = asyncio.run(entrevista_responder(upd, context))
        if i < 5:
            assert state == ENTREVISTA_RESPUESTA
        else:
            assert state == -1

    combinado_final = "\n".join(textos_respuesta(upd))
    assert "Resumen de la entrevista" in combinado_final
    assert "Preguntas respondidas: 5" in combinado_final

    db = db_session_factory()
    try:
        usuario = db.query(Usuario).filter(Usuario.id == uid).first()
        historial = obtener_historial_entrevistas(db, usuario)
        assert historial["total_entrevistas"] == 1
        entrevista = historial["historial"][0]
        assert len(entrevista["respuestas"]) == 5
        assert all(r["puntuacion"] is not None for r in entrevista["respuestas"])
    finally:
        db.close()


def test_pregunta_no_reconocida_por_evaluador(db_session_factory):
    """Verifica que una pregunta sin criterios se guarde sin inventar puntuación."""
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9005, correo="int4@example.com")
        crear_analisis(db, usuario, "Habilidades: Python FastAPI SQL Node.js Django Git Docker")
        uid = usuario.id
        entrevista = Entrevista(perfil="Desarrollador Backend", id_usuario=uid)
        db.add(entrevista)
        db.commit()
        db.refresh(entrevista)
        entrevista_id = entrevista.id
    finally:
        db.close()

    pregunta_sin_criterios = "¿Cuál es tu expectativa profesional a largo plazo?"
    pregunta_siguiente = "¿Qué es una API REST y para qué se utiliza?"
    context = make_context(
        {
            AUTH_USER_ID_KEY: uid,
            "entrevista_id": entrevista_id,
            "entrevista_perfil": "Desarrollador Backend",
            "entrevista_preguntas": [pregunta_sin_criterios, pregunta_siguiente],
            "entrevista_indice": 0,
            "entrevista_respuestas": [],
        }
    )

    resp = make_update("Me gustaría crecer como desarrollador y liderar proyectos.", telegram_id=9005)
    state = asyncio.run(entrevista_responder(resp, context))
    assert state == ENTREVISTA_RESPUESTA  # continúa con la siguiente pregunta
    txt = "\n".join(textos_respuesta(resp))
    assert "no disponible" in txt.lower()
    assert "Respuesta evaluada" not in txt
    assert "Puntuación:" not in txt  # no inventar puntuación para la pregunta sin criterios

    db = db_session_factory()
    try:
        respuestas = db.query(RespuestaEntrevista).filter(RespuestaEntrevista.id_entrevista == entrevista_id).all()
        assert len(respuestas) == 1
        assert respuestas[0].puntuacion is None
        assert respuestas[0].retroalimentacion
    finally:
        db.close()
def test_cancelacion_de_entrevista(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9006, correo="int5@example.com")
        crear_analisis(db, usuario, "Habilidades: Python FastAPI SQL Node.js Django Git")
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    asyncio.run(entrevista_inicio(make_update("6. Practicar entrevista laboral", telegram_id=9006), context))
    assert context.user_data.get("entrevista_id") is not None

    update = make_update("Cancelar", telegram_id=9006)
    result = asyncio.run(cancelar(update, context))
    assert result == -1
    # Datos temporales de entrevista limpiados
    assert context.user_data.get("entrevista_id") is None
    assert context.user_data.get("entrevista_preguntas") is None
    assert context.user_data.get("entrevista_indice") is None


def test_aislamiento_entre_usuarios(db_session_factory):
    db = db_session_factory()
    try:
        u1 = crear_usuario_y_vinculo(db, telegram_id=9101, correo="iso_i1@example.com", nombres="Uno")
        u2 = crear_usuario_y_vinculo(db, telegram_id=9102, correo="iso_i2@example.com", nombres="Dos")
        crear_analisis(db, u1, "Habilidades: Python FastAPI SQL Node.js Django Git")
        crear_analisis(db, u2, "Habilidades: Python FastAPI SQL Node.js Django Git")
        u1_id, u2_id = u1.id, u2.id
    finally:
        db.close()

    # Usuario 1 inicia entrevista
    ctx1 = make_context({AUTH_USER_ID_KEY: u1_id})
    asyncio.run(entrevista_inicio(make_update("6. Practicar entrevista laboral", telegram_id=9101), ctx1))
    ent1_id = ctx1["user_data"].get("entrevista_id") if isinstance(ctx1, dict) else ctx1.user_data.get("entrevista_id")

    db = db_session_factory()
    try:
        user1 = db.query(Usuario).filter(Usuario.id == u1_id).first()
        user2 = db.query(Usuario).filter(Usuario.id == u2_id).first()
        hist1 = obtener_historial_entrevistas(db, user1)
        hist2 = obtener_historial_entrevistas(db, user2)
        assert hist1["total_entrevistas"] == 1
        assert hist2["total_entrevistas"] == 0

        # Usuario 2 no debe poder acceder/usar la entrevista de usuario 1 mediante servicio
        from backend.app.services.interview_management_service import evaluar_y_guardar_respuesta, InterviewManagementError
        preguntas = generar_preguntas("Desarrollador Backend")["preguntas"]
        with pytest.raises(InterviewManagementError):
            evaluar_y_guardar_respuesta(
                db=db,
                usuario=user2,
                id_entrevista=hist1["historial"][0]["id_entrevista"],
                pregunta=preguntas[0],
                respuesta="Respuesta de prueba",
                guardar_no_reconocida=True,
            )
    finally:
        db.close()

def test_compatibilidad_telegram_frontend_con_evaluacion(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9010, correo="front_eval@example.com")
        crear_analisis(db, usuario, "Habilidades: HTML CSS JavaScript React Git")
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    state = asyncio.run(entrevista_inicio(make_update("6. Practicar entrevista laboral", telegram_id=9010), context))
    assert state == ENTREVISTA_RESPUESTA
    assert context.user_data.get("entrevista_perfil") == "Desarrollador Frontend"

    preguntas = context.user_data.get("entrevista_preguntas") or []
    assert len(preguntas) == 5

    respuesta = (
        "HTML define la estructura del contenido, CSS se encarga de los estilos y la presentación visual, "
        "y JavaScript agrega interactividad y comportamiento dinámico."
    )
    resp = make_update(respuesta, telegram_id=9010)
    state = asyncio.run(entrevista_responder(resp, context))
    assert state == ENTREVISTA_RESPUESTA

    txt = "\n".join(textos_respuesta(resp))
    assert "Respuesta evaluada" in txt
    assert "Puntuación:" in txt
    assert "Retroalimentación:" in txt
    assert "no disponible" not in txt.lower()

    db = db_session_factory()
    try:
        entrevista = db.query(Entrevista).filter(Entrevista.id_usuario == uid).first()
        assert entrevista is not None
        respuestas = db.query(RespuestaEntrevista).filter(RespuestaEntrevista.id_entrevista == entrevista.id).all()
        assert len(respuestas) == 1
        assert respuestas[0].puntuacion is not None
        assert respuestas[0].retroalimentacion
    finally:
        db.close()
