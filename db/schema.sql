CREATE DATABASE IF NOT EXISTS ticketflow
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ticketflow;

CREATE TABLE IF NOT EXISTS departamentos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL UNIQUE,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  auth0_id VARCHAR(180) NULL UNIQUE,
  nome VARCHAR(160) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  papel ENUM('solicitante', 'tecnico', 'admin') NOT NULL DEFAULT 'solicitante',
  departamento_id INT NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_usuarios_departamento
    FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categorias (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL UNIQUE,
  prioridade ENUM('Alta', 'Media', 'Baixa') NOT NULL DEFAULT 'Baixa',
  sla_horas INT NOT NULL DEFAULT 24,
  departamento_padrao_id INT NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_categorias_departamento_padrao
    FOREIGN KEY (departamento_padrao_id) REFERENCES departamentos(id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tickets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  protocolo INT NOT NULL,
  ano YEAR NOT NULL,
  titulo VARCHAR(180) NOT NULL,
  descricao TEXT NOT NULL,
  status VARCHAR(60) NOT NULL DEFAULT 'Criado',
  categoria_id INT NOT NULL,
  solicitante_id INT NULL,
  responsavel_id INT NULL,
  departamento_id INT NULL,
  sla_tipo VARCHAR(120) NOT NULL DEFAULT 'TA - Tempo de Atualizacao',
  sla_deadline DATETIME NULL,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  fechado_em DATETIME NULL,
  UNIQUE KEY uk_tickets_protocolo_ano (protocolo, ano),
  INDEX idx_tickets_status (status),
  INDEX idx_tickets_responsavel (responsavel_id),
  INDEX idx_tickets_departamento (departamento_id),
  INDEX idx_tickets_categoria (categoria_id),
  CONSTRAINT fk_tickets_categoria
    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
  CONSTRAINT fk_tickets_solicitante
    FOREIGN KEY (solicitante_id) REFERENCES usuarios(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_tickets_responsavel
    FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_tickets_departamento
    FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_historico (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL,
  tipo ENUM('created', 'assigned', 'status', 'comment', 'internal_note', 'attachment', 'department') NOT NULL,
  titulo VARCHAR(180) NOT NULL,
  descricao TEXT NULL,
  ator_id INT NULL,
  status_de VARCHAR(60) NULL,
  status_para VARCHAR(60) NULL,
  departamento_de_id INT NULL,
  departamento_para_id INT NULL,
  publico BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_historico_ticket (ticket_id, criado_em),
  CONSTRAINT fk_historico_ticket
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_historico_ator
    FOREIGN KEY (ator_id) REFERENCES usuarios(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_historico_departamento_de
    FOREIGN KEY (departamento_de_id) REFERENCES departamentos(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_historico_departamento_para
    FOREIGN KEY (departamento_para_id) REFERENCES departamentos(id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ticket_anexos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL,
  nome_arquivo VARCHAR(255) NOT NULL,
  caminho_arquivo VARCHAR(500) NULL,
  tamanho_bytes BIGINT NULL,
  tipo_arquivo VARCHAR(40) NULL,
  enviado_por_id INT NULL,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_anexos_ticket (ticket_id),
  CONSTRAINT fk_anexos_ticket
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_anexos_usuario
    FOREIGN KEY (enviado_por_id) REFERENCES usuarios(id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

INSERT IGNORE INTO departamentos (id, nome) VALUES
  (1, 'Financeiro'),
  (2, 'Produto'),
  (3, 'Suporte N1'),
  (4, 'Infraestrutura');

INSERT IGNORE INTO categorias (id, nome, prioridade, sla_horas, departamento_padrao_id) VALUES
  (1, 'Incidente Critico', 'Alta', 4, 4),
  (2, 'Incidente', 'Alta', 8, 3),
  (3, 'Bug de Interface', 'Media', 24, 2),
  (4, 'Melhoria', 'Media', 48, 2),
  (5, 'Duvida ou Solicitacao', 'Baixa', 72, 3),
  (6, 'Acesso', 'Baixa', 24, 3),
  (7, 'Documentacao', 'Baixa', 72, 2);
