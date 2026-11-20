import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.connection import Base
import backend.app.database.models  # noqa: F401 - registra modelos
from backend.app.services.security import encriptar_contrasena
from backend.app.services.telegram_account_service import vincular_telegram_a_usuario
from backend.app.services.user_service import registrar_usuario
from telegram_bot import auth as telegram_auth
from telegram_bot.auth import AUTH_USER_ID_KEY
from telegram_bot.handlers import (
    cerrar_sesion,
    login_contrasena,
    login_correo,
    login_inicio,
    menu_principal,
    registro_apellidos,
    registro_contrasena,
    registro_correo,
    registro_inicio,
    registro_nombres,
)
from telegram_bot.states import (
    LOGIN_CONTRASENA,
    LOGIN_CORREO,
    REGISTRO_APELLIDOS,
    REGISTRO_CONTRASENA,
    REGISTRO_CORREO,
    REGISTRO_NOMBRES,
)
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

    # Redirigir las sesiones del bot a la base de datos de prueba en memoria
    monkeypatch.setattr(telegram_auth, "SessionLocal", TestingSessionLocal)

    yield TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def make_update(text="", telegram_id=1001, chat_type="private"):
    message = SimpleNamespace(
        text=text,
        reply_text=AsyncMock(),
        delete=AsyncMock(),
    )
    chat = SimpleNamespace(type=chat_type)
    user = SimpleNamespace(id=telegram_id)
    update = SimpleNamespace(
        message=message,
        effective_message=message,
        effective_chat=chat,
        effective_user=user,
    )
    return update


def make_context(user_data=None):
    return SimpleNamespace(user_data=user_data if user_data is not None else {})


def crear_usuario(db, nombres="Ana", apellidos="Pérez", correo="ana@example.com", contrasena="ClaveSegura123"):
    return registrar_usuario(
        db=db,
        nombres=nombres,
        apellidos=apellidos,
        correo=correo,
        contrasena=contrasena,
    )


def test_registro_exitoso(db_session_factory):
    update = make_update(text="1. Registrarme", telegram_id=2001)
    context = make_context()

    state = asyncio.run(registro_inicio(update, context))
    assert state == REGISTRO_NOMBRES

    state = asyncio.run(registro_nombres(make_update("Ana", telegram_id=2001), context))
    assert state == REGISTRO_APELLIDOS

    state = asyncio.run(registro_apellidos(make_update("García", telegram_id=2001), context))
    assert state == REGISTRO_CORREO

    state = asyncio.run(registro_correo(make_update("ana.nueva@example.com", telegram_id=2001), context))
    assert state == REGISTRO_CONTRASENA

    result = asyncio.run(registro_contrasena(make_update("Secreta123", telegram_id=2001), context))
    assert result is -1  # ConversationHandler.END

    db = db_session_factory()
    try:
        from backend.app.database.models import CuentaTelegram, Usuario
        usuario = db.query(Usuario).filter(Usuario.correo == "ana.nueva@example.com").first()
        assert usuario is not None
        assert usuario.contrasena != "Secreta123"
        vinculo = db.query(CuentaTelegram).filter(CuentaTelegram.telegram_id == 2001).first()
        assert vinculo is not None
        assert vinculo.id_usuario == usuario.id
    finally:
        db.close()

    assert context.user_data.get(AUTH_USER_ID_KEY) is not None


def test_correo_duplicado(db_session_factory):
    db = db_session_factory()
    try:
        crear_usuario(db, correo="duplicado@example.com")
    finally:
        db.close()

    context = make_context()
    state = asyncio.run(registro_inicio(make_update("1. Registrarme", telegram_id=2002), context))
    assert state == REGISTRO_NOMBRES
    asyncio.run(registro_nombres(make_update("Luis", telegram_id=2002), context))
    asyncio.run(registro_apellidos(make_update("Lopez", telegram_id=2002), context))

    result = asyncio.run(registro_correo(make_update("duplicado@example.com", telegram_id=2002), context))
    assert result is -1  # fin por correo duplicado

    # No debe crear vinculación ni sesión para este telegram
    db = db_session_factory()
    try:
        from backend.app.database.models import CuentaTelegram
        assert db.query(CuentaTelegram).filter(CuentaTelegram.telegram_id == 2002).first() is None
    finally:
        db.close()
    assert context.user_data.get(AUTH_USER_ID_KEY) is None


def test_correo_invalido(db_session_factory):
    context = make_context()
    asyncio.run(registro_inicio(make_update("1. Registrarme", telegram_id=2003), context))
    asyncio.run(registro_nombres(make_update("Marta", telegram_id=2003), context))
    asyncio.run(registro_apellidos(make_update("Ruiz", telegram_id=2003), context))

    state = asyncio.run(registro_correo(make_update("correo-invalido", telegram_id=2003), context))
    assert state == REGISTRO_CORREO
    assert context.user_data.get(AUTH_USER_ID_KEY) is None


def test_inicio_sesion_correcto(db_session_factory):
    db = db_session_factory()
    try:
        usuario = crear_usuario(db, correo="login@example.com", contrasena="ClaveCorrecta1")
    finally:
        db.close()

    context = make_context()
    state = asyncio.run(login_inicio(make_update("2. Iniciar sesión", telegram_id=3001), context))
    assert state == LOGIN_CORREO

    state = asyncio.run(login_correo(make_update("login@example.com", telegram_id=3001), context))
    assert state == LOGIN_CONTRASENA

    result = asyncio.run(login_contrasena(make_update("ClaveCorrecta1", telegram_id=3001), context))
    assert result is -1
    assert context.user_data.get(AUTH_USER_ID_KEY) == usuario.id

    db = db_session_factory()
    try:
        from backend.app.database.models import CuentaTelegram
        vinculo = db.query(CuentaTelegram).filter(CuentaTelegram.telegram_id == 3001).first()
        assert vinculo is not None
        assert vinculo.id_usuario == usuario.id
    finally:
        db.close()


def test_contrasena_incorrecta(db_session_factory):
    db = db_session_factory()
    try:
        crear_usuario(db, correo="badpass@example.com", contrasena="ClaveCorrecta1")
    finally:
        db.close()

    context = make_context()
    asyncio.run(login_inicio(make_update("2. Iniciar sesión", telegram_id=3002), context))
    asyncio.run(login_correo(make_update("badpass@example.com", telegram_id=3002), context))
    result = asyncio.run(login_contrasena(make_update("incorrecta", telegram_id=3002), context))

    assert result is -1
    assert context.user_data.get(AUTH_USER_ID_KEY) is None

    db = db_session_factory()
    try:
        from backend.app.database.models import CuentaTelegram
        assert db.query(CuentaTelegram).filter(CuentaTelegram.telegram_id == 3002).first() is None
    finally:
        db.close()


def test_telegram_vinculado_a_otra_cuenta(db_session_factory):
    db = db_session_factory()
    try:
        usuario_a = crear_usuario(db, nombres="A", apellidos="Uno", correo="a@example.com", contrasena="ClaveA123")
        usuario_b = crear_usuario(db, nombres="B", apellidos="Dos", correo="b@example.com", contrasena="ClaveB123")
        vincular_telegram_a_usuario(db, telegram_id=4001, usuario=usuario_a)
        usuario_a_id = usuario_a.id
    finally:
        db.close()

    context = make_context()
    asyncio.run(login_inicio(make_update("2. Iniciar sesión", telegram_id=4001), context))
    asyncio.run(login_correo(make_update("b@example.com", telegram_id=4001), context))
    result = asyncio.run(login_contrasena(make_update("ClaveB123", telegram_id=4001), context))

    assert result is -1
    assert context.user_data.get(AUTH_USER_ID_KEY) is None

    db = db_session_factory()
    try:
        from backend.app.database.models import CuentaTelegram
        vinculo = db.query(CuentaTelegram).filter(CuentaTelegram.telegram_id == 4001).first()
        assert vinculo is not None
        assert vinculo.id_usuario == usuario_a_id
    finally:
        db.close()


def test_cierre_sesion(db_session_factory):
    context = make_context({AUTH_USER_ID_KEY: 999})
    update = make_update("8. Cerrar sesión", telegram_id=5001)

    asyncio.run(cerrar_sesion(update, context))

    assert context.user_data.get(AUTH_USER_ID_KEY) is None
    update.message.reply_text.assert_awaited()
    args, _ = update.message.reply_text.await_args
    assert "Sesión cerrada" in args[0]


def test_usuario_no_autenticado_accede_opcion_protegida(db_session_factory):
    context = make_context()
    update = make_update("3. Analizar mi hoja de vida", telegram_id=6001)

    asyncio.run(menu_principal(update, context))

    update.message.reply_text.assert_awaited()
    args, _ = update.message.reply_text.await_args
    assert args[0] == mensaje_no_autenticado()
    assert context.user_data.get(AUTH_USER_ID_KEY) is None
