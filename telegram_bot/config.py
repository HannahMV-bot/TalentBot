import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde la raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def get_telegram_bot_token() -> str:
    """Obtiene el token del bot de Telegram desde el entorno."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "La variable de entorno TELEGRAM_BOT_TOKEN no está configurada. "
            "Agrega el token en el archivo .env antes de iniciar el bot."
        )
    return token
