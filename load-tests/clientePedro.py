from __future__ import annotations

import random
import string
from typing import Optional

from locust import HttpUser, between, task


PASSWORD_PADRAO = "senha123456"


class OficinaMecanicaUser(HttpUser):
    # Usuarios, spawn rate e host podem ser ajustados direto na interface do Locust.
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.token = ""
        self.email = ""
        self.cpf_cliente = ""
        self.placa_veiculo = ""
        self.id_servico: Optional[int] = None

        self._registrar_e_logar()
        self._garantir_cliente()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        expected_status: set[int],
        *,
        name: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        with self.client.request(
            method,
            path,
            name=name,
            json=json,
            params=params,
            headers=headers or self._headers(),
            catch_response=True,
        ) as response:
            if response.status_code in expected_status:
                response.success()
            else:
                response.failure(
                    f"Status {response.status_code}: {response.text[:200] or '<sem corpo>'}"
                )
            return response

    def _registrar_e_logar(self) -> None:
        sufixo = self._random_digits(6)
        self.email = f"locust_{sufixo}@teste.com"

        self._request(
            "POST",
            "/auth/register",
            {201},
            name="POST /auth/register",
            headers={"Content-Type": "application/json"},
            json={
                "nome": f"Usuario Locust {sufixo}",
                "email": self.email,
                "senha": PASSWORD_PADRAO,
            },
        )

        response = self._request(
            "POST",
            "/auth/login",
            {200},
            name="POST /auth/login",
            headers={"Content-Type": "application/json"},
            json={"email": self.email, "senha": PASSWORD_PADRAO},
        )

        if response.status_code == 200:
            try:
                self.token = response.json().get("token", "")
            except ValueError:
                self.token = ""

    def _garantir_cliente(self) -> None:
        if self.cpf_cliente:
            return
        self._criar_cliente_base()

    def _garantir_veiculo(self) -> None:
        if self.placa_veiculo:
            return
        self._criar_veiculo_base()

    def _garantir_servico(self) -> None:
        if self.id_servico is not None:
            return

        response = self._request("GET", "/servicos", {200}, name="GET /servicos")
        if response.status_code == 200:
            try:
                servicos = response.json()
            except ValueError:
                servicos = []

            if servicos:
                self.id_servico = servicos[0].get("id")
                return

        self._criar_servico_base()

        response = self._request("GET", "/servicos", {200}, name="GET /servicos")
        if response.status_code == 200:
            try:
                servicos = response.json()
            except ValueError:
                servicos = []

            if servicos:
                self.id_servico = servicos[-1].get("id")

    def _criar_cliente_base(self) -> None:
        cpf = self._random_digits(11)
        payload = {
            "cpf": cpf,
            "nome": f"Cliente {cpf[-4:]}",
            "email": f"cliente_{cpf}@teste.com",
        }

        response = self._request(
            "POST",
            "/clientes",
            {201},
            name="POST /clientes",
            json=payload,
        )
        if response.status_code == 201:
            self.cpf_cliente = cpf

    def _criar_veiculo_base(self) -> None:
        self._garantir_cliente()

        placa = self._random_plate()
        payload = {
            "placa": placa,
            "marca": "Fiat",
            "modelo": "Uno",
            "cor": "Branco",
            "cpfCliente": self.cpf_cliente,
        }

        response = self._request(
            "POST",
            "/veiculos",
            {201},
            name="POST /veiculos",
            json=payload,
        )
        if response.status_code == 201:
            self.placa_veiculo = placa

    def _criar_servico_base(self) -> None:
        descricao = f"Servico Locust {self._random_digits(5)}"
        self._request(
            "POST",
            "/servicos",
            {201},
            name="POST /servicos",
            json={
                "descricao": descricao,
                "valor": 120.0,
                "duracaoEstimadaEmSegundos": 3600,
            },
        )

    @task(1)
    def ver_perfil(self) -> None:
        self._request("GET", "/auth/profile", {200}, name="GET /auth/profile")

    @task(1)
    def criar_cliente(self) -> None:
        self._criar_cliente_base()

    @task(1)
    def atualizar_cliente(self) -> None:
        self._garantir_cliente()

        payload = {
            "cpf": self.cpf_cliente,
            "nome": f"Cliente Atualizado {self._random_digits(4)}",
            "email": f"cliente_atualizado_{self.cpf_cliente}@teste.com",
        }

        self._request(
            "PUT",
            f"/clientes/{self.cpf_cliente}",
            {200},
            name="PUT /clientes/{cpf}",
            json=payload,
        )

    @task(1)
    def listar_veiculos_do_cliente(self) -> None:
        self._garantir_cliente()
        self._request(
            "GET",
            f"/clientes/{self.cpf_cliente}/veiculos",
            {200},
            name="GET /clientes/{cpf}/veiculos",
        )

    @task(1)
    def criar_veiculo(self) -> None:
        self._criar_veiculo_base()

    @task(1)
    def listar_veiculos(self) -> None:
        self._request("GET", "/veiculos", {200}, name="GET /veiculos")

    @task(1)
    def buscar_veiculo(self) -> None:
        self._garantir_veiculo()
        self._request(
            "GET",
            f"/veiculos/{self.placa_veiculo}",
            {200},
            name="GET /veiculos/{placa}",
        )

    @task(1)
    def atualizar_veiculo(self) -> None:
        self._garantir_veiculo()

        payload = {
            "placa": self.placa_veiculo,
            "marca": "Toyota",
            "modelo": "Corolla",
            "cor": "Preto",
            "cpfCliente": self.cpf_cliente,
        }

        self._request(
            "PUT",
            f"/veiculos/{self.placa_veiculo}",
            {200},
            name="PUT /veiculos/{placa}",
            json=payload,
        )

    @task(1)
    def listar_servicos(self) -> None:
        self._request("GET", "/servicos", {200}, name="GET /servicos")

    @task(1)
    def criar_servico(self) -> None:
        self._criar_servico_base()
        self.id_servico = None

    @task(1)
    def abrir_os(self) -> None:
        self._garantir_veiculo()
        self._garantir_servico()

        if self.id_servico is None:
            return

        self._request(
            "POST",
            "/os",
            {201},
            name="POST /os",
            json={"placaVeiculo": self.placa_veiculo, "idServico": self.id_servico},
        )

    @task(1)
    def listar_os_abertas(self) -> None:
        self._request("GET", "/os/abertas", {200}, name="GET /os/abertas")

    @staticmethod
    def _random_digits(size: int) -> str:
        return "".join(random.choices(string.digits, k=size))

    @staticmethod
    def _random_plate() -> str:
        letras = "".join(random.choices(string.ascii_uppercase, k=3))
        numeros = "".join(random.choices(string.digits, k=4))
        return f"{letras}{numeros}"
