# Testes de Carga - API Oficina Mecânica

Este diretório contém os testes de carga para a API de Oficina Mecânica utilizando Locust.

## Instalação

1. Instale o Python 3.8 ou superior
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Execução dos Testes

### Modo Web Interface (Recomendado)

Execute o Locust com interface web para ter controle total sobre os parâmetros:

```bash
cd load-tests
locust -f Veiculo.py --host=http://localhost:8080
```

Depois acesse: http://localhost:8089

Na interface web você pode configurar:
- **Number of users**: Número total de usuários simulados
- **Spawn rate**: Taxa de criação de usuários por segundo
- **Host**: URL base da API (padrão: http://localhost:8080)

### Modo Headless (Linha de Comando)

Para executar sem interface:

```bash
locust -f Veiculo.py --host=http://localhost:8080 --users 10 --spawn-rate 2 --run-time 5m --headless
```

Parâmetros:
- `--users 10`: Simula 10 usuários concorrentes
- `--spawn-rate 2`: Adiciona 2 usuários por segundo
- `--run-time 5m`: Executa por 5 minutos
- `--headless`: Executa sem interface web

## Estratégia de Teste Recomendada

### 1. Teste de Carga Inicial (Baseline)
- Usuários: 5-10
- Duração: 2-3 minutos
- Objetivo: Estabelecer métricas de baseline

### 2. Teste de Carga Gradual
- Início: 10 usuários
- Incremento: +10 a cada 2 minutos
- Máximo: 100 usuários
- Objetivo: Identificar ponto de degradação

### 3. Teste de Pico
- Usuários: 50-100
- Spawn rate: 10/segundo
- Duração: 5 minutos
- Objetivo: Simular picos de tráfego

### 4. Teste de Resistência (Stress)
- Usuários: Aumentar até falhas
- Objetivo: Encontrar limite máximo

## Métricas a Observar

- **Response Time**: Tempo de resposta (50%, 95%, 99%)
- **Requests/s**: Taxa de requisições por segundo
- **Failure Rate**: Taxa de falha das requisições
- **Users**: Número de usuários simultâneos

## Pré-requisitos

Certifique-se de que:
1. A aplicação Spring Boot está rodando em http://localhost:8080
2. O banco de dados está acessível
3. As tabelas estão criadas corretamente

## Estrutura dos Testes

### Veiculo.py
Testa as operações do modelo Veículo:
- **POST /veiculos**: Criação de novos veículos (peso 3)
- **GET /veiculos/{placa}**: Busca por placa (peso 1)
- **GET /veiculos**: Listagem de veículos (peso 1)

### Fluxo de Teste
1. Registro de usuário (setup)
2. Login e obtenção de token JWT (setup)
3. Criação de cliente (setup)
4. Loop de tarefas:
   - Criar veículos (75% das operações)
   - Buscar veículos (12.5% das operações)
   - Listar veículos (12.5% das operações)

## Resultados

Os resultados são exibidos em tempo real na interface web e incluem:

- Gráficos de performance
- Tabela de estatísticas por endpoint
- Distribuição de tempo de resposta
- Taxa de falhas
- Número de usuários ativos

## Exportar Resultados

Para gerar relatórios HTML:

```bash
locust -f Veiculo.py --host=http://localhost:8080 --users 50 --spawn-rate 5 --run-time 5m --headless --html report.html
```

## Troubleshooting

### Erro de Conexão
- Verifique se a API está rodando
- Confirme a URL e porta corretas

### Muitas Falhas 401 Unauthorized
- Verifique a configuração de segurança
- Confirme que o token JWT está sendo gerado

### Falhas 400 Bad Request
- Verifique os dados gerados aleatoriamente
- Confirme que o cliente está sendo criado antes dos veículos

## Observações

- Cada usuário virtual cria seu próprio cliente e veículos
- As placas são geradas aleatoriamente no formato AAA0000
- Os dados são persistidos no banco, limpe periodicamente
