# TicketFlow Back

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Banco%20de%20Dados-4479A1?logo=mysql&logoColor=white)

Back-end do sistema **TicketFlow**, uma API desenvolvida em **Python** com **FastAPI** para gerenciar os chamados do sistema de help desk interno.

## Sobre o projeto

O **TicketFlow** foi idealizado para padronizar a abertura e o gerenciamento de tickets de TI, reduzindo perda de informações e melhorando a triagem dos chamados.

Este repositório contém o **back-end** da aplicação, responsável por:

- receber requisições do front-end;
- processar as regras de negócio;
- expor rotas REST;
- conectar com o banco de dados MySQL;
- gerenciar os dados dos tickets.

## Arquitetura

A aplicação segue o modelo **Cliente-Servidor**, onde este repositório representa a camada de servidor.

Estrutura base prevista:

- `main.py` para inicialização da aplicação;
- pasta de `routes` para organização das rotas;
- camada de conexão com banco de dados;
- scripts auxiliares do back-end;
- integração com MySQL.

## Tecnologias utilizadas

- **Python**
- **FastAPI**
- **MySQL**
- **Uvicorn**

## Funcionalidades previstas

- [x] Estrutura inicial do projeto
- [ ] Criação de rotas REST
- [ ] Cadastro de tickets
- [ ] Listagem de chamados
- [ ] Atualização de status
- [ ] Integração com banco MySQL
- [ ] Cálculo de SLA
- [ ] Roteamento automático por categoria
- [ ] Histórico de auditoria dos tickets

## Regras de negócio previstas

### Motor de SLA
O sistema deverá calcular o prazo máximo de atendimento e resolução dos chamados, permitindo identificar visualmente tickets dentro ou fora do prazo.

### Roteamento automático
Os tickets poderão ser direcionados automaticamente para o técnico ou setor responsável com base na categoria informada.

### Trilha de auditoria
Cada alteração realizada em um ticket poderá ser registrada, armazenando informações de quem alterou, o que foi alterado e quando ocorreu.

## Como executar o projeto

### Pré-requisitos

- Python 3 instalado
- pip
- MySQL

### Instalação

```bash
git clone https://github.com/joaosant05/TicketFlow-back
cd TicketFlow-back
pip install -r requirements.txt
uvicorn main:app --reload
```

Ao iniciar, a API executa `db/schema.sql` automaticamente. Se o banco `ticketflow`
ainda nao existir no MySQL local, ele sera criado com `CREATE DATABASE IF NOT EXISTS`
e as tabelas serao criadas com `CREATE TABLE IF NOT EXISTS`.

Configuracao padrao de banco:

```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=Joao1700556#
MYSQL_DATABASE=ticketflow
```

## Docker Compose demonstrativo

Os arquivos Docker foram mantidos para apresentacao da arquitetura do projeto.
Para desenvolvimento local, continue usando o fluxo normal com `uvicorn` e o
frontend com Vite.

Na raiz do projeto `TicketFlow`, suba todos os servicos:

```bash
docker compose up --build
```

Servicos expostos:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger da API: `http://localhost:8000/docs`
- MySQL do Docker: `localhost:3307`

O MySQL interno do Compose usa o host `mysql` na rede Docker. Por isso o backend
usa `MYSQL_HOST=mysql` quando roda em container.

As credenciais no `docker-compose.yml` sao demonstrativas e nao representam a
senha real do MySQL local.
