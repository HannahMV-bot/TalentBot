from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.app.database.connection import Base


# ==========================================
# MODELO DE USUARIOS
# ==========================================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    contrasena = Column(String(255), nullable=False)

    hojas_vida = relationship(
        "HojaVida",
        back_populates="usuario"
    )

    entrevistas = relationship(
        "Entrevista",
        back_populates="usuario"
    )

    recomendaciones = relationship(
        "RecomendacionLaboral",
        back_populates="usuario"
    )


# ==========================================
# MODELO DE HOJAS DE VIDA
# ==========================================

class HojaVida(Base):
    __tablename__ = "hojas_vida"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(255), nullable=False)
    fecha_subida = Column(DateTime, default=datetime.utcnow)

    id_usuario = Column(
        Integer,
        ForeignKey("usuarios.id")
    )

    usuario = relationship(
        "Usuario",
        back_populates="hojas_vida"
    )

    analisis = relationship(
        "AnalisisCV",
        back_populates="hoja_vida"
    )


# ==========================================
# MODELO DE ANÁLISIS DE HOJAS DE VIDA
# ==========================================

class AnalisisCV(Base):
    __tablename__ = "analisis_cv"

    id = Column(Integer, primary_key=True, index=True)
    habilidades = Column(Text, nullable=True)
    perfil_profesional = Column(String(150), nullable=True)
    fecha_analisis = Column(DateTime, default=datetime.utcnow)

    id_hoja_vida = Column(
        Integer,
        ForeignKey("hojas_vida.id")
    )

    hoja_vida = relationship(
        "HojaVida",
        back_populates="analisis"
    )


# ==========================================
# MODELO DE OFERTAS LABORALES
# ==========================================

class OfertaLaboral(Base):
    __tablename__ = "ofertas_laborales"

    id = Column(Integer, primary_key=True, index=True)
    cargo = Column(String(150), nullable=False)
    empresa = Column(String(150), nullable=False)
    modalidad = Column(String(50), nullable=True)
    habilidades = Column(Text, nullable=True)

    respuestas = relationship(
        "Entrevista",
        back_populates="oferta"
    )

    recomendaciones = relationship(
        "RecomendacionLaboral",
        back_populates="oferta"
    )


# ==========================================
# MODELO DE ENTREVISTAS
# ==========================================

class Entrevista(Base):
    __tablename__ = "entrevistas"

    id = Column(Integer, primary_key=True, index=True)
    perfil = Column(String(150), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)

    id_usuario = Column(
        Integer,
        ForeignKey("usuarios.id")
    )

    id_oferta = Column(
        Integer,
        ForeignKey("ofertas_laborales.id"),
        nullable=True
    )

    usuario = relationship(
        "Usuario",
        back_populates="entrevistas"
    )

    oferta = relationship(
        "OfertaLaboral",
        back_populates="respuestas"
    )

    respuestas = relationship(
        "RespuestaEntrevista",
        back_populates="entrevista"
    )


# ==========================================
# MODELO DE RESPUESTAS DE ENTREVISTA
# ==========================================

class RespuestaEntrevista(Base):
    __tablename__ = "respuestas_entrevista"

    id = Column(Integer, primary_key=True, index=True)
    pregunta = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    puntuacion = Column(Float, nullable=True)
    retroalimentacion = Column(Text, nullable=True)

    id_entrevista = Column(
        Integer,
        ForeignKey("entrevistas.id")
    )

    entrevista = relationship(
        "Entrevista",
        back_populates="respuestas"
    )


# ==========================================
# MODELO DE RECOMENDACIONES LABORALES
# ==========================================

class RecomendacionLaboral(Base):
    __tablename__ = "recomendaciones_laborales"

    id = Column(Integer, primary_key=True, index=True)

    porcentaje_compatibilidad = Column(Float, nullable=False)
    habilidades_coincidentes = Column(Text, nullable=True)
    habilidades_faltantes = Column(Text, nullable=True)

    fecha_recomendacion = Column(
        DateTime,
        default=datetime.utcnow
    )

    id_usuario = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False
    )

    id_oferta = Column(
        Integer,
        ForeignKey("ofertas_laborales.id"),
        nullable=False
    )

    usuario = relationship(
        "Usuario",
        back_populates="recomendaciones"
    )

    oferta = relationship(
        "OfertaLaboral",
        back_populates="recomendaciones"
    )
