import random
import string
import time

from locust import HttpUser, between, task


class TesteDeCargaCliente(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.password = "123456"
        self.email = self._build_unique_email()
        self.nome = "Carga Cliente"
        self.token = ""

        self._register_user()

        with self.client.post(
            "/auth/login",
            json={"email": self.email, "senha": self.password},
            name="POST /auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Falha ao logar. Status: {response.status_code}. Resposta: {response.text}")
                return

            try:
                self.token = response.json().get("token", "")
            except Exception:
                response.failure("Resposta de login nao eh um JSON valido.")
                return

            if not self.token:
                response.failure("Login retornou 200, mas sem token na resposta.")
                return

            response.success()

    @task
    def fluxo_criar_e_ler_cliente(self):
        if not self.token:
            return

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        cpf_gerado = "".join(random.choices(string.digits, k=11))
        sufixo_email = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

        payload_cliente = {
            "cpf": cpf_gerado,
            "nome": f"Cliente Carga {sufixo_email}",
            "email": f"carga_{sufixo_email}@teste.com"
        }

        with self.client.post(
            "/clientes",
            json=payload_cliente,
            headers=headers,
            name="POST /clientes",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Erro no POST. Status: {response.status_code}. Resposta: {response.text}")
                return

        with self.client.get(
            f"/clientes/{cpf_gerado}/veiculos",
            headers=headers,
            name="GET /clientes/[cpf]/veiculos",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Erro no GET. Status: {response.status_code}. Resposta: {response.text}")

    def _register_user(self):
        payload = {
            "nome": self.nome,
            "email": self.email,
            "senha": self.password,
        }

        with self.client.post(
            "/auth/register",
            json=payload,
            name="POST /auth/register",
            catch_response=True,
        ) as response:
            if response.status_code not in (201, 400):
                response.failure(f"Falha ao registrar usuario. Status: {response.status_code}. Resposta: {response.text}")

    @staticmethod
    def _build_unique_email():
        sufixo = f"{int(time.time() * 1000)}{random.randint(1000, 9999)}"
        return f"cliente.carga.{sufixo}@load.test"
