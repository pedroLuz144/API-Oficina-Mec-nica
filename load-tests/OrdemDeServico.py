import random
import string
import time
from typing import Optional

from locust import HttpUser, LoadTestShape, between, task


class OrdemDeServicoUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        self.password = "123456"
        self.email = self._build_unique_email()
        self.nome = "Rafael Kakizuko"

        self._register_user()
        token = self._login_user()
        if not token:
            raise RuntimeError("Falha ao autenticar no cenário de Ordem de Serviço.")

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        self.cpf = self._build_cpf()
        self.placa = self._build_plate()
        self.servico_descricao = f"OS Load {int(time.time() * 1000)}-{random.randint(1000, 9999)}"
        self.last_os_id = None

        self._create_cliente()
        self._create_veiculo()
        self.servico_id = self._create_and_get_servico_id()

        if self.servico_id is None:
            raise RuntimeError("Não foi possível obter idServico para o teste de OS.")

    @task(1)
    def post_criar_os(self) -> None:
        payload = {
            "placaVeiculo": self.placa,
            "idServico": self.servico_id,
        }

        with self.client.post(
            "/os",
            json=payload,
            headers=self.headers,
            name="POST /os",
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Esperado 201, retornou {response.status_code}: {response.text}")
                return

        with self.client.get(
            "/os/abertas",
            headers=self.headers,
            name="GET /os/abertas (captura id)",
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Falha ao capturar ID da OS: {response.status_code}: {response.text}")
                return

            try:
                data = response.json()
            except Exception:
                response.failure("Resposta de /os/abertas não é JSON válido.")
                return

            if not data:
                response.failure("/os/abertas retornou vazio após criação da OS.")
                return

            found = None
            for item in reversed(data):
                if item.get("veiculoPlaca") == self.placa and item.get("servicoDescricao") == self.servico_descricao:
                    found = item.get("id")
                    break

            if found is None:
                found = data[-1].get("id")

            self.last_os_id = found

    @task(1)
    def get_ler_os_criada(self) -> None:
        with self.client.get(
            "/os/abertas",
            headers=self.headers,
            name="GET /os/abertas (leitura)",
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Esperado 200, retornou {response.status_code}: {response.text}")
                return

            try:
                data = response.json()
            except Exception:
                response.failure("Resposta de leitura não é JSON válido.")
                return

            if self.last_os_id is None:
                if len(data) == 0:
                    response.failure("Nenhuma OS disponível para leitura.")
                return

            exists = any(item.get("id") == self.last_os_id for item in data)
            if not exists:
                response.failure(f"OS criada (id={self.last_os_id}) não encontrada na leitura.")

    def _register_user(self) -> None:
        payload = {
            "nome": self.nome,
            "email": self.email,
            "senha": self.password,
        }
        with self.client.post("/auth/register", json=payload, name="POST /auth/register", catch_response=True) as response:
            if response.status_code not in (201, 400):
                response.failure(f"Registro retornou status inesperado {response.status_code}: {response.text}")

    def _login_user(self) -> Optional[str]:
        payload = {
            "email": self.email,
            "senha": self.password,
        }
        with self.client.post("/auth/login", json=payload, name="POST /auth/login", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Login falhou: {response.status_code} - {response.text}")
                return None

            try:
                data = response.json()
            except Exception:
                response.failure("Resposta de /auth/login não é JSON válido.")
                return None

            token = data.get("token")
            if not token:
                response.failure("Token não encontrado na resposta de /auth/login.")
                return None
            return token

    def _create_cliente(self) -> None:
        payload = {
            "cpf": self.cpf,
            "nome": "Cliente Load OS",
            "email": f"cliente.{self.cpf}@load.test",
        }
        with self.client.post("/clientes", json=payload, headers=self.headers, name="POST /clientes", catch_response=True) as response:
            if response.status_code != 201:
                response.failure(f"Criação de cliente falhou: {response.status_code} - {response.text}")

    def _create_veiculo(self) -> None:
        payload = {
            "placa": self.placa,
            "marca": "Fiat",
            "modelo": "Uno",
            "cor": "Branco",
            "cpfCliente": self.cpf,
        }
        with self.client.post("/veiculos", json=payload, headers=self.headers, name="POST /veiculos", catch_response=True) as response:
            if response.status_code != 201:
                response.failure(f"Criação de veículo falhou: {response.status_code} - {response.text}")

    def _create_and_get_servico_id(self) -> Optional[int]:
        payload = {
            "descricao": self.servico_descricao,
            "valor": 120.0,
            "duracaoEstimadaEmSegundos": 3600,
        }

        with self.client.post("/servicos", json=payload, headers=self.headers, name="POST /servicos", catch_response=True) as response:
            if response.status_code != 201:
                response.failure(f"Criação de serviço falhou: {response.status_code} - {response.text}")
                return None

        with self.client.get("/servicos", headers=self.headers, name="GET /servicos", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Listagem de serviços falhou: {response.status_code} - {response.text}")
                return None

            try:
                servicos = response.json()
            except Exception:
                response.failure("Resposta de /servicos não é JSON válido.")
                return None

            for servico in servicos:
                if servico.get("descricao") == self.servico_descricao:
                    return servico.get("id")

            response.failure("Serviço criado não encontrado na listagem de /servicos.")
            return None

    @staticmethod
    def _build_unique_email() -> str:
        suffix = f"{int(time.time() * 1000)}{random.randint(1000, 9999)}"
        return f"rafael.kakizuko.{suffix}@load.test"

    @staticmethod
    def _build_cpf() -> str:
        return f"{random.randint(10**10, (10**11)-1)}"

    @staticmethod
    def _build_plate() -> str:
        letters = "".join(random.choice(string.ascii_uppercase) for _ in range(3))
        numbers = "".join(random.choice(string.digits) for _ in range(4))
        return f"{letters}{numbers}"


class CargaCrescenteOS(LoadTestShape):
    stages = [
        {"duration": 30, "users": 50, "spawn_rate": 10},
        {"duration": 75, "users": 180, "spawn_rate": 25},
        {"duration": 120, "users": 320, "spawn_rate": 40},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]

        return None
