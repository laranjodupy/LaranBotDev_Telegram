"""banco.py — Simulação de sistema bancário para o LaranBot.

EXCEÇÃO DOCUMENTADA à regra "tudo inline, sem arquivo separado" desta
versão (boilerplate). Isolado num arquivo próprio porque é uma simulação
com várias operações e regras de negócio próprias (saldo não pode ficar
negativo, valores em centavos, atomicidade de transferência) — misturar
tudo isso dentro do bloco gigante de `telegram_webhook`, em `entry.py`,
tornaria aquele bloco difícil de navegar, o oposto do que a regra
"tudo inline" tenta proteger. Ver README.md, seção "Decisões de design",
para o registro formal desta exceção.

Valores monetários são guardados e manipulados em CENTAVOS (inteiros),
NUNCA em float. R$ 10,50 vira o inteiro 1050. Isso evita o erro clássico
de ponto flutuante: números como 0.10 não têm representação binária
exata, e o erro se acumula a cada operação — depois de muitas transações,
o saldo "flutuante" pode divergir de centavos reais.
"""


def formatar_reais(centavos: int) -> str:
    """Converte um valor em centavos (int) para texto em reais.
    Ex.: 1050 -> "R$ 10,50" ; -350 -> "-R$ 3,50" """
    sinal = "-" if centavos < 0 else ""
    centavos_abs = abs(centavos)
    reais = centavos_abs // 100
    resto = centavos_abs % 100
    return f"{sinal}R$ {reais},{resto:02d}"


def reais_para_centavos(texto: str) -> int | None:
    """Converte texto digitado pelo usuário (ex.: "10.50" ou "10,50") para
    centavos (int). Retorna None se o texto não for um valor positivo válido."""
    texto = texto.strip().replace(",", ".")
    try:
        valor = float(texto)
    except ValueError:
        return None
    if valor <= 0:
        return None
    return round(valor * 100)


async def garantir_conta(env, chat_id: int) -> None:
    """Cria a conta do chat_id com saldo zero, se ela ainda não existir.

    INSERT OR IGNORE: se a conta já existir (chat_id é PRIMARY KEY), o
    comando simplesmente não faz nada — sem erro, sem duplicar linha.
    """
    await env.DB.prepare(
        "INSERT OR IGNORE INTO contas_bancarias (chat_id, saldo_centavos) VALUES (?, 0)"
    ).bind(chat_id).run()


async def consultar_saldo(env, chat_id: int) -> int:
    """Retorna o saldo atual, em centavos. Cria a conta (saldo 0) se ainda não existir."""
    await garantir_conta(env, chat_id)
    resultado = await env.DB.prepare(
        "SELECT saldo_centavos FROM contas_bancarias WHERE chat_id = ?"
    ).bind(chat_id).first()
    return resultado["saldo_centavos"] if resultado else 0


async def depositar(env, chat_id: int, valor_centavos: int) -> int:
    """Deposita um valor e registra a transação. Retorna o novo saldo, em centavos.

    Usa .batch() para que a atualização de saldo e o registro da transação
    aconteçam como uma única transação SQL — se um dos dois falhar, o D1
    reverte os dois (confirmado na documentação oficial do D1: statements
    em batch são transações de verdade, com rollback automático em falha).
    """
    await garantir_conta(env, chat_id)
    await env.DB.batch([
        env.DB.prepare(
            "UPDATE contas_bancarias SET saldo_centavos = saldo_centavos + ? WHERE chat_id = ?"
        ).bind(valor_centavos, chat_id),
        env.DB.prepare(
            "INSERT INTO transacoes_bancarias (chat_id_origem, tipo, valor_centavos) VALUES (?, 'deposito', ?)"
        ).bind(chat_id, valor_centavos),
    ])
    return await consultar_saldo(env, chat_id)


async def sacar(env, chat_id: int, valor_centavos: int) -> tuple[bool, int]:
    """Tenta sacar um valor. Retorna (sucesso, saldo_atual_em_centavos).
    Se o saldo for insuficiente, sucesso=False e nada é alterado."""
    saldo_atual = await consultar_saldo(env, chat_id)
    if valor_centavos > saldo_atual:
        return False, saldo_atual

    await env.DB.batch([
        env.DB.prepare(
            "UPDATE contas_bancarias SET saldo_centavos = saldo_centavos - ? WHERE chat_id = ?"
        ).bind(valor_centavos, chat_id),
        env.DB.prepare(
            "INSERT INTO transacoes_bancarias (chat_id_origem, tipo, valor_centavos) VALUES (?, 'saque', ?)"
        ).bind(chat_id, valor_centavos),
    ])
    novo_saldo = await consultar_saldo(env, chat_id)
    return True, novo_saldo


async def transferir(env, chat_id_origem: int, chat_id_destino: int, valor_centavos: int) -> tuple[bool, str]:
    """Tenta transferir um valor entre duas contas.
    Retorna (sucesso, mensagem_de_erro) — mensagem_de_erro é "" se sucesso=True.

    NOTA SOBRE CONCORRÊNCIA (limitação conhecida, documentada de propósito):
    a checagem de saldo (SELECT, em consultar_saldo) e a atualização
    (.batch(), abaixo) não são uma única operação atômica entre si — existe
    uma janela teórica onde duas transferências simultâneas da MESMA conta
    poderiam ambas passar pela checagem antes de qualquer uma debitar de
    verdade. Para uma simulação de aprendizado, essa é uma simplificação
    aceita, não um descuido. Uma versão "à prova de concorrência" faria a
    checagem dentro da própria condição do UPDATE, com algo como
    "WHERE chat_id = ? AND saldo_centavos >= ?" e conferiria se alguma
    linha foi de fato alterada.
    """
    if chat_id_origem == chat_id_destino:
        return False, "Não é possível transferir para você mesmo."

    await garantir_conta(env, chat_id_origem)
    await garantir_conta(env, chat_id_destino)

    saldo_origem = await consultar_saldo(env, chat_id_origem)
    if valor_centavos > saldo_origem:
        return False, "Saldo insuficiente."

    await env.DB.batch([
        env.DB.prepare(
            "UPDATE contas_bancarias SET saldo_centavos = saldo_centavos - ? WHERE chat_id = ?"
        ).bind(valor_centavos, chat_id_origem),
        env.DB.prepare(
            "UPDATE contas_bancarias SET saldo_centavos = saldo_centavos + ? WHERE chat_id = ?"
        ).bind(valor_centavos, chat_id_destino),
        env.DB.prepare(
            "INSERT INTO transacoes_bancarias (chat_id_origem, chat_id_destino, tipo, valor_centavos) "
            "VALUES (?, ?, 'transferencia', ?)"
        ).bind(chat_id_origem, chat_id_destino, valor_centavos),
    ])
    return True, ""


async def historico(env, chat_id: int, limite: int = 10) -> list:
    """Retorna as últimas transações envolvendo este chat_id (como origem
    OU destino), mais recentes primeiro."""
    resultado = await env.DB.prepare(
        "SELECT tipo, valor_centavos, chat_id_origem, chat_id_destino, criado_em "
        "FROM transacoes_bancarias "
        "WHERE chat_id_origem = ? OR chat_id_destino = ? "
        "ORDER BY id DESC LIMIT ?"
    ).bind(chat_id, chat_id, limite).all()
    return resultado.results if hasattr(resultado, "results") else resultado