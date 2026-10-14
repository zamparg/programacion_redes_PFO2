import os
import sqlite3
from contextlib import closing
from functools import wraps
from pathlib import Path

from flask import Flask, current_app, jsonify, render_template_string, request
from werkzeug.security import check_password_hash, generate_password_hash


def create_app(database_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    default_database = Path(__file__).with_name("tareas.db")
    app.config["DATABASE"] = str(
        database_path or os.environ.get("PFO2_DATABASE", default_database)
    )

    database = Path(app.config["DATABASE"])
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL
            )
            """
        )
        connection.commit()

    def require_basic_auth(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            credentials = request.authorization
            if (
                credentials is None
                or credentials.type.lower() != "basic"
                or not credentials.username
                or not credentials.password
            ):
                return (
                    jsonify({"error": "Autenticación requerida"}),
                    401,
                    {"WWW-Authenticate": 'Basic realm="PFO2"'},
                )

            with closing(sqlite3.connect(current_app.config["DATABASE"])) as connection:
                row = connection.execute(
                    "SELECT password_hash FROM usuarios WHERE usuario = ?",
                    (credentials.username,),
                ).fetchone()

            if row is None or not check_password_hash(row[0], credentials.password):
                return (
                    jsonify({"error": "Usuario o contraseña incorrectos"}),
                    401,
                    {"WWW-Authenticate": 'Basic realm="PFO2"'},
                )

            return view(credentials.username, *args, **kwargs)

        return wrapped

    def credentials_from_request():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, None
        username = data.get("usuario")
        password = data.get("contraseña")
        if not isinstance(username, str) or not isinstance(password, str):
            return None, None
        username = username.strip()
        if not username or not password or ":" in username:
            return None, None
        return username, password

    @app.post("/registro")
    def register():
        username, password = credentials_from_request()
        if username is None or password is None:
            return (
                jsonify(
                    {
                        "error": (
                            'Se requieren "usuario" y "contraseña" como texto no '
                            "vacío; el usuario no puede contener ':'"
                        )
                    }
                ),
                400,
            )

        password_hash = generate_password_hash(password)
        try:
            with closing(sqlite3.connect(current_app.config["DATABASE"])) as connection:
                connection.execute(
                    "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
                connection.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "El usuario ya existe"}), 409

        return jsonify({"mensaje": "Usuario registrado correctamente"}), 201

    @app.post("/login")
    def login():
        username, password = credentials_from_request()
        if username is None or password is None:
            return (
                jsonify(
                    {
                        "error": (
                            'Se requieren "usuario" y "contraseña" como texto no '
                            "vacío; el usuario no puede contener ':'"
                        )
                    }
                ),
                400,
            )

        with closing(sqlite3.connect(current_app.config["DATABASE"])) as connection:
            row = connection.execute(
                "SELECT password_hash FROM usuarios WHERE usuario = ?",
                (username,),
            ).fetchone()

        if row is None or not check_password_hash(row[0], password):
            return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

        return jsonify({"mensaje": "Inicio de sesión correcto"}), 200

    @app.get("/tareas")
    @require_basic_auth
    def tasks(username: str):
        return render_template_string(
            """
            <!doctype html>
            <html lang="es">
              <head>
                <meta charset="utf-8">
                <title>Gestión de tareas</title>
              </head>
              <body>
                <h1>¡Bienvenido/a, {{ usuario }}!</h1>
                <p>Has iniciado sesión correctamente en el sistema de tareas.</p>
              </body>
            </html>
            """,
            usuario=username,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
