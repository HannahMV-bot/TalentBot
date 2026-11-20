from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Dirección de nuestra base de datos SQLite
DATABASE_URL = "sqlite:///./talentbot.db"

# Crear el motor de conexión
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Crear sesiones para interactuar con la base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para definir los modelos de las tablas
Base = declarative_base()


# Función para obtener una sesión de base de datos
def obtener_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
