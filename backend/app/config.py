import os

from dotenv import load_dotenv


# Cargar las variables del archivo .env
load_dotenv()


# Configuración de JWT
SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
