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
from backend.app.database.models import AnalisisCV, CuentaTelegram, HojaVida, Usuario
from backend.app.services.cv_management_service import obtener_historial_cv
from backend.app.services.telegram_account_service import vincular_telegram_a_usuario
from backend.app.services.user_service import registrar_usuario
from telegram_bot import auth as telegram_auth
from telegram_bot.auth import AUTH_USER_ID_KEY
from telegram_bot.handlers import cv_inicio, cv_recibir_documento
from telegram_bot.states import ESPERANDO_CV
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


def make_text_update(text="", telegram_id=1001, chat_type="private"):
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


def make_document_update(document, telegram_id=1001, chat_type="private", caption=None):
    message = SimpleNamespace(
        text=caption,
        reply_text=AsyncMock(),
        delete=AsyncMock(),
        document=document,
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


def crear_pdf_bytes(texto="Nombre: Ana\nHabilidades: Python SQL FastAPI Git Docker\nExperiencia: desarrollo backend"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), texto)
    contenido = doc.tobytes()
    doc.close()
    return contenido


def crear_documento_mock(nombre_archivo="cv.pdf", contenido=b"", file_size=None):
    contenido_bytes = bytearray(contenido)
    archivo = SimpleNamespace(
        download_as_bytearray=AsyncMock(return_value=contenido_bytes)
    )
    documento = SimpleNamespace(
        file_name=nombre_archivo,
        file_size=len(contenido) if file_size is None else file_size,
        get_file=AsyncMock(return_value=archivo),
    )
    return documento


def test_usuario_no_autenticado_cv(db_session_factory):
    update = make_text_update("3. Analizar mi hoja de vida", telegram_id=7001)
    context = make_context()

    result = asyncio.run(cv_inicio(update, context))

    assert result is -1
    update.message.reply_text.assert_awaited()
    args, _ = update.message.reply_text.await_args
    assert args[0] == mensaje_no_autenticado()


def test_recepcion_correcta_de_pdf(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=7002, correo="cv1@example.com")
        usuario_id = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    inicio = asyncio.run(cv_inicio(make_text_update("3. Analizar mi hoja de vida", telegram_id=7002), context))
    assert inicio == ESPERANDO_CV

    contenido = crear_pdf_bytes()
    doc = crear_documento_mock("micv.pdf", contenido)
    update = make_document_update(doc, telegram_id=7002)

    result = asyncio.run(cv_recibir_documento(update, context))
    assert result is -1

    # Debe informar procesamiento y luego resultado
    textos = [call.args[0] for call in update.message.reply_text.await_args_list]
    assert any("procesando" in t.lower() for t in textos)
    assert any("Análisis de hoja de vida completado" in t for t in textos)


def test_rechazo_archivo_no_pdf(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=7003, correo="cv2@example.com")
        usuario_id = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    asyncio.run(cv_inicio(make_text_update("3. Analizar mi hoja de vida", telegram_id=7003), context))

    doc = crear_documento_mock("archivo.txt", b"hola")
    update = make_document_update(doc, telegram_id=7003)
    result = asyncio.run(cv_recibir_documento(update, context))

    assert result == ESPERANDO_CV
    args, _ = update.message.reply_text.await_args
    assert "formato PDF" in args[0]


def test_pdf_vacio_o_ilegible(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=7004, correo="cv3@example.com")
        usuario_id = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    asyncio.run(cv_inicio(make_text_update("3. Analizar mi hoja de vida", telegram_id=7004), context))

    # PDF vacío (bytes vacíos) -> error claro y permite reintentar
    doc_vacio = crear_documento_mock("vacio.pdf", b"")
    update_vacio = make_document_update(doc_vacio, telegram_id=7004)
    result_vacio = asyncio.run(cv_recibir_documento(update_vacio, context))
    assert result_vacio == ESPERANDO_CV
    textos_vacio = [c.args[0] for c in update_vacio.message.reply_text.await_args_list]
    assert any("vacío" in t.lower() or "vacio" in t.lower() for t in textos_vacio)

    # PDF ilegible/sin texto legible -> error de procesamiento
    context2 = make_context({AUTH_USER_ID_KEY: usuario_id})
    asyncio.run(cv_inicio(make_text_update("3. Analizar mi hoja de vida", telegram_id=7004), context2))
    doc_ilegible = crear_documento_mock("ilegible.pdf", b"%PDF-1.4 contenido no legible")
    update_ilegible = make_document_update(doc_ilegible, telegram_id=7004)
    result_ilegible = asyncio.run(cv_recibir_documento(update_ilegible, context2))
    assert result_ilegible is -1
    textos_ilegible = [c.args[0] for c in update_ilegible.message.reply_text.await_args_list]
    assert any("No fue posible procesar el PDF" in t or "No fue posible leer el PDF" in t or "no fue posible" in t.lower() for t in textos_ilegible)


def test_analisis_exitoso_y_persistencia(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=7005, correo="cv4@example.com")
        usuario_id = usuario.id
    finally:
        db.close()

    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    asyncio.run(cv_inicio(make_text_update("3. Analizar mi hoja de vida", telegram_id=7005), context))

    contenido = crear_pdf_bytes(
        "Ingeniera de software. Habilidades: Python, SQL, JavaScript, React, FastAPI, Git y Docker"
    )
    doc = crear_documento_mock("cv_ana.pdf", contenido)
    update = make_document_update(doc, telegram_id=7005)
    result = asyncio.run(cv_recibir_documento(update, context))
    assert result is -1

    textos = [call.args[0] for call in update.message.reply_text.await_args_list]
    resultado_msg = next(t for t in textos if "Análisis de hoja de vida completado" in t)
    assert "cv_ana.pdf" in resultado_msg
    assert "Cantidad de habilidades encontradas:" in resultado_msg
    assert "Perfil profesional identificado:" in resultado_msg

    db = db_session_factory()
    try:
        hojas = db.query(HojaVida).filter(HojaVida.id_usuario == usuario_id).all()
        assert len(hojas) == 1
        assert hojas[0].nombre_archivo == "cv_ana.pdf"
        analisis = db.query(AnalisisCV).filter(AnalisisCV.id_hoja_vida == hojas[0].id).all()
        assert len(analisis) == 1
        assert analisis[0].habilidades is not None
    finally:
        db.close()


def test_asociacion_incorrecta_de_telegram(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario_y_vinculo(db, telegram_id=7006, correo="cv5@example.com")
        # Sesión activa apunta al usuario, pero el request vendrá desde otro telegram_id sin vínculo correcto
        usuario_id = usuario.id
    finally:
        db.close()

    # Telegram distinto al vinculado intenta usar la sesión
    context = make_context({AUTH_USER_ID_KEY: usuario_id})
    update = make_text_update("3. Analizar mi hoja de vida", telegram_id=9999)
    result = asyncio.run(cv_inicio(update, context))

    assert result is -1
    assert context.user_data.get(AUTH_USER_ID_KEY) is None
    args, _ = update.message.reply_text.await_args
    assert args[0] == mensaje_no_autenticado()


def test_aislamiento_historial_entre_usuarios(db_session_factory):
    db = db_session_factory()
    try:
        usuario1 = crear_usuario_y_vinculo(db, telegram_id=7101, correo="hist1@example.com", nombres="Uno")
        usuario2 = crear_usuario_y_vinculo(db, telegram_id=7102, correo="hist2@example.com", nombres="Dos")
        u1_id, u2_id = usuario1.id, usuario2.id

        # Crear análisis para usuario 1
        from backend.app.services.cv_management_service import analizar_y_guardar_cv
        contenido = crear_pdf_bytes("Habilidades: Python SQL FastAPI Docker Git")
        analizar_y_guardar_cv(db, usuario1, "cv_u1.pdf", contenido)
    finally:
        db.close()

    db = db_session_factory()
    try:
        u1 = db.query(Usuario).filter(Usuario.id == u1_id).first()
        u2 = db.query(Usuario).filter(Usuario.id == u2_id).first()
        hist1 = obtener_historial_cv(db, u1)
        hist2 = obtener_historial_cv(db, u2)

        assert hist1["total_hojas_vida"] == 1
        assert hist1["historial"][0]["nombre_archivo"] == "cv_u1.pdf"
        assert hist2["total_hojas_vida"] == 0
        assert hist2["historial"] == []

        # Verificar que las hojas de vida en BD pertenecen al usuario correcto
        hojas_u1 = db.query(HojaVida).filter(HojaVida.id_usuario == u1_id).all()
        hojas_u2 = db.query(HojaVida).filter(HojaVida.id_usuario == u2_id).all()
        assert len(hojas_u1) == 1
        assert len(hojas_u2) == 0
    finally:
        db.close()
