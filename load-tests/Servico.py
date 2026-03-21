import random
from locust import HttpUser, task, between

class ServicoTestUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        response = self.client.post("/auth/login", json={
            "email": "admin@oficina.com", 
            "senha": "senha123"  
        })
        
        if response.status_code == 200:
            
            self.token = response.json().get("token") 
        else:
            print(f"Falha ao fazer login: {response.status_code} - {response.text}")

    @task(2) 
    def ler_servicos(self):
      
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/servicos", headers=headers, name="GET /servicos")

    @task(1)
    def criar_servico(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
    
        id_aleatorio = random.randint(1000, 999999)
        
    
        payload = {
            "descricao": f"Alinhamento e Balanceamento {id_aleatorio}",
            "valor": 120.50,
            "duracaoEstimadaEmSegundos": 3600
        }
        
        self.client.post("/servicos", json=payload, headers=headers, name="POST /servicos")