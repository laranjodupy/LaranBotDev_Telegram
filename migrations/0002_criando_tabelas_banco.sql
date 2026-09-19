-- Migration number: 0002
-- Tabelas da simulação de sistema bancário (comando /banco).

CREATE TABLE IF NOT EXISTS contas_bancarias (
  chat_id INTEGER PRIMARY KEY,
  saldo_centavos INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Valores em CENTAVOS (inteiro), nunca em float — ver comentário no topo
-- de banco.py para o porquê.

CREATE TABLE IF NOT EXISTS transacoes_bancarias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id_origem INTEGER NOT NULL,
  chat_id_destino INTEGER,              -- NULL para depósito/saque; preenchido só em transferência
  tipo TEXT NOT NULL CHECK (tipo IN ('deposito', 'saque', 'transferencia')),
  valor_centavos INTEGER NOT NULL,
  criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);