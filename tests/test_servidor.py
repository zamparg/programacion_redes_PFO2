import base64
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from servidor import create_app
from werkzeug.security import check_password_hash


class ServidorTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(self.database)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.credentials = {"usuario": "ana", "contraseña": "clave-segura"}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registration_stores_a_password_hash(self):
        response = self.client.post("/registro", json=self.credentials)

        self.assertEqual(response.status_code, 201)
        with closing(sqlite3.connect(self.database)) as connection:
            stored_hash = connection.execute(
                "SELECT password_hash FROM usuarios WHERE usuario = ?",
                (self.credentials["usuario"],),
            ).fetchone()[0]
        self.assertNotEqual(stored_hash, self.credentials["contraseña"])
        self.assertTrue(
            check_password_hash(stored_hash, self.credentials["contraseña"])
        )

    def test_duplicate_registration_is_rejected(self):
        self.client.post("/registro", json=self.credentials)

        response = self.client.post("/registro", json=self.credentials)

        self.assertEqual(response.status_code, 409)

    def test_login_rejects_wrong_password(self):
        self.client.post("/registro", json=self.credentials)

        response = self.client.post(
            "/login",
            json={"usuario": "ana", "contraseña": "incorrecta"},
        )

        self.assertEqual(response.status_code, 401)

    def test_login_accepts_valid_credentials(self):
        self.client.post("/registro", json=self.credentials)

        response = self.client.post("/login", json=self.credentials)

        self.assertEqual(response.status_code, 200)

    def test_tasks_requires_valid_basic_auth(self):
        self.client.post("/registro", json=self.credentials)
        token = base64.b64encode(b"ana:clave-segura").decode("ascii")

        unauthorized = self.client.get("/tareas")
        authorized = self.client.get(
            "/tareas",
            headers={"Authorization": f"Basic {token}"},
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertIn("¡Bienvenido/a, ana!".encode(), authorized.data)

    def test_registration_validates_required_fields(self):
        response = self.client.post("/registro", json={"usuario": "ana"})

        self.assertEqual(response.status_code, 400)

    def test_registration_rejects_colons_in_username(self):
        response = self.client.post(
            "/registro",
            json={"usuario": "ana:admin", "contraseña": "clave-segura"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
