from locust import HttpUser, task, between, events
import random
import string
import json


class VeiculoLoadTest(HttpUser):

    wait_time = between(1, 3)

    token = None
    cpf_cliente = None
    placas_criadas = []

    def on_start(self):
        user_id = ''.join(random.choices(string.digits, k=6))
        email = f"loadtest_{user_id}@example.com"
        senha = "senha123456"

        register_payload = {
            "nome": f"Usuario LoadTest {user_id}",
            "email": email,
            "senha": senha
        }

        with self.client.post(
            "/auth/register",
            json=register_payload,
            catch_response=True,
            name="01_Auth_Register"
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                error_msg = f"Status {response.status_code}"
                try:
                    error_msg += f" - {response.text}"
                except:
                    pass
                response.failure(f"Falha no registro: {error_msg}")

        login_payload = {
            "email": email,
            "senha": senha
        }

        with self.client.post(
            "/auth/login",
            json=login_payload,
            catch_response=True,
            name="02_Auth_Login"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                if self.token:
                    response.success()
                else:
                    response.failure("Token não retornado no login")
            else:
                error_msg = f"Status {response.status_code}"
                try:
                    error_msg += f" - {response.text}"
                except:
                    pass
                response.failure(f"Falha no login: {error_msg}")

        self.cpf_cliente = ''.join(random.choices(string.digits, k=11))

        cliente_payload = {
            "cpf": self.cpf_cliente,
            "nome": f"Cliente LoadTest {user_id}",
            "email": f"cliente_{user_id}@example.com"
        }

        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.post(
            "/clientes",
            json=cliente_payload,
            headers=headers,
            catch_response=True,
            name="03_Create_Cliente"
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                error_msg = f"Status {response.status_code}"
                try:
                    error_msg += f" - {response.text}"
                except:
                    pass
                response.failure(f"Falha ao criar cliente: {error_msg}")

    def _gerar_placa(self):
        letras = ''.join(random.choices(string.ascii_uppercase, k=3))
        numeros = ''.join(random.choices(string.digits, k=4))
        return f"{letras}{numeros}"

    def _gerar_dados_veiculo(self):
        marcas = ["Toyota", "Honda", "Ford", "Chevrolet", "Volkswagen", "Fiat", "Hyundai"]
        modelos = ["Sedan", "SUV", "Hatchback", "Pickup", "Crossover", "Van"]
        cores = ["Preto", "Branco", "Prata", "Vermelho", "Azul", "Cinza", "Verde"]

        return {
            "placa": self._gerar_placa(),
            "marca": random.choice(marcas),
            "modelo": random.choice(modelos),
            "cor": random.choice(cores),
            "cpfCliente": self.cpf_cliente
        }

    @task(3)
    def criar_veiculo(self):
        if not self.token or not self.cpf_cliente:
            return

        veiculo_data = self._gerar_dados_veiculo()
        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.post(
            "/veiculos",
            json=veiculo_data,
            headers=headers,
            catch_response=True,
            name="POST /veiculos"
        ) as response:
            if response.status_code == 201:
                self.placas_criadas.append(veiculo_data["placa"])
                response.success()
            else:
                response.failure(f"Erro ao criar veículo: {response.status_code} - {response.text}")

    @task(1)
    def buscar_veiculo_por_placa(self):
        if not self.token or not self.placas_criadas:
            return

        placa = random.choice(self.placas_criadas)
        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.get(
            f"/veiculos/{placa}",
            headers=headers,
            catch_response=True,
            name="GET /veiculos/{placa}"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.failure(f"Veículo não encontrado: {placa}")
            else:
                response.failure(f"Erro ao buscar veículo: {response.status_code} - {response.text}")

    @task(1)
    def listar_veiculos(self):
        if not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.get(
            "/veiculos",
            headers=headers,
            catch_response=True,
            name="GET /veiculos"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Erro ao listar veículos: {response.status_code} - {response.text}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*60)
    print("TESTE DE CARGA - MODELO VEÍCULO")
    print("="*60)
    print("Iniciando simulação de carga...")
    print(f"Host: {environment.host}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*60)
    print("TESTE FINALIZADO")
    print("="*60)
    print("Verifique os resultados na interface web do Locust")
    print("="*60 + "\n")


if __name__ == "__main__":
    import os
    os.system("locust -f Veiculo.py --host=http://localhost:8080")
