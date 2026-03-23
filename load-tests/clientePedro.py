from __future__ import annotations

import random
import string
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from locust import HttpUser, LoadTestShape, between, events, task


TARGET_USERS = 1000
REQUESTS_PER_CYCLE = 20
SPAWN_RATE = 100

CLIENTE_STAGES = [
    {"duration": 120, "users": 250, "spawn_rate": SPAWN_RATE, "label": "carga_250"},
    {"duration": 240, "users": 500, "spawn_rate": SPAWN_RATE, "label": "carga_500"},
    {"duration": 360, "users": 750, "spawn_rate": SPAWN_RATE, "label": "carga_750"},
    {"duration": 480, "users": TARGET_USERS, "spawn_rate": SPAWN_RATE, "label": "carga_1000"},
]

MEASURED_ROUTES = {
    "POST /clientes",
    "PUT /clientes/{cpf}",
    "DELETE /clientes/{cpf}",
    "GET /clientes/{cpf}/veiculos",
}

REPORT_PATH = Path(__file__).with_name("relatorio_clientes.md")


@dataclass
class ClienteRegistro:
    cpf: str
    nome: str
    email: str
    has_vehicle: bool = False


@dataclass
class BucketMetricas:
    request_count: int = 0
    failure_count: int = 0
    total_response_time: float = 0.0
    max_response_time: float = 0.0
    timeout_count: int = 0
    status_4xx: int = 0
    status_5xx: int = 0
    response_times: List[float] = field(default_factory=list)

    def add_sample(
        self,
        response_time: float,
        response: Optional[object],
        exception: Optional[BaseException],
    ) -> None:
        elapsed_ms = float(response_time or 0.0)
        self.request_count += 1
        self.total_response_time += elapsed_ms
        self.max_response_time = max(self.max_response_time, elapsed_ms)
        self.response_times.append(elapsed_ms)

        status_code = getattr(response, "status_code", None)
        if exception is not None:
            self.failure_count += 1
            if "timeout" in str(exception).lower():
                self.timeout_count += 1
            return

        if status_code is None:
            return

        if status_code >= 400:
            self.failure_count += 1
            if 400 <= status_code < 500:
                self.status_4xx += 1
            if status_code >= 500:
                self.status_5xx += 1

    @property
    def avg_response_time(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_response_time / self.request_count

    @property
    def failure_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.failure_count / self.request_count

    def percentile(self, percent: float) -> float:
        if not self.response_times:
            return 0.0

        ordered = sorted(self.response_times)
        rank = int(round((len(ordered) - 1) * (percent / 100.0)))
        return ordered[max(0, min(rank, len(ordered) - 1))]


class AnaliseCargaClientes:
    def __init__(self, stages: List[Dict[str, object]]) -> None:
        self.stages = stages
        self.lock = threading.Lock()
        self.started_at: Optional[float] = None
        self.host: str = ""
        self.stage_buckets = [BucketMetricas() for _ in stages]
        self.route_buckets = {route: BucketMetricas() for route in MEASURED_ROUTES}
        self.total_bucket = BucketMetricas()

    def start(self, host: Optional[str]) -> None:
        with self.lock:
            self.started_at = time.monotonic()
            self.host = host or ""
            self.stage_buckets = [BucketMetricas() for _ in self.stages]
            self.route_buckets = {route: BucketMetricas() for route in MEASURED_ROUTES}
            self.total_bucket = BucketMetricas()

    def record(
        self,
        route_name: str,
        response_time: float,
        response: Optional[object],
        exception: Optional[BaseException],
    ) -> None:
        if route_name not in MEASURED_ROUTES or self.started_at is None:
            return

        elapsed = max(0.0, time.monotonic() - self.started_at)
        stage_index = self._stage_index_for_elapsed(elapsed)

        with self.lock:
            self.stage_buckets[stage_index].add_sample(response_time, response, exception)
            self.route_buckets[route_name].add_sample(response_time, response, exception)
            self.total_bucket.add_sample(response_time, response, exception)

    def build_report(self) -> str:
        total = self.total_bucket
        if total.request_count == 0:
            return self._empty_report()

        stage_lines = self._build_stage_lines()
        bottleneck_summary = self._detect_bottleneck()
        route_name, route_bucket = self._heaviest_route()

        report_lines = [
            "# Relatorio de Carga - Clientes",
            "",
            "## Modelo da aplicacao testado",
            "Modulo de clientes da API Oficina Mecanica em Spring Boot com autenticacao JWT e persistencia JPA/Hibernate.",
            "",
            "## Descricao breve do teste implementado",
            f"O script `clientePedro.py` aplica carga crescente ate {TARGET_USERS} usuarios somente nas rotas de clientes.",
            "As operacoes medidas sao `POST /clientes`, `PUT /clientes/{cpf}`, `DELETE /clientes/{cpf}` e `GET /clientes/{cpf}/veiculos`.",
            f"Cada ciclo de usuario executa exatamente {REQUESTS_PER_CYCLE} requisicoes nas rotas de clientes.",
            "Autenticacao e criacao de veiculos de apoio sao feitas fora das metricas para nao contaminar a analise das rotas de cliente.",
            "",
            "## Resumo do comportamento observado durante o aumento de carga",
            (
                f"Foram registradas {total.request_count} requisicoes medidas com latencia media global de "
                f"{total.avg_response_time:.2f} ms, p95 de {total.percentile(95):.2f} ms e taxa de falha de "
                f"{total.failure_rate * 100:.2f}%."
            ),
        ]
        report_lines.extend(stage_lines)
        report_lines.extend(
            [
                "",
                "## Momento em que a aplicacao comecou a apresentar gargalos",
                bottleneck_summary,
                "",
                "## Sintomas observados (latencia, falhas, timeouts, etc.)",
                f"- Latencia media global: {total.avg_response_time:.2f} ms",
                f"- p95 global: {total.percentile(95):.2f} ms",
                f"- Pico de latencia: {total.max_response_time:.2f} ms",
                f"- Taxa de falha global: {total.failure_rate * 100:.2f}%",
                f"- Falhas 4xx: {total.status_4xx}",
                f"- Falhas 5xx: {total.status_5xx}",
                f"- Timeouts identificados: {total.timeout_count}",
                "",
                "## Operacao com maior impacto de desempenho",
                (
                    f"A operacao com maior impacto foi `{route_name}`, com latencia media de "
                    f"{route_bucket.avg_response_time:.2f} ms, p95 de {route_bucket.percentile(95):.2f} ms "
                    f"e taxa de falha de {route_bucket.failure_rate * 100:.2f}%."
                ),
                "",
                "## Interpretacao sobre o possivel motivo do gargalo",
                self._build_interpretation(route_name, route_bucket, bottleneck_summary),
                "",
                "## Conclusao sobre o limite observado da aplicacao",
                self._build_conclusion(bottleneck_summary),
                "",
                "## Observacoes por rota",
            ]
        )
        report_lines.extend(self._build_route_lines())
        report_lines.append("")
        return "\n".join(report_lines)

    def write_report(self) -> Path:
        report_content = self.build_report()
        REPORT_PATH.write_text(report_content, encoding="utf-8")
        return REPORT_PATH

    def _empty_report(self) -> str:
        return "\n".join(
            [
                "# Relatorio de Carga - Clientes",
                "",
                "Nenhuma requisicao das rotas de cliente foi registrada durante a execucao.",
                "Verifique se o teste foi iniciado com o arquivo correto e com host configurado.",
                "",
                "Rotas esperadas:",
                "- POST /clientes",
                "- PUT /clientes/{cpf}",
                "- DELETE /clientes/{cpf}",
                "- GET /clientes/{cpf}/veiculos",
                "",
            ]
        )

    def _build_stage_lines(self) -> List[str]:
        lines = []
        for index, stage in enumerate(self.stages):
            bucket = self.stage_buckets[index]
            start_second = 0 if index == 0 else int(self.stages[index - 1]["duration"])
            end_second = int(stage["duration"])
            lines.append(
                (
                    f"- {start_second}s a {end_second}s | {stage['users']} usuarios | "
                    f"reqs={bucket.request_count} | falhas={bucket.failure_count} "
                    f"({bucket.failure_rate * 100:.2f}%) | media={bucket.avg_response_time:.2f} ms | "
                    f"p95={bucket.percentile(95):.2f} ms | max={bucket.max_response_time:.2f} ms"
                )
            )
        return lines

    def _build_route_lines(self) -> List[str]:
        lines = []
        for route_name in sorted(MEASURED_ROUTES):
            bucket = self.route_buckets[route_name]
            lines.append(
                (
                    f"- {route_name}: reqs={bucket.request_count}, media={bucket.avg_response_time:.2f} ms, "
                    f"p95={bucket.percentile(95):.2f} ms, falhas={bucket.failure_count} "
                    f"({bucket.failure_rate * 100:.2f}%), timeouts={bucket.timeout_count}"
                )
            )
        return lines

    def _detect_bottleneck(self) -> str:
        previous_bucket: Optional[BucketMetricas] = None

        for index, stage in enumerate(self.stages):
            bucket = self.stage_buckets[index]
            if bucket.request_count == 0:
                continue

            start_second = 0 if index == 0 else int(self.stages[index - 1]["duration"])
            end_second = int(stage["duration"])

            if bucket.timeout_count > 0 or bucket.status_5xx > 0:
                return (
                    f"O primeiro sinal forte apareceu entre {start_second}s e {end_second}s "
                    f"(cerca de {stage['users']} usuarios), quando surgiram timeouts/5xx e o p95 chegou a "
                    f"{bucket.percentile(95):.2f} ms."
                )

            if bucket.failure_rate >= 0.03:
                return (
                    f"O gargalo ficou evidente entre {start_second}s e {end_second}s "
                    f"(cerca de {stage['users']} usuarios), quando a taxa de falha subiu para "
                    f"{bucket.failure_rate * 100:.2f}%."
                )

            if previous_bucket is not None and previous_bucket.request_count > 0:
                avg_growth = self._growth_ratio(previous_bucket.avg_response_time, bucket.avg_response_time)
                p95_growth = self._growth_ratio(previous_bucket.percentile(95), bucket.percentile(95))
                if avg_growth >= 1.80 or p95_growth >= 1.80:
                    return (
                        f"O gargalo comecou a aparecer entre {start_second}s e {end_second}s "
                        f"(cerca de {stage['users']} usuarios), quando a latencia cresceu de forma acentuada "
                        f"em relacao ao estagio anterior."
                    )

            previous_bucket = bucket

        max_users = int(self.stages[-1]["users"])
        return (
            f"Nao houve sinal claro de gargalo dentro da carga configurada. A aplicacao se manteve observavel "
            f"ate o teto de {max_users} usuarios simultaneos deste roteiro."
        )

    def _build_interpretation(
        self,
        route_name: str,
        route_bucket: BucketMetricas,
        bottleneck_summary: str,
    ) -> str:
        route_causes = {
            "POST /clientes": (
                "A rota de cadastro depende de insercao no banco a cada requisicao. Em carga alta, o custo de "
                "persistencia e validacao tende a crescer junto com a pressao sobre o banco."
            ),
            "PUT /clientes/{cpf}": (
                "Ha um ponto de atencao no backend: `ClienteServiceImp.atualizarInformacoes` instancia um novo "
                "`ClienteEntity`, preenche apenas nome e email e faz `save` sem reaplicar o CPF. Isso pode gerar "
                "falha de persistencia ou comportamento inconsistente sob carga."
            ),
            "DELETE /clientes/{cpf}": (
                "A remocao pode esbarrar em integridade referencial. Se a base estiver acumulando clientes com "
                "veiculos ou OS relacionadas, o delete tende a falhar e aumentar a pressao de erro."
            ),
            "GET /clientes/{cpf}/veiculos": (
                "A listagem depende de buscar o cliente e carregar sua colecao de veiculos. Em JPA/Hibernate, isso "
                "pode ampliar o custo de banco e de serializacao conforme a quantidade de registros associados."
            ),
        }

        if "Nao houve sinal claro" in bottleneck_summary:
            return (
                "Mesmo sem um gargalo explicito no intervalo testado, a rota mais pesada merece atencao porque ela "
                f"ja concentrou a pior combinacao de latencia/falha. Possivel foco: {route_causes[route_name]}"
            )

        return (
            f"A principal suspeita para o comportamento observado recai sobre `{route_name}`. "
            f"Ela apresentou media de {route_bucket.avg_response_time:.2f} ms e p95 de "
            f"{route_bucket.percentile(95):.2f} ms. Possivel explicacao: {route_causes[route_name]}"
        )

    def _build_conclusion(self, bottleneck_summary: str) -> str:
        if "Nao houve sinal claro" in bottleneck_summary:
            max_users = int(self.stages[-1]["users"])
            return (
                f"Nesta execucao, o modulo de clientes permaneceu estavel ate {max_users} usuarios concorrentes, "
                "sem indiciar um limite operacional nitido dentro da rampa configurada."
            )

        for index, stage in enumerate(self.stages):
            bucket = self.stage_buckets[index]
            if bucket.request_count == 0:
                continue

            start_second = 0 if index == 0 else int(self.stages[index - 1]["duration"])
            end_second = int(stage["duration"])

            if f"{start_second}s e {end_second}s" in bottleneck_summary:
                previous_users = int(self.stages[index - 1]["users"]) if index > 0 else int(stage["users"])
                return (
                    f"O limite observado da aplicacao ficou proximo da transicao para {int(stage['users'])} usuarios "
                    f"concorrentes. Como o comportamento piorou nesse intervalo, o ponto mais seguro parece estar "
                    f"na faixa do estagio anterior, em torno de {previous_users} usuarios."
                )

        return (
            "A execucao indicou degradacao sob carga crescente, mas sem uma fronteira unica totalmente precisa. "
            "Use o estagio imediatamente anterior ao primeiro sinal de falha como limite operacional conservador."
        )

    def _heaviest_route(self) -> Tuple[str, BucketMetricas]:
        populated = [
            (route_name, bucket)
            for route_name, bucket in self.route_buckets.items()
            if bucket.request_count > 0
        ]
        if not populated:
            route_name = "POST /clientes"
            return route_name, self.route_buckets[route_name]

        return max(
            populated,
            key=lambda item: (
                item[1].failure_rate,
                item[1].avg_response_time,
                item[1].percentile(95),
                item[1].request_count,
            ),
        )

    def _stage_index_for_elapsed(self, elapsed_seconds: float) -> int:
        for index, stage in enumerate(self.stages):
            if elapsed_seconds < float(stage["duration"]):
                return index
        return len(self.stages) - 1

    @staticmethod
    def _growth_ratio(previous_value: float, current_value: float) -> float:
        if previous_value <= 0:
            return 1.0 if current_value <= 0 else current_value
        return current_value / previous_value


ANALISADOR = AnaliseCargaClientes(CLIENTE_STAGES)


class ClienteLoadTest(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        self.base_url = self.host or getattr(self.environment, "host", None)
        if not self.base_url:
            raise RuntimeError("Informe o host da API com --host=http://localhost:8080")

        self.external_session = requests.Session()
        self.external_session.headers.update({"Content-Type": "application/json"})
        self.headers: Dict[str, str] = {}
        self.clientes: Dict[str, ClienteRegistro] = {}
        self.clean_cpfs: List[str] = []
        self.vehicle_cpfs: List[str] = []
        self.suffix = self._build_unique_suffix()
        self.operation_plan = (
            ["create"] * 8
            + ["list_vehicles"] * 6
            + ["update"] * 4
            + ["delete"] * 2
        )

        self._register_and_login()
        self._seed_initial_data()

    @task
    def executar_ciclo_de_clientes(self) -> None:
        cycle_plan = list(self.operation_plan)
        random.shuffle(cycle_plan)

        for operation_name in cycle_plan:
            if operation_name == "create":
                self._executar_criacao_cliente()
            elif operation_name == "list_vehicles":
                self._executar_listagem_veiculos()
            elif operation_name == "update":
                self._executar_atualizacao_cliente()
            else:
                self._executar_remocao_cliente()

    def _executar_criacao_cliente(self) -> None:
        cliente = self._build_cliente(prefix="Cliente Post")

        with self.client.post(
            "/clientes",
            json=self._cliente_payload(cliente),
            headers=self.headers,
            name="POST /clientes",
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code == 201:
                self._track_cliente(cliente)
                response.success()
                return

            response.failure(
                f"POST /clientes retornou {response.status_code}: {self._safe_response_text(response)}"
            )

    def _executar_listagem_veiculos(self) -> None:
        cliente = self._pick_vehicle_cliente()
        if cliente is None:
            return

        with self.client.get(
            f"/clientes/{cliente.cpf}/veiculos",
            headers=self.headers,
            name="GET /clientes/{cpf}/veiculos",
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"GET /clientes/{cliente.cpf}/veiculos retornou {response.status_code}: "
                    f"{self._safe_response_text(response)}"
                )
                return

            try:
                payload = response.json()
            except Exception as exc:
                response.failure(f"Resposta invalida de veiculos: {exc}")
                return

            if not isinstance(payload, list):
                response.failure("GET /clientes/{cpf}/veiculos nao retornou uma lista.")
                return

            response.success()

    def _executar_atualizacao_cliente(self) -> None:
        cliente = self._pick_any_cliente()
        if cliente is None:
            return

        updated_cliente = ClienteRegistro(
            cpf=cliente.cpf,
            nome=f"{cliente.nome} Atualizado",
            email=f"upd.{cliente.cpf}.{random.randint(1000, 9999)}@load.test",
            has_vehicle=cliente.has_vehicle,
        )

        with self.client.put(
            f"/clientes/{cliente.cpf}",
            json=self._cliente_payload(updated_cliente),
            headers=self.headers,
            name="PUT /clientes/{cpf}",
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code == 200:
                self.clientes[cliente.cpf] = updated_cliente
                response.success()
                return

            response.failure(
                f"PUT /clientes/{cliente.cpf} retornou {response.status_code}: "
                f"{self._safe_response_text(response)}"
            )

    def _executar_remocao_cliente(self) -> None:
        cliente = self._pick_clean_cliente()
        if cliente is None:
            return

        with self.client.delete(
            f"/clientes/{cliente.cpf}",
            headers=self.headers,
            name="DELETE /clientes/{cpf}",
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code == 204:
                self._forget_cliente(cliente.cpf)
                self._ensure_clean_pool()
                response.success()
                return

            response.failure(
                f"DELETE /clientes/{cliente.cpf} retornou {response.status_code}: "
                f"{self._safe_response_text(response)}"
            )

    def _register_and_login(self) -> None:
        email = f"locust.cliente.{self.suffix}@load.test"
        password = "senha123456"

        register_payload = {
            "nome": f"Usuario Locust {self.suffix}",
            "email": email,
            "senha": password,
        }
        register_response = self.external_session.post(
            self._absolute_url("/auth/register"),
            json=register_payload,
            timeout=10,
        )
        if register_response.status_code != 201:
            raise RuntimeError(
                f"Falha no setup /auth/register: {register_response.status_code} - "
                f"{self._safe_requests_text(register_response)}"
            )

        login_response = self.external_session.post(
            self._absolute_url("/auth/login"),
            json={"email": email, "senha": password},
            timeout=10,
        )
        if login_response.status_code != 200:
            raise RuntimeError(
                f"Falha no setup /auth/login: {login_response.status_code} - "
                f"{self._safe_requests_text(login_response)}"
            )

        token = login_response.json().get("token")
        if not token:
            raise RuntimeError("O login nao retornou token JWT para o teste de clientes.")

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.external_session.headers.update(self.headers)

    def _seed_initial_data(self) -> None:
        seeded_clean = self._create_support_cliente(with_vehicle=False)
        self._track_cliente(seeded_clean)

        seeded_vehicle = self._create_support_cliente(with_vehicle=True)
        self._track_cliente(seeded_vehicle)

        extra_clean = self._create_support_cliente(with_vehicle=False)
        self._track_cliente(extra_clean)

    def _create_support_cliente(self, with_vehicle: bool) -> ClienteRegistro:
        cliente = self._build_cliente(prefix="Cliente Seed", has_vehicle=with_vehicle)
        response = self.external_session.post(
            self._absolute_url("/clientes"),
            json=self._cliente_payload(cliente),
            timeout=10,
        )
        if response.status_code != 201:
            raise RuntimeError(
                f"Falha ao criar cliente de apoio: {response.status_code} - "
                f"{self._safe_requests_text(response)}"
            )

        if with_vehicle:
            for _ in range(2):
                vehicle_response = self.external_session.post(
                    self._absolute_url("/veiculos"),
                    json=self._veiculo_payload(cliente.cpf),
                    timeout=10,
                )
                if vehicle_response.status_code != 201:
                    raise RuntimeError(
                        f"Falha ao criar veiculo de apoio: {vehicle_response.status_code} - "
                        f"{self._safe_requests_text(vehicle_response)}"
                    )

        return cliente

    def _ensure_clean_pool(self) -> None:
        while len(self.clean_cpfs) < 2:
            cliente = self._create_support_cliente(with_vehicle=False)
            self._track_cliente(cliente)

    def _track_cliente(self, cliente: ClienteRegistro) -> None:
        self.clientes[cliente.cpf] = cliente
        target_list = self.vehicle_cpfs if cliente.has_vehicle else self.clean_cpfs
        if cliente.cpf not in target_list:
            target_list.append(cliente.cpf)

    def _forget_cliente(self, cpf: str) -> None:
        self.clientes.pop(cpf, None)
        if cpf in self.clean_cpfs:
            self.clean_cpfs.remove(cpf)
        if cpf in self.vehicle_cpfs:
            self.vehicle_cpfs.remove(cpf)

    def _pick_any_cliente(self) -> Optional[ClienteRegistro]:
        if not self.clientes:
            self._ensure_clean_pool()
        if not self.clientes:
            return None
        return self.clientes[random.choice(list(self.clientes.keys()))]

    def _pick_clean_cliente(self) -> Optional[ClienteRegistro]:
        if not self.clean_cpfs:
            self._ensure_clean_pool()
        if not self.clean_cpfs:
            return None
        return self.clientes[random.choice(self.clean_cpfs)]

    def _pick_vehicle_cliente(self) -> Optional[ClienteRegistro]:
        if not self.vehicle_cpfs:
            cliente = self._create_support_cliente(with_vehicle=True)
            self._track_cliente(cliente)
        if not self.vehicle_cpfs:
            return None
        return self.clientes[random.choice(self.vehicle_cpfs)]

    def _build_cliente(self, prefix: str, has_vehicle: bool = False) -> ClienteRegistro:
        cpf = self._build_cpf()
        nome = f"{prefix} {self.suffix} {random.randint(100, 999)}"
        email = f"cliente.{cpf}.{random.randint(1000, 9999)}@load.test"
        return ClienteRegistro(cpf=cpf, nome=nome, email=email, has_vehicle=has_vehicle)

    def _cliente_payload(self, cliente: ClienteRegistro) -> Dict[str, str]:
        return {"cpf": cliente.cpf, "nome": cliente.nome, "email": cliente.email}

    def _veiculo_payload(self, cpf_cliente: str) -> Dict[str, str]:
        return {
            "placa": self._build_plate(),
            "marca": random.choice(["Fiat", "Ford", "Toyota", "Volkswagen"]),
            "modelo": random.choice(["Uno", "Ka", "Corolla", "Gol"]),
            "cor": random.choice(["Branco", "Preto", "Prata", "Azul"]),
            "cpfCliente": cpf_cliente,
        }

    def _absolute_url(self, path: str) -> str:
        return urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    @staticmethod
    def _build_unique_suffix() -> str:
        base = int(time.time() * 1000)
        return f"{base}{random.randint(1000, 9999)}"

    @staticmethod
    def _build_cpf() -> str:
        return "".join(random.choice(string.digits) for _ in range(11))

    @staticmethod
    def _build_plate() -> str:
        letters = "".join(random.choice(string.ascii_uppercase) for _ in range(3))
        numbers = "".join(random.choice(string.digits) for _ in range(4))
        return f"{letters}{numbers}"

    @staticmethod
    def _safe_response_text(response: object) -> str:
        text = getattr(response, "text", "")
        return text[:300] if text else "<sem corpo>"

    @staticmethod
    def _safe_requests_text(response: requests.Response) -> str:
        return response.text[:300] if response.text else "<sem corpo>"


class CargaCrescenteClientes(LoadTestShape):
    stages = CLIENTE_STAGES

    def tick(self) -> Optional[Tuple[int, int]]:
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < float(stage["duration"]):
                return int(stage["users"]), int(stage["spawn_rate"])

        return None


@events.test_start.add_listener
def on_test_start(environment, **kwargs) -> None:
    ANALISADOR.start(getattr(environment, "host", None))
    print("\n" + "=" * 72)
    print("TESTE DE CARGA - ROTAS DE CLIENTES")
    print("=" * 72)
    print("Rotas medidas: POST /clientes, PUT /clientes/{cpf}, DELETE /clientes/{cpf}, GET /clientes/{cpf}/veiculos")
    print(f"Carga configurada: rampa ate {TARGET_USERS} usuarios simultaneos e {REQUESTS_PER_CYCLE} requisicoes por ciclo")
    print(f"Host: {getattr(environment, 'host', '<nao informado>')}")
    print("Relatorio final: load-tests/relatorio_clientes.md")
    print("=" * 72 + "\n")


@events.request.add_listener
def on_request(
    request_type,
    name,
    response_time,
    response_length,
    response=None,
    context=None,
    exception=None,
    start_time=None,
    url=None,
    **kwargs,
) -> None:
    ANALISADOR.record(name, response_time, response, exception)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs) -> None:
    report_path = ANALISADOR.write_report()
    print("\n" + "=" * 72)
    print("TESTE FINALIZADO")
    print("=" * 72)
    print(f"Relatorio salvo em: {report_path}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    import os

    os.system("locust -f clientePedro.py --host=http://localhost:8080")
