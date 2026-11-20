from backend.app.database.connection import Base, engine

# Importar los modelos para registrarlos en SQLAlchemy
from backend.app.database import models


def crear_tablas():
    Base.metadata.create_all(bind=engine)

    print("¡Base de datos TalentBot creada correctamente!")
    print("Tablas registradas:")

    for tabla in Base.metadata.sorted_tables:
        print(f"- {tabla.name}")


if __name__ == "__main__":
    crear_tablas()
