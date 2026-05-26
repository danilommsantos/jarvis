"""
Script de uso unico via Django shell.
Importa ObservacaoRevisao a partir do arquivo de devolvidos.

Como executar:
    python manage.py shell
    >>> exec(open('importar_observacoes.py').read())
"""

import re
import difflib

from pautas.models import ObservacaoRevisao, RevisaoProcesso

# ── Configuracoes ──────────────────────────────────────────────────────────
ARQUIVO = (
    "C:\\Pendrive\\TST\\14. Pauta\\Devolvidos para corre"
    + chr(231) + chr(227) + "o.txt"
)
LIMIAR = 0.75

# ── Padroes ────────────────────────────────────────────────────────────────
RE_HEADER = re.compile(
    r'^[A-Za-z][A-Za-z0-9-]*\s+-\s+(\d+)-(\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})'
)
PAT_TEMA = re.compile(r'^Tema\s*:', re.IGNORECASE)
PAT_OBS  = re.compile(
    r'^Observa' + chr(231) + chr(227) + r'o\s*:', re.IGNORECASE
)
PAT_NOTA = re.compile(r'^Nota\s+geral\s*:', re.IGNORECASE)


def _similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() >= LIMIAR


def _ja_existe_db(revisao, tema, obs):
    for existente in ObservacaoRevisao.objects.filter(revisao=revisao, tema=tema):
        if _similar(existente.observacao, obs):
            return True
    return False


def _numero_completo(m):
    return m.group(1).zfill(7) + '-' + m.group(2)


def _flush_pair(pairs, tema, lines):
    obs = '\n'.join(lines).strip()
    if obs:
        pairs.append((tema.strip(), obs))


def _parse_content(lines):
    """Retorna lista de (tema, obs) a partir das linhas de conteudo do bloco."""
    pairs        = []
    state        = 'free'
    current_tema = []
    current_obs  = []
    current_nota = []
    current_free = []
    pending_tema = None  # tema acumulado antes de 'Observacao:'

    for line in lines:
        stripped = line.strip()

        if PAT_TEMA.match(stripped):
            if state == 'free' and current_free:
                _flush_pair(pairs, 'Geral', current_free)
                current_free = []
            elif state == 'obs' and current_obs:
                _flush_pair(pairs, pending_tema or 'Geral', current_obs)
                current_obs = []
            elif state == 'nota' and current_nota:
                _flush_pair(pairs, 'Nota geral', current_nota)
                current_nota = []
            state = 'tema'
            current_tema = []
            pending_tema = None

        elif PAT_OBS.match(stripped):
            if state == 'free':
                if current_free:
                    _flush_pair(pairs, 'Geral', current_free)
                    current_free = []
                pending_tema = None
            elif state == 'tema':
                pending_tema = '\n'.join(current_tema).strip()
                current_tema = []
            elif state == 'obs':
                if current_obs:
                    _flush_pair(pairs, pending_tema or 'Geral', current_obs)
                    current_obs = []
                pending_tema = None
            elif state == 'nota':
                if current_nota:
                    _flush_pair(pairs, 'Nota geral', current_nota)
                    current_nota = []
                pending_tema = None
            state = 'obs'
            current_obs = []

        elif PAT_NOTA.match(stripped):
            if state == 'free' and current_free:
                _flush_pair(pairs, 'Geral', current_free)
                current_free = []
            elif state == 'tema':
                current_tema = []
            elif state == 'obs' and current_obs:
                _flush_pair(pairs, pending_tema or 'Geral', current_obs)
                current_obs = []
            elif state == 'nota' and current_nota:
                _flush_pair(pairs, 'Nota geral', current_nota)
                current_nota = []
            state = 'nota'
            current_nota = []
            pending_tema = None

        else:
            raw = line.rstrip()
            if state == 'free':
                current_free.append(raw)
            elif state == 'tema':
                current_tema.append(raw)
            elif state == 'obs':
                current_obs.append(raw)
            elif state == 'nota':
                current_nota.append(raw)

    # Flush final
    if state == 'free' and current_free:
        _flush_pair(pairs, 'Geral', current_free)
    elif state == 'obs' and current_obs:
        _flush_pair(pairs, pending_tema or 'Geral', current_obs)
    elif state == 'nota' and current_nota:
        _flush_pair(pairs, 'Nota geral', current_nota)

    return pairs


# ── Leitura e parsing do arquivo ───────────────────────────────────────────

blocks = []           # list of ([numeros], [content_lines])
current_numbers = []
current_content = []
file_state = 'idle'   # 'idle', 'headers', 'content'

with open(ARQUIVO, encoding='utf-8') as f:
    raw_lines = f.readlines()

for line in raw_lines:
    m = RE_HEADER.match(line.strip())
    if m:
        numero = _numero_completo(m)
        if file_state == 'content':
            blocks.append((current_numbers[:], current_content[:]))
            current_numbers = [numero]
            current_content = []
            file_state = 'headers'
        else:  # idle ou headers
            current_numbers.append(numero)
            file_state = 'headers'
    else:
        if file_state == 'headers':
            file_state = 'content'
        if file_state == 'content':
            current_content.append(line.rstrip())
        # idle: descarta silenciosamente

# Flush ultimo bloco
if current_numbers and current_content:
    blocks.append((current_numbers, current_content))

print(f"Blocos lidos: {len(blocks)}")

# ── Inserir no banco ───────────────────────────────────────────────────────

# seen: numero -> [chaves ja processadas para este numero no arquivo]
seen = {}

criados       = 0
duplicatas    = 0
nao_encontrados = set()

for numeros, content_lines in blocks:
    pairs = _parse_content(content_lines)
    if not pairs:
        continue

    for numero in numeros:
        revisoes = list(RevisaoProcesso.objects.filter(processo__numero=numero))
        if not revisoes:
            nao_encontrados.add(numero)
            continue

        vistos = seen.setdefault(numero, [])

        for tema, obs in pairs:
            chave = tema + '|' + obs

            # Bloco duplicado no arquivo
            if any(_similar(chave, v) for v in vistos):
                duplicatas += 1
                continue

            vistos.append(chave)

            for revisao in revisoes:
                if _ja_existe_db(revisao, tema, obs):
                    duplicatas += 1
                    continue
                ObservacaoRevisao.objects.create(
                    revisao=revisao,
                    tema=tema,
                    observacao=obs,
                    duvida=False,
                )
                criados += 1

print(f"ObservacaoRevisao criadas : {criados}")
print(f"Duplicatas ignoradas      : {duplicatas}")

if nao_encontrados:
    print(f"\nProcessos nao encontrados ({len(nao_encontrados)}):")
    for n in sorted(nao_encontrados):
        print(f"  {n}")

print("Concluido.")
