"""
Script de uso unico via Django shell.

Como executar:
    python manage.py shell
    >>> exec(open('atualizar_minutantes.py').read())
"""

import re
import sys

from processos.models import Responsavel
from pautas.models import RevisaoProcesso

# chr(225) = a com acento agudo, evita nao-ASCII no fonte
ARQUIVO = "C:\\Pendrive\\TST\\14. Pauta\\Respons" + chr(225) + "vel.txt"
NOMES_IGNORAR = {"Minutante desconhecido"}

# --- 1. Listar responsaveis existentes --------------------------------------

todos = list(Responsavel.objects.order_by("nome_completo"))
print(f"\n{len(todos)} responsaveis no banco:")
for r in todos:
    print(f"  [{r.id:>3}] {r.nome_completo}")

# --- 2. Parsear o arquivo ---------------------------------------------------

padrao_numero = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
entradas = []  # lista de (numero, nome_arquivo)

with open(ARQUIVO, encoding="utf-8") as f:
    for i, linha in enumerate(f, 1):
        linha = linha.strip()
        if not linha:
            continue

        match = padrao_numero.search(linha)
        if not match:
            print(f"AVISO linha {i}: numero nao encontrado -> {linha}")
            continue

        numero = match.group()
        partes = linha.rsplit(" - ", 1)
        if len(partes) != 2:
            print(f"AVISO linha {i}: formato inesperado -> {linha}")
            continue

        nome = partes[1].strip()
        if nome in NOMES_IGNORAR:
            continue

        entradas.append((numero, nome))

nomes_unicos = sorted(set(nome for _, nome in entradas))
print(f"\n{len(entradas)} entradas lidas, {len(nomes_unicos)} nomes unicos.\n")

# --- 3. Tentar match automatico e confirmar manualmente --------------------

def candidatos_para(nome, responsaveis):
    """Retorna responsaveis cujo nome_completo contem todas as palavras do nome."""
    palavras = nome.lower().split()
    return [
        r for r in responsaveis
        if all(p in r.nome_completo.lower() for p in palavras)
    ]

mapeamento = {}  # nome_arquivo -> Responsavel ou None

print("=" * 60)
print("ETAPA DE CONFIRMACAO DO MAPEAMENTO")
print("=" * 60)

for nome in nomes_unicos:
    candidatos = candidatos_para(nome, todos)
    count_proc = sum(1 for _, n in entradas if n == nome)

    print(f"\n  Nome no arquivo : '{nome}' ({count_proc} processo(s))")

    if not candidatos:
        print("  -> Nenhum candidato encontrado automaticamente.")
        print("    Responsaveis disponiveis:")
        for r in todos:
            print(f"      [{r.id:>3}] {r.nome_completo}")
        id_dig = input("    Digite o ID correto (ou 0 para ignorar): ").strip()

    elif len(candidatos) == 1:
        r = candidatos[0]
        print(f"  -> Candidato unico: [{r.id}] {r.nome_completo}")
        resp = input("    Confirma? [s]/n ou ID alternativo: ").strip()

        if resp.lower() in ("s", ""):
            mapeamento[nome] = r
            continue
        elif resp.lower() == "n":
            id_dig = input("    Digite o ID correto (ou 0 para ignorar): ").strip()
        else:
            id_dig = resp  # tentou digitar ID direto

    else:
        print(f"  -> {len(candidatos)} candidatos:")
        for r in candidatos:
            print(f"      [{r.id:>3}] {r.nome_completo}")
        id_dig = input("    Digite o ID correto (ou 0 para ignorar): ").strip()

    # Resolver o ID digitado
    if id_dig == "0":
        mapeamento[nome] = None
        print("    -> Ignorado.")
    else:
        try:
            r_escolhido = Responsavel.objects.get(id=int(id_dig))
            mapeamento[nome] = r_escolhido
            print(f"    -> Mapeado para: {r_escolhido.nome_completo}")
        except (ValueError, Responsavel.DoesNotExist):
            print("    ID invalido. Ignorando este nome.")
            mapeamento[nome] = None

# --- 4. Resumo final antes de aplicar --------------------------------------

print("\n" + "=" * 60)
print("RESUMO FINAL")
print("=" * 60)

validos = {n: r for n, r in mapeamento.items() if r is not None}
ignorados = [n for n, r in mapeamento.items() if r is None]

for nome, r in validos.items():
    count = sum(1 for _, n in entradas if n == nome)
    print(f"  '{nome}' -> {r.nome_completo} ({count} processo(s))")

if ignorados:
    print(f"\n  Ignorados ({len(ignorados)}): {', '.join(ignorados)}")

total_linhas_validas = sum(
    1 for _, nome in entradas if mapeamento.get(nome) is not None
)
print(f"\n  Total de linhas que serao processadas: {total_linhas_validas}")
print("  (So atualiza RevisaoProcesso sem minutante)")

confirma = input("\nAplicar as atualizacoes? (s/n): ").strip().lower()
if confirma != "s":
    print("Operacao cancelada.")
    sys.exit(0)

# --- 5. Aplicar atualizacoes -----------------------------------------------

atualizados = 0
sem_revisao = []
ja_preenchido = []

for numero, nome in entradas:
    responsavel = mapeamento.get(nome)
    if responsavel is None:
        continue

    qs_sem = RevisaoProcesso.objects.filter(
        processo__numero=numero,
        minutante__isnull=True,
    )

    if qs_sem.exists():
        count = qs_sem.update(minutante=responsavel)
        atualizados += count
    else:
        if RevisaoProcesso.objects.filter(processo__numero=numero).exists():
            ja_preenchido.append(numero)
        else:
            sem_revisao.append(numero)

print("\n" + "=" * 60)
print(f"RevisaoProcesso atualizadas : {atualizados}")

if sem_revisao:
    print(f"\nSem RevisaoProcesso no banco ({len(sem_revisao)}):")
    for n in sem_revisao:
        print(f"  {n}")

if ja_preenchido:
    print(f"\nJa tinham minutante - nao alterados ({len(ja_preenchido)}):")
    for n in ja_preenchido:
        print(f"  {n}")

print("=" * 60)
print("Concluido.")
