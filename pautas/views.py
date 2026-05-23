import datetime
import os
import re
import pyperclip

import FreeSimpleGUI as sg

from icecream import ic
from nup_poder_judiciario import NumeroUnicoProcesso as nup
from scipy import stats

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, F, Window, Q, Prefetch
from django.db.models.functions import Rank
from django.contrib import messages # Importe o sistema de mensagens
from django.utils import timezone

from .models import Pauta, RevisaoProcesso, ListaProcessos, ObservacaoRevisao, StatusRevisao, Memorial, AtendimentoAdvogado
from .forms import AdicionarProcessosLoteForm, ObservacaoRevisaoForm, MarcarRRProvidoForm, MoverProcessosForm
from .services.docx_service import DocxService
from .services.automation import abre_voto_ge, abre_voto_pasta_pauta

from main.utils.utils import formatar_tempo, buscar_pecas_btv
from processos.models import Processo, Classe
from processos.services.parser import formatar_numero_processo


def lista_pautas(request):
    pautas = Pauta.objects.annotate(
        total_processos=Count('revisoes')
    ).all()
    context = {
        'pautas': pautas,
    }
    return render(request, 'pautas/lista_pautas.html', context)


def pauta(request, pk):
    pauta = get_object_or_404(Pauta, pk=pk)
    form = AdicionarProcessosLoteForm(request.POST or None, pauta=pauta)
    form_rr = MarcarRRProvidoForm(request.POST)
    form_mover = MoverProcessosForm(request.POST or None, pauta=pauta)
    
    if request.method == 'POST':
        # --- AÇÃO 1: Adicionar Processos em Lote ---
        if 'btn_adicionar_lote' in request.POST:
            if form.is_valid():
                numeros_raw = form.cleaned_data['processos_numeros']
                lista_origem = form.cleaned_data['lista_origem']
                nome_nova_lista = form.cleaned_data.get('nome_nova_lista')
                # VARIAVEL inclusao_tardia APAGADA DAQUI!

                if nome_nova_lista:
                    lista_origem = ListaProcessos.objects.create(pauta=pauta, nome=nome_nova_lista)
                elif not lista_origem and not nome_nova_lista:
                    total_listas = total_listas = pauta.listas.count()
                    lista_origem = ListaProcessos.objects.create(pauta=pauta, titulo=f"Lote {total_listas + 1}")

                numeros_lista = re.split(r'[,\n\r;]+', numeros_raw)
                adicionados = 0
                ignorados = 0
                
                total = len(numeros_lista)
                
                for i, num in enumerate(numeros_lista, start=1):
                    ic(num)
                    sg.one_line_progress_meter("Inclui na pauta", i, total, orientation="h")
                    num_limpo = num.strip()
                    if num_limpo:
                        if " - " not in num_limpo:
                            continue
                        fase, numero = formatar_numero_processo(num_limpo)
                        processo = Processo.objects.filter(numero=numero).first()
                        if not processo:
                            if '-' in fase:
                                classe = fase.split('-')[0].strip()
                            else:
                                classe = fase.strip()
                            classe, _ = Classe.objects.get_or_create(nome=classe)
                            processo = Processo.objects.create(
                                numero=numero, 
                                fase_completa=fase, 
                                classe=classe, 
                                data_entrada=None,)
                        ic(processo.classe.nome)
                        revisao, rev_created = RevisaoProcesso.objects.get_or_create(
                            pauta=pauta,
                            processo=processo,
                            defaults={
                                'lista_origem': lista_origem,
                            }
                        )
                        
                        if rev_created:
                            adicionados += 1
                        else:
                            ignorados += 1
                
                # Dispara um alerta de sucesso que vai aparecer no seu base.html
                messages.success(request, f"{adicionados} processos incluídos com sucesso! ({ignorados} ignorados por já estarem na pauta).")
                return redirect('pautas:pauta', pk=pauta.pk)

        # --- AÇÃO 2: Mover Processos para Outra Pauta ---
        elif 'btn_mover_processos' in request.POST:
            if form_mover.is_valid():
                numeros_raw = form_mover.cleaned_data['processos_numeros']
                pauta_destino = form_mover.cleaned_data['pauta_destino']

                numeros_lista = re.split(r'[,\n\r;]+', numeros_raw)
                movidos = 0
                nao_encontrados = []
                ja_existem = []

                for num in numeros_lista:
                    num_limpo = num.strip()
                    if not num_limpo:
                        continue

                    if " - " in num_limpo:
                        _, numero = formatar_numero_processo(num_limpo)
                    else:
                        from nup_poder_judiciario import NumeroUnicoProcesso as nup
                        try:
                            numero = nup(num_limpo).formatado()
                        except Exception:
                            nao_encontrados.append(num_limpo)
                            continue

                    revisao = RevisaoProcesso.objects.filter(pauta=pauta, processo__numero=numero).first()
                    if not revisao:
                        nao_encontrados.append(numero)
                        continue

                    if RevisaoProcesso.objects.filter(pauta=pauta_destino, processo__numero=numero).exists():
                        ja_existem.append(numero)
                        continue

                    revisao.pauta = pauta_destino
                    revisao.lista_origem = None
                    revisao.save()
                    movidos += 1

                if movidos:
                    messages.success(request, f"{movidos} processo(s) movido(s) para '{pauta_destino}'.")
                if nao_encontrados:
                    messages.warning(request, f"{len(nao_encontrados)} número(s) não encontrado(s) nesta pauta: {', '.join(nao_encontrados[:5])}{'...' if len(nao_encontrados) > 5 else ''}.")
                if ja_existem:
                    messages.error(request, f"{len(ja_existem)} processo(s) já existe(m) na pauta de destino: {', '.join(ja_existem[:5])}{'...' if len(ja_existem) > 5 else ''}.")

                return redirect('pautas:pauta', pk=pauta.pk)

        # --- AÇÃO 3: Marcar RR Providos ---
        elif 'btn_marcar_rr' in request.POST:
            if form_rr.is_valid():
                rr_providos_raw = form_rr.cleaned_data.get('processos_rr_providos', '')
                lista_rr = re.split(r'[,\n\r;]+', rr_providos_raw)
                numeros_para_atualizar = []
                
                total = len(lista_rr)
                for i, num in enumerate(lista_rr, start=1):
                    sg.one_line_progress_meter("RRs providos", i, total, orientation="h")
                    num_limpo = num.strip()
                    if num_limpo:
                        numero = nup(num_limpo).formatado()
                        numeros_para_atualizar.append(numero)
                
                atualizados_rr = RevisaoProcesso.objects.filter(
                    pauta=pauta,
                    processo__numero__in=numeros_para_atualizar,
                ).update(rr_provido=True)
                
                if atualizados_rr > 0:
                    messages.success(request, f"{atualizados_rr} processo(s) marcado(s) com RR Provido.")
                else:
                    messages.warning(request, "Nenhum dos processos informados foi encontrado nesta pauta.")
                    
                return redirect('pautas:pauta', pk=pauta.pk)


    revisoes = pauta.revisoes.ordenar_pela_prioridade().select_related(
    'processo', 'minutante'
    ).prefetch_related(
        # Traz apenas os atendimentos DESTA pauta
        Prefetch(
            'processo__atendimentos',
            queryset=AtendimentoAdvogado.objects.filter(pauta=pauta)
        ),
        # Traz apenas os memoriais DESTA pauta
        Prefetch(
            'processo__memoriais',
            queryset=Memorial.objects.filter(pauta=pauta)
        )
    )
    
    total_processos = revisoes.count()
    relatorio_classes = revisoes.values('processo__classe__nome').annotate(total=Count('id')).order_by('-total')
    relatorio_status = revisoes.values('status__nome').annotate(total=Count('id')).order_by('-total')
    relatorio_minutante = revisoes.values('minutante__inicial', 'minutante__nome_completo', 'minutante__user__first_name').annotate(total=Count('id')).order_by('-total')
    
    context = {
        'pauta': pauta,
        'revisoes': revisoes,
        'total_processos': total_processos,
        'relatorio_classes': relatorio_classes,
        'relatorio_status': relatorio_status,
        'relatorio_minutante': relatorio_minutante,
        'form': form,
        'form_rr': form_rr,
        'form_mover': form_mover,
    }
    return render(request, 'pautas/pauta.html', context)


def revisar_processo(request, pk):
    print('revisar_processo')
    revisao = get_object_or_404(RevisaoProcesso.objects.select_related(
        'processo', 
        'pauta', 
        'minutante'
        ), pk=pk)
    processo = revisao.processo
    observacoes = revisao.observacoes.all() 
    status_disponiveis = StatusRevisao.objects.all()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        # --- NOVO: Resetar o cronômetro ---
        if form_type == 'resetar_tempo':
            revisao.tempo_gasto = 0
            revisao.save()
            messages.success(request, 'Cronômetro zerado com sucesso!', extra_tags="timeout-2000")
            return redirect('pautas:revisar_processo', pk=revisao.pk)

        # --- SALVAMENTO GLOBAL DE TEMPO ---
        # Salva em qualquer submissão, desde que não seja a ação de resetar
        if form_type != 'resetar_tempo':
            tempo_str = request.POST.get('tempo_gasto', '0')
            if tempo_str.isdigit():
                tempo_enviado = int(tempo_str)
                # Só salva se o tempo enviado for maior que o salvo no banco (evita retrocessos acidentais)
                if tempo_enviado > revisao.tempo_gasto:
                    revisao.tempo_gasto = tempo_enviado
                    revisao.save() 

        # --- 1. Salvar Formulário Principal (Status e Anotações) ---
        if form_type == 'salvar_revisao':
            anotacoes = request.POST.get('anotacoes', '')
            revisao.anotacoes = anotacoes
            revisao.save() # O tempo já foi salvo acima

            status_selecionados_ids = request.POST.getlist('status')
            revisao.status.set(status_selecionados_ids)
            
            if 'btn_proximo' in request.POST:
                messages.success(request, "Processo salvo! Carregando o próximo...", extra_tags="timeout-4000")
                return redirect('pautas:proxima_revisao', pauta_pk=revisao.pauta.pk)
            
            messages.success(request, 'Revisão guardada com sucesso!', extra_tags="timeout-4000")
            return redirect('pautas:revisar_processo', pk=revisao.pk)
        
        # --- 2. Acrescentar Nova Observação ---
        elif form_type == 'salvar_observacao':
            form_obs = ObservacaoRevisaoForm(request.POST)
            if form_obs.is_valid():
                nova_obs = form_obs.save(commit=False)
                nova_obs.revisao = revisao
                nova_obs.save()
                messages.success(request, 'Observação acrescentada com sucesso!', extra_tags="timeout-4000")
                return redirect('pautas:revisar_processo', pk=revisao.pk)

        # --- 3. Editar Observação Existente ---
        elif form_type == 'editar_observacao':
            obs_id = request.POST.get('obs_id')
            obs = get_object_or_404(ObservacaoRevisao, id=obs_id, revisao=revisao)
            
            form_obs = ObservacaoRevisaoForm(request.POST, instance=obs)
            if form_obs.is_valid():
                form_obs.save()
                messages.success(request, 'Observação atualizada com sucesso!', extra_tags="timeout-4000")
                return redirect('pautas:revisar_processo', pk=revisao.pk)

        # --- 4. Excluir Observação ---
        elif form_type == 'excluir_observacao':
            obs_id = request.POST.get('obs_id')
            obs = get_object_or_404(ObservacaoRevisao, id=obs_id, revisao=revisao)
            obs.delete()
            messages.success(request, 'Observação excluída com sucesso!', extra_tags="timeout-4000")
            return redirect('pautas:revisar_processo', pk=revisao.pk)
            
    else:
        try:
            # Usa o Python para forçar a cópia no sistema operativo local
            pyperclip.copy(processo.numero)            
            # Cria a mensagem de aviso (equivalente ao sg.popup)
            messages.info(request, f"Copiado o número: {processo.numero}", extra_tags="timeout-2000")
            # abre_voto_ge(processo.numero)
            # abre_voto_pasta_pauta(pasta=revisao.pauta.pasta, fase_completa=processo.fase_completa, numero=processo.numero, request=request)
        except Exception as e:
            print(f"Erro no pyperclip/automação: {e}")
    
    agora = timezone.localtime(timezone.now())
    revisoes_pauta = revisao.pauta.revisoes.filter(rr_provido=False)
    
    concluidos = revisoes_pauta.filter(status__eh_revisado=True, tempo_gasto__gt=0)
    pendentes = revisoes_pauta.filter(~Q(status__eh_revisado=True))

    ultima_tarefa = concluidos.order_by('-atualizado_em').first()
    tempo_ultima = ultima_tarefa.tempo_gasto if ultima_tarefa else 0

    # Inicialização de variáveis de métricas
    media_servidor_segs = 0
    estimativa_servidor_segs = 0
    pendentes_servidor_count = 0
    concluidos_servidor_count = 0
    total_servidor_count = 0
    percentual_servidor = 0
    
    if revisao.minutante:
        pendentes_servidor = pendentes.filter(minutante=revisao.minutante)
        tempos_servidor = list(concluidos.filter(minutante=revisao.minutante).values_list('tempo_gasto', flat=True))
        
        if tempos_servidor:
            media_servidor_segs = float(stats.trim_mean(tempos_servidor, 0.1))
            
        pendentes_servidor_count = pendentes_servidor.count()
        estimativa_servidor_segs = media_servidor_segs * pendentes_servidor_count
        concluidos_servidor_count = concluidos.filter(minutante=revisao.minutante).count()
        total_servidor_count = pendentes_servidor_count + concluidos_servidor_count
        
        if total_servidor_count > 0:
            percentual_servidor = int((concluidos_servidor_count / total_servidor_count) * 100)

    tempos_total = list(concluidos.values_list('tempo_gasto', flat=True))
    media_total_segs = float(stats.trim_mean(tempos_total, 0.1)) if tempos_total else 0
    
    pendentes_total_count = pendentes.count()
    concluidos_total_count = concluidos.count()
    total_pauta_count = pendentes_total_count + concluidos_total_count
    
    percentual_total = int((concluidos_total_count / total_pauta_count) * 100) if total_pauta_count > 0 else 0
    estimativa_total_segs = media_total_segs * pendentes_total_count
    
    btv_pecas = buscar_pecas_btv(processo.numero)

    estatisticas = {
        'ultima_tarefa': formatar_tempo(tempo_ultima),
        'media_servidor': formatar_tempo(media_servidor_segs),
        'estimativa_servidor': formatar_tempo(estimativa_servidor_segs),
        'horario_servidor': (agora + datetime.timedelta(seconds=estimativa_servidor_segs)).strftime('%H:%M') if estimativa_servidor_segs > 0 else '-',
        'media_total': formatar_tempo(media_total_segs),
        'estimativa_total': formatar_tempo(estimativa_total_segs),
        'horario_total': (agora + datetime.timedelta(seconds=estimativa_total_segs)).strftime('%H:%M') if estimativa_total_segs > 0 else '-',
        'media_servidor_raw': media_servidor_segs, 
        
        'concluidos_servidor': concluidos_servidor_count,
        'total_servidor': total_servidor_count,
        'pendentes_servidor': pendentes_servidor_count,
        'percentual_servidor': percentual_servidor,
        
        'concluidos_total': concluidos_total_count,
        'total_pauta': total_pauta_count,
        'pendentes_total': pendentes_total_count,
        'percentual_total': percentual_total,
    }

    form_obs = ObservacaoRevisaoForm()

    context = {
        'revisao': revisao,
        'processo': processo,
        'observacoes': observacoes,
        'status_disponiveis': status_disponiveis,
        'form_obs': form_obs,
        'estatisticas': estatisticas,
        'btv_pecas': btv_pecas,
    }
    return render(request, 'pautas/revisar_processo.html', context)


def extrair_minutantes_docx(request, pk):
    pauta = get_object_or_404(Pauta, pk=pk)
    
    # Verifica se a pasta existe antes de começar
    if not pauta.pasta or not os.path.exists(pauta.pasta):
        messages.error(request, f"Caminho da pasta inválido ou não configurado: {pauta.pasta}")
        return redirect('pautas:pauta', pk=pauta.pk)

    # 1. Filtramos APENAS as revisões desta pauta onde o minutante ainda é None (nulo)
    revisoes_pendentes = pauta.revisoes.filter(minutante__isnull=True).select_related('processo')
    
    if not revisoes_pendentes.exists():
        messages.info(request, "Todos os processos desta pauta já possuem minutantes vinculados.")
        return redirect('pautas:pauta', pk=pauta.pk)

    service = DocxService()
    arquivos_na_pasta = os.listdir(pauta.pasta)
    atualizados = 0
    
    total = revisoes_pendentes.count()

    for i, revisao in enumerate(revisoes_pendentes, start=1):
        sg.one_line_progress_meter('Extrai minutante', i, total, orientation='h')
        # 2. Busca o arquivo que contenha o número do processo
        arquivo_correspondente = None
        # Otimização: removemos pontuação do número para comparação mais segura
        num_limpo = ''.join(filter(str.isdigit, revisao.processo.numero))
        
        for f in arquivos_na_pasta:
            f_limpo = ''.join(filter(str.isdigit, f))
            if f.endswith('.docx') and num_limpo in f_limpo:
                arquivo_correspondente = os.path.join(pauta.pasta, f)
                break
        
        # 3. Se achou o arquivo, tenta extrair o minutante
        if arquivo_correspondente:
            minutante = service.analisar_minutante_no_arquivo(arquivo_correspondente)
            if minutante:
                revisao.minutante = minutante
                revisao.save()
                atualizados += 1

    # 4. Feedback final
    if atualizados > 0:
        messages.success(request, f"Sucesso! {atualizados} novos minutantes foram identificados e vinculados.")
    else:
        messages.warning(request, "A pasta foi analisada, mas nenhum novo minutante foi encontrado nos arquivos correspondentes.")

    return redirect('pautas:pauta', pk=pauta.pk)


def alternar_pular(request, pk):
    revisao = get_object_or_404(RevisaoProcesso, pk=pk)
    revisao.pulado = not revisao.pulado
    revisao.save()
    
    if 'revisar' in request.META.get('HTTP_REFERER', '') and revisao.pulado:
        return redirect('pautas:proxima_revisao', pauta_pk=revisao.pauta.pk)
        
    return redirect('pautas:revisar_processo', pk=revisao.pk)


def proxima_revisao(request, pauta_pk):
    """
    Identifica o próximo processo pendente na pauta seguindo a ordem:
    1. Não pulados primeiro.
    2. Minutantes com maior volume de processos.
    3. Processos que não possuem status com 'eh_revisado=True'.
    """
    pauta = get_object_or_404(Pauta, pk=pauta_pk)

    # 1. Definir a Fila Pendente com as regras de prioridade
    # Filtramos para excluir qualquer processo que já tenha um status marcado como 'eh_revisado'
    proximo = pauta.revisoes.filter(
        ~Q(status__eh_revisado=True)
    ).ordenar_pela_prioridade().first()

    if not proximo:
        messages.success(request, "Não há processos pendentes para revisão nesta pauta.")
        return redirect('pautas:pauta', pk=pauta.pk)

    # 3. Redirecionar para a tela de revisão do primeiro encontrado
    return redirect('pautas:revisar_processo', pk=proximo.pk)


def relatorio_observacoes(request, pk):
    pauta = get_object_or_404(Pauta, pk=pk)
    
    # Aplicamos a ordenação customizada definida no models.py
    revisoes = pauta.revisoes.filter(
        observacoes__isnull=False
    ).distinct().ordenar_pela_prioridade().select_related(
        'processo', 
        'minutante__user'
    ).prefetch_related(
        'observacoes'
    )

    context = {
        'pauta': pauta,
        'revisoes': revisoes,
    }
    return render(request, 'pautas/relatorio_observacoes.html', context)