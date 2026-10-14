import base64
import json
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "http://127.0.0.1:5000"


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)


def request_api(path: str, method: str, payload: dict | None = None, auth=None):
    headers = {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if auth is not None:
        username, password = auth
        token = base64.b64encode(
            f"{username}:{password}".encode("utf-8")
        ).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    request = Request(f"{API_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


def message_from(body: bytes) -> str:
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        return body.decode("utf-8", errors="replace")
    return data.get("mensaje") or data.get("error") or str(data)


def main():
    print("Sistema de Gestión de Tareas")
    print("1. Registrarse")
    print("2. Iniciar sesión")
    option = input("Selecciona una opción: ").strip()
    if option not in {"1", "2"}:
        print("Opción no válida.")
        return

    username = input("Usuario: ").strip()
    password = input("Contraseña: ")
    if not username or not password:
        print("El usuario y la contraseña no pueden estar vacíos.")
        return

    if option == "1":
        status, _, body = request_api(
            "/registro",
            "POST",
            {"usuario": username, "contraseña": password},
        )
        print(message_from(body))
        if status == 201:
            print("Ahora puedes iniciar sesión.")
        return

    status, _, body = request_api(
        "/login",
        "POST",
        {"usuario": username, "contraseña": password},
    )
    if status != 200:
        print(message_from(body))
        return

    print("Inicio de sesión correcto.")
    status, content_type, body = request_api(
        "/tareas", "GET", auth=(username, password)
    )
    if status != 200:
        print(message_from(body))
        return

    if "text/html" in content_type:
        page = PageText()
        page.feed(body.decode("utf-8"))
        print(" ".join(page.parts))


if __name__ == "__main__":
    try:
        main()
    except URLError as error:
        print(f"No se pudo conectar con la API ({API_URL}): {error.reason}")
