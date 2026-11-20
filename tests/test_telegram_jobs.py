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
from backend.app.database.models import RecomendacionLaboral, Usuario
from backend.app.services.cv_management_service import analizar_y_guardar_cv
from backend.app.services.job_management_service import obtener_historial_recomendaciones
from backend.app.services.telegram_account_service import vincular_telegram_a_usuario
from backend.app.services.user_service import registrar_usuario
from telegram_bot import auth as telegram_auth
from telegram_bot.auth import AUTH_USER_ID_KEY
from telegram_bot.handlers import buscar_ofertas_laborales
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


def make_update(text="5. Buscar ofertas laborales", telegram_id=1001, chat_type="private"):
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


def crear_pdf_bytes(texto="Habilidades: Python, SQL, FastAPI, Git, Docker, JavaScript, React"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), texto)
    contenido = doc.tobytes()
    doc.close()
    return contenido


def crear_analisis_para_usuario(db, usuario, nombre_archivo="cv.pdf", texto=None):
    contenido = crear_pdf_bytes(texto or "Habilidades: Python, SQL, FastAPI, Git, Docker")
    return analizar_y_guardar_cv(db, usuario, nombre_archivo, contenido)


def test_usuario_no_autenticado(db_session_factory):
    update = make_update(telegram_id=8001)
    context = make_context()

    asyncio.run(buscar_ofertas_laborales(update, context))

    update.message.reply_text.assert_awaited()
    args, _ = update.message.reply_text.await_args
    assert args[0] == mensaje_no_autenticado()


def test_asociacion_incorrecta_de_telegram(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=8002, correo="jobs1@example.com")
        crear_analisis_para_usuario(db, usuario)
        usuario_id = usuario.id
    finally:
        db.close()

    # Sesión apunta al usuario pero la solicitud viene de otro Telegram no vinculado
    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    update = make_update(telegram_id=9998)

    asyncio.run(buscar_ofertas_laborales(update, context))

    assert context.user_data.get(AUTH_USER_ID_KEY) is None
    args, _ = update.message.reply_text.await_args
    assert args[0] == mensaje_no_autenticado()


def test_usuario_sin_analisis_de_cv(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=8003, correo="jobs2@example.com")
        usuario_id = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    update = make_update(telegram_id=8003)

    asyncio.run(buscar_ofertas_laborales(update, context))

    textos = [call.args[0] for call in update.message.reply_text.await_args_list]
    assert any("analizar primero" in t.lower() or "3. Analizar mi hoja de vida" in t for t in textos)


def test_generacion_exitosa_orden_persistencia_y_contenido(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=8004, correo="jobs3@example.com")
        crear_analisis_para_usuario(db, usuario, texto="Habilidades: Python, SQL, FastAPI, Git, Docker, React, JavaScript")
        usuario_id = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    update = make_update(telegram_id=8004)

    asyncio.run(buscar_ofertas_laborales(update, context))

    textos = [call.args[0] for call in update.message.reply_text.await_args_list]
    combinado = "\n".join(textos)

    # Mensaje de generación y aviso de ofertas demostrativas/académicas
    assert any("generando" in t.lower() for t in textos)
    assert ("demostrativ" in combinado.lower()) or ("académic" in combinado.lower()) or ("academic" in combinado.lower())
    assert "no corresponden a vacantes laborales reales" in combinado.lower()

    # Campos requeridos en resultados
    assert "Empresa:" in combinado
    assert "Modalidad:" in combinado
    assert "Porcentaje de compatibilidad:" in combinado
    assert "Habilidades coincidentes:" in combinado
    assert "Habilidades que le faltan al candidato:" in combinado
    # Nombre del cargo (catálogo demostrativo)
    assert "Desarrollador" in combinado or "Analista" in combinado or "Especialista" in combinado

    # Persistencia en SQLite
    db = db_session_factory()
    try:
        recs = db.query(RecomendacionLaboral).filter(RecomendacionLaboral.id_usuario == usuario_id).all()
        assert len(recs) > 0
        porcentajes_guardados = sorted([r.porcentaje_compatibilidad for r in recs], reverse=True)

        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        historial = obtener_historial_recomendaciones(db, usuario)
        assert historial["total_recomendaciones"] == len(recs)

        porcentajes_hist = [h["porcentaje_compatibilidad"] for h in historial["historial"]]
        assert sorted(porcentajes_hist, reverse=True) == porcentajes_guardados

        # Coherencia y orden de compatibilidad (mayor a menor) en los resultados mostrados
        import re
        porcentajes_mensaje = [float(x) for x in re.findall(r"Porcentaje de compatibilidad: ([0-9]+(?:\.[0-9]+)?)%", combinado)]
        assert len(porcentajes_mensaje) == len(recs)
        assert porcentajes_mensaje == sorted(porcentajes_mensaje, reverse=True)
        assert sorted(porcentajes_mensaje, reverse=True) == porcentajes_guardados
    finally:
        db.close()


def test_aislamiento_informacion_entre_usuarios(db_session_factory):
    db = db_session_factory()
    try:
        u1 = crear_usuario_y_vinculo(db, telegram_id=8101, correo="iso1@example.com", nombres="Uno")
        u2 = crear_usuario_y_vinculo(db, telegram_id=8102, correo="iso2@example.com", nombres="Dos")
        crear_analisis_para_usuario(db, u1, texto="Habilidades: Python, SQL, FastAPI, Git, Docker")
        crear_analisis_para_usuario(db, u2, texto="Habilidades: HTML, CSS, JavaScript, React, Git")
        u1_id, u2_id = u1.id, u2.id
    finally:
        db.close()

    # Generar recomendaciones solo para usuario 1
    context1 = make_context({AUTH_USER_ID_KEY: u1_id})
    update1 = make_update(telegram_id=8101)
    asyncio.run(buscar_ofertas_laborales(update1, context1))

    db = db_session_factory()
    try:
        user1 = db.query(Usuario).filter(Usuario.id == u1_id).first()
        user2 = db.query(Usuario).filter(Usuario.id == u2_id).first()
        hist1 = obtener_historial_recomendaciones(db, user1)
        hist2 = obtener_historial_recomendaciones(db, user2)

        assert hist1["total_recomendaciones"] > 0
        assert hist2["total_recomendaciones"] == 0
        assert all(r["id_recomendacion"] for r in hist1["historial"])

        recs_u1 = db.query(RecomendacionLaboral).filter(RecomendacionLaboral.id_usuario == u1_id).all()
        recs_u2 = db.query(RecomendacionLaboral).filter(RecomendacionLaboral.id_usuario == u2_id).all()
        assert len(recs_u1) > 0
        assert len(recs_u2) == 0
    finally:
        db.close()
