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
from backend.app.database.models import Usuario
from backend.app.services.cv_management_service import analizar_y_guardar_cv
from backend.app.services.job_management_service import generar_y_guardar_recomendaciones
from backend.app.services.interview_management_service import evaluar_y_guardar_respuesta, generar_y_guardar_entrevista
from backend.app.services.telegram_account_service import vincular_telegram_a_usuario
from backend.app.services.user_service import registrar_usuario
from telegram_bot import auth as telegram_auth
from telegram_bot.auth import AUTH_USER_ID_KEY
from telegram_bot.handlers import historial_inicio, historial_opcion
from telegram_bot.states import HISTORIAL_MENU
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


def textos(update):
    return [call.args[0] for call in update.message.reply_text.await_args_list]


def crear_usuario_y_vinculo(db, telegram_id, correo, contrasena="ClaveSegura123", nombres="Ana", apellidos="Pérez"):
    usuario = registrar_usuario(db=db, nombres=nombres, apellidos=apellidos, correo=correo, contrasena=contrasena)
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


def seed_datos_usuario(db, usuario):
    # CV análisis
    analizar_y_guardar_cv(
        db, usuario, "cv_test.pdf",
        crear_pdf_bytes("Habilidades: Python FastAPI SQL Node.js Django Git Docker"),
    )
    # Recomendaciones
    generar_y_guardar_recomendaciones(db, usuario)
    # Entrevista con una respuesta evaluada y una no reconocida
    entrevista = generar_y_guardar_entrevista(db, usuario, "Desarrollador Backend")
    preguntas = entrevista["preguntas"]
    # Primera pregunta backend es reconocible
    evaluar_y_guardar_respuesta(
        db, usuario, entrevista["id_entrevista"], preguntas[0],
        "Una API REST usa HTTP para que cliente y servidor se comuniquen con solicitudes.",
    )
    # Forzar una pregunta no reconocida guardada
    evaluar_y_guardar_respuesta(
        db, usuario, entrevista["id_entrevista"], "Pregunta sin criterios conocidos",
        "Respuesta libre del usuario",
        guardar_no_reconocida=True,
    )


def test_usuario_no_autenticado(db_session_factory):
    update = make_update("7. Consultar mi historial", telegram_id=9201)
    context = make_context()
    result = asyncio.run(historial_inicio(update, context))
    assert result == -1
    assert textos(update)[0] == mensaje_no_autenticado()


def test_asociacion_incorrecta_de_telegram(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9202, correo="h1@example.com")
        uid = usuario.id
    finally:
        db.close()

    # Sesión del usuario pero desde otro telegram no vinculado
    context = make_context({AUTH_USER_ID_KEY: uid})
    update = make_update("7. Consultar mi historial", telegram_id=9997)
    result = asyncio.run(historial_inicio(update, context))
    assert result == -1
    assert context.user_data.get(AUTH_USER_ID_KEY) is None
    assert textos(update)[0] == mensaje_no_autenticado()

    # También al intentar consultar una opción del historial
    context2 = make_context({AUTH_USER_ID_KEY: uid})
    update2 = make_update("1. Mis análisis de hojas de vida", telegram_id=9997)
    result2 = asyncio.run(historial_opcion(update2, context2))
    assert result2 == -1
    assert context2.user_data.get(AUTH_USER_ID_KEY) is None
    assert textos(update2)[0] == mensaje_no_autenticado()


def test_navegacion_menu_historial(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9203, correo="h2@example.com")
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    up_inicio = make_update("7. Consultar mi historial", telegram_id=9203)
    state = asyncio.run(historial_inicio(up_inicio, context))
    assert state == HISTORIAL_MENU
    combinado_inicio = "\n".join(textos(up_inicio))
    assert "historial" in combinado_inicio.lower()

    # Opción inválida mantiene en menú
    up_inv = make_update("Opción inválida", telegram_id=9203)
    state_inv = asyncio.run(historial_opcion(up_inv, context))
    assert state_inv == HISTORIAL_MENU

    # Volver al menú principal
    up_volver = make_update("4. Volver al menú principal", telegram_id=9203)
    state_volver = asyncio.run(historial_opcion(up_volver, context))
    assert state_volver == -1
    combinado_volver = "\n".join(textos(up_volver))
    assert "menú principal" in combinado_volver.lower()


def test_usuario_sin_registros(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9204, correo="h3@example.com")
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    asyncio.run(historial_inicio(make_update("7. Consultar mi historial", telegram_id=9204), context))

    for opcion, esperado in [
        ("1. Mis análisis de hojas de vida", "No tienes análisis"),
        ("2. Mis recomendaciones laborales", "No tienes recomendaciones"),
        ("3. Mis entrevistas realizadas", "No tienes entrevistas"),
    ]:
        up = make_update(opcion, telegram_id=9204)
        state = asyncio.run(historial_opcion(up, context))
        assert state == HISTORIAL_MENU
        combinado = "\n".join(textos(up))
        assert esperado in combinado


def test_historial_cv_recomendaciones_y_entrevistas(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=9205, correo="h4@example.com")
        seed_datos_usuario(db, usuario)
        uid = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: uid})
    asyncio.run(historial_inicio(make_update("7. Consultar mi historial", telegram_id=9205), context))

    # CV
    up_cv = make_update("1. Mis análisis de hojas de vida", telegram_id=9205)
    assert asyncio.run(historial_opcion(up_cv, context)) == HISTORIAL_MENU
    cv_txt = "\n".join(textos(up_cv))
    assert "cv_test.pdf" in cv_txt
    assert "Fecha del análisis:" in cv_txt
    assert "Perfil profesional detectado:" in cv_txt
    assert "Habilidades identificadas:" in cv_txt

    # Recomendaciones
    up_rec = make_update("2. Mis recomendaciones laborales", telegram_id=9205)
    assert asyncio.run(historial_opcion(up_rec, context)) == HISTORIAL_MENU
    rec_txt = "\n".join(textos(up_rec))
    assert "Cargo:" in rec_txt
    assert "Empresa:" in rec_txt
    assert "Modalidad:" in rec_txt
    assert "Porcentaje de compatibilidad:" in rec_txt
    assert "Fecha de recomendación:" in rec_txt
    assert "demostrativ" in rec_txt.lower() or "no corresponden a vacantes laborales reales" in rec_txt.lower()

    # Entrevistas
    up_ent = make_update("3. Mis entrevistas realizadas", telegram_id=9205)
    assert asyncio.run(historial_opcion(up_ent, context)) == HISTORIAL_MENU
    ent_txt = "\n".join(textos(up_ent))
    assert "Perfil profesional:" in ent_txt
    assert "Fecha de realización:" in ent_txt
    assert "Preguntas respondidas:" in ent_txt
    assert "Puntuaciones disponibles:" in ent_txt
    assert "Retroalimentación registrada:" in ent_txt
    # Respuesta no evaluada debe aparecer sin puntuación inventada
    assert "sin puntuación automática" in ent_txt.lower()


def test_aislamiento_entre_usuarios(db_session_factory):
    db = db_session_factory()
    try:
        u1 = crear_usuario_y_vinculo(db, telegram_id=9301, correo="iso_h1@example.com", nombres="Uno")
        u2 = crear_usuario_y_vinculo(db, telegram_id=9302, correo="iso_h2@example.com", nombres="Dos")
        seed_datos_usuario(db, u1)
        u1_id, u2_id = u1.id, u2.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: u2_id})
    asyncio.run(historial_inicio(make_update("7. Consultar mi historial", telegram_id=9302), context))

    up_cv = make_update("1. Mis análisis de hojas de vida", telegram_id=9302)
    asyncio.run(historial_opcion(up_cv, context))
    assert "cv_test.pdf" not in "\n".join(textos(up_cv))
    assert "No tienes análisis" in "\n".join(textos(up_cv))

    up_rec = make_update("2. Mis recomendaciones laborales", telegram_id=9302)
    asyncio.run(historial_opcion(up_rec, context))
    assert "No tienes recomendaciones" in "\n".join(textos(up_rec))

    up_ent = make_update("3. Mis entrevistas realizadas", telegram_id=9302)
    asyncio.run(historial_opcion(up_ent, context))
    assert "No tienes entrevistas" in "\n".join(textos(up_ent))
