import re

def remove_assinatura(linha):
    if 'Assinado eletronicamente por:' in linha:
        linha = linha.split(' - ')
        if len(linha) >= 2:
            linha.pop(0)
            linha.pop(0)
        else:
            return ''
        linha = ' - '.join(linha)
        return linha[7:]
    elif 'Documento assinado eletronicamente por ' in linha:
        padrao = r'Documento assinado eletronicamente por .*? - \S{7}'
        return re.sub(padrao, '', linha, flags=re.DOTALL)
    elif 'Assinado eletronicamente. A Certificação Digital pertence a:' in linha:
        return ''
    else:
        return linha



def remove_segredo_de_justica(linha):
    if 'Documento em sigilo ou segredo de justiça Usuário em visibilidade: DANILO MONTEIRO DE MELO SANTOS' in linha:
        return ''
    else:
        return linha

def remove_num(linha):
    if 'Num. ' in linha and linha[:5] == 'Num. ':
        linha = linha[22:]
        if 'Assinado eletronicamente.' in linha:
            partes = linha.split(':')[2:]
            partes[0] = partes[0][9:]
            linha = ':'.join(partes)
        return linha
    else:
        return linha

def remove_espacos_extras(linhas):
    # Remove espaços no início e no final das linhas
    linhas = [linha.strip() for linha in linhas if linha.strip()]
    # Remove espaços duplos
    linhas = [' '.join(linha.split()) for linha in linhas if linha.strip()]
    return linhas

def comeca_com_item_numerico(linha):
    return bool(re.match(r'^\d+\.\d+\s', linha.strip()))

# Títulos principais que SEMPRE devem iniciar nova linha
SECOES_PRINCIPAIS = {'PRESSUPOSTOS EXTRÍNSECOS', 'PRESSUPOSTOS INTRÍNSECOS', '---', 'CONSIDERAÇÕES PRELIMINARES', 'RECURSO DE REVISTA', 'CONCLUSÃO'}

# Conectores que impedem a quebra no final de um título
CONECTIVOS_QUEBRA = (' DE', ' E', ' OU', ' COM', ' DOS', ' DAS', ' AOS', ' ÀS', ' PARA', ' EM', ' POR', ' DO', ' DA', ' NOS', ' NAS')

# Abreviações que impedem quebra após o ponto
ABREVIACOES_PROTEGIDAS = ('art', 'arts', 'fl', 'fls', 'id', 'pje', 'oj', 'inc', 'al', 'clt')

def linha_eh_titulo(linha):
    """
    Verifica se a linha é um título permitindo conectores minúsculos (de, do, da)
    e ignorando números/símbolos.
    """
    conectores = {'de', 'do', 'da', 'dos', 'das', 'e', 'ou', 'com', 'por', 'em', 'para'}
    # Extrai apenas palavras (letras)
    palavras = re.findall(r'[a-zA-ZÀ-ÿ]+', linha)
    if not palavras: return False
    
    # Filtra apenas as palavras que não são conectores e verifica se estão em MAIÚSCULAS
    palavras_principais = [p for p in palavras if p.lower() not in conectores]
    if not palavras_principais:
        return all(p.isupper() for p in palavras)
    
    return all(p.isupper() for p in palavras_principais)

def adiciona_quebra(linha, proxima):
    linha_segura = linha.rstrip() 
    proxima_segura = proxima.lstrip()
    
    def debug_regras(regra, linha_segura=linha_segura, debug=False):
        if debug:
            print(f"{regra}: {linha_segura[:50]}")
    
    if linha_segura in SECOES_PRINCIPAIS:
        debug_regras(regra='Regra  1')
        return linha_segura + '\n'
    
    if linha_segura.endswith('/ Recurso / Transcendência') or linha_segura.endswith('Transcendência'):
        debug_regras(regra='Regra  2')
        return linha_segura + '\n'
    
    if not proxima_segura: 
        debug_regras(regra='Regra  3')
        return linha_segura + ' '

    # 1. GATILHOS DE QUEBRA PRIORITÁRIOS (PRÓXIMA LINHA)
    if proxima_segura in SECOES_PRINCIPAIS:
        debug_regras(regra='Regra  4')
        return linha_segura + '\n'
        
    palavras_chave = ('Alegação(ões):', 'Fundamentos:', 'Recurso de:', 'Processo Nº')
    if any(proxima_segura.startswith(kw) for kw in palavras_chave):
        debug_regras(regra='Regra  5')
        return linha_segura + '\n'

    # 2. LÓGICA DE TÍTULOS (LINHA ATUAL)
    eh_titulo_atual = linha_eh_titulo(linha_segura)
    eh_proximo_titulo = linha_eh_titulo(proxima_segura)
    
    # Detecta se a próxima linha é um novo item (Ex: 2.2, 3.1, II)
    eh_item_linha = comeca_com_item_numerico(linha_segura)
    eh_item_proxima = comeca_com_item_numerico(proxima_segura)
    # print(eh_item_linha, eh_item_proxima)
    
    if eh_item_proxima and eh_proximo_titulo and not eh_titulo_atual:
        if linha_eh_titulo(proxima_segura):
            debug_regras(regra='Regra  6')
            return linha_segura + '\n'
    
    # Se ambos são títulos, mantém na mesma linha (resolve o erro do seu exemplo)
    if eh_titulo_atual and eh_proximo_titulo and not eh_item_proxima:
        debug_regras(regra='Regra  7')
        return linha_segura + ' '

    if eh_titulo_atual and eh_proximo_titulo and eh_item_proxima:
        debug_regras(regra='Regra  8')
        return linha_segura + '\n'
    
    # Proteção por conectivo no fim do título
    if eh_titulo_atual and linha_segura.endswith(CONECTIVOS_QUEBRA):
        debug_regras(regra='Regra  9')
        return linha_segura + ' '

    # Fim de título para texto normal
    if eh_titulo_atual and not eh_proximo_titulo:
        debug_regras(regra='Regra 10')        
        return linha_segura + '\n'

    # 3. TEXTO NORMAL (Abreviações e Fim de Frase)
    if not eh_titulo_atual:
        palavras = linha_segura.lower().replace('.', '').replace('"', '').split()
        ultima_palavra = palavras[-1] if palavras else ""
        
        # Detecta ponto final seguido de aspas
        termina_frase = re.search(r'\.["\']?$', linha_segura)
        
        if termina_frase and ultima_palavra not in ABREVIACOES_PROTEGIDAS:
            if proxima_segura[0].isupper() or proxima_segura[0].isdigit():
                debug_regras(regra='Regra 11')        
                return linha_segura + '\n'

        if linha_segura.endswith(':'):
            if not (proxima_segura.startswith('R$') or proxima_segura.lower().startswith('id')):
                debug_regras(regra='Regra 12')        
                return linha_segura + '\n'
    
    debug_regras(regra='Regra 13')
    return linha_segura + ' '

def corrige_texto_pdf(texto):
    # print(repr(texto))
    if not texto: return ""
    linhas = texto.splitlines()
    # Limpeza e remoção de assinaturas/segredos    
    linhas = [remove_segredo_de_justica(l) for l in linhas]
    linhas = [remove_num(l) for l in linhas]
    linhas = [re.sub(r'^Fls\.\:\s*\d{3,4}\s*', '', l) for l in linhas]
    # linhas = [l.replace(' ', ' ') for l in linhas] 
    linhas = remove_espacos_extras(linhas)
    linhas = [remove_assinatura(l) for l in linhas]
    linhas = [l for l in linhas if l != '']
    
    for i in range(len(linhas) - 1):
        # print(repr(linhas[i]))
        linhas[i] = adiciona_quebra(linhas[i], linhas[i+1])
    
    return "".join(linhas)

# Mantenha as funções auxiliares (remove_assinatura, etc.) abaixo