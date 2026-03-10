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
uvicorn app.main:app --reload