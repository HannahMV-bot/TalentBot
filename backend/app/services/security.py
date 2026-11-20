from pwdlib import PasswordHash

# Configurar el algoritmo Argon2
password_hash = PasswordHash.recommended()


def encriptar_contrasena(contrasena: str) -> str:
    """
    Genera un hash seguro de la contraseña.
    """
    return password_hash.hash(contrasena)


def verificar_contrasena(
    contrasena: str,
    contrasena_hash: str
) -> bool:
    """
    Comprueba si una contraseña coincide con su hash.
    """
    return password_hash.verify(
        contrasena,
        contrasena_hash
    )
