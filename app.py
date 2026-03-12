import streamlit as st
import datetime
import csv
import io
import json  # NOVO
import os    # NOVO
# Tentar importar biblioteca para gerar imagens
try:
    from PIL import Image, ImageDraw, ImageFont
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import requests

ARQUIVO_DADOS = 'banco_turno.json'

def get_jsonbin_config():
    """Tenta pegar as chaves do JSONBin nos Secrets do Streamlit"""
    try:
        # Quando estiver no Streamlit Cloud, ele vai pegar as variáveis daqui
        api_key = st.secrets["JSONBIN_API_KEY"]
        bin_id = st.secrets["JSONBIN_BIN_ID"]
        return api_key, bin_id
    except Exception:
        # Se falhar (ex: rodando local sem secrets.toml configurado), retorna None
        return None, None

def carregar_dados():
    """Lê os dados da nuvem (JSONBin) ou do arquivo físico local (Fallback)"""
    api_key, bin_id = get_jsonbin_config()

    # 1. TENTA LER DA NUVEM (JSONBIN)
    if api_key and bin_id:
        try:
            url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
            headers = {"X-Master-Key": api_key}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                # O JSONBin retorna os dados reais dentro da chave "record"
                dados = response.json().get("record", {})
                return dados
            else:
                st.sidebar.error(f"Erro ao ler da nuvem: {response.status_code}")
        except Exception as e:
            st.sidebar.error(f"Falha de conexão com a nuvem: {e}")

    # 2. SE NÃO TEM NUVEM (OU FALHOU), TENTA LER LOCAL
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    # Se nada existir, retorna a estrutura vazia padrão
    return {
        'fornecedores': {}, 'checklists_pendentes': [], 'divergencias': [],
        'pendencias_turno': "", 'paletes_inicio': 0, 'paletes_fim': 0,
        'veiculos_inicio': 0, 'veiculos_fim': 0,
        'carretas_inicio': "", 'carretas_fim': ""
    }

def salvar_dados():
    """Salva os dados na nuvem (JSONBin) e sempre faz um backup no arquivo local"""
    dados_para_salvar = {
        'fornecedores': st.session_state.get('fornecedores', {}),
        'checklists_pendentes': st.session_state.get('checklists_pendentes', []),
        'divergencias': st.session_state.get('divergencias', []),
        'pendencias_turno': st.session_state.get('pendencias_turno', ""),
        'paletes_inicio': st.session_state.get('paletes_inicio', 0),
        'paletes_fim': st.session_state.get('paletes_fim', 0),
        'veiculos_inicio': st.session_state.get('veiculos_inicio', 0),
        'veiculos_fim': st.session_state.get('veiculos_fim', 0),
        'carretas_inicio': st.session_state.get('carretas_inicio', ""),
        'carretas_fim': st.session_state.get('carretas_fim', "")
    }

    # 1. BACKUP LOCAL: Sempre salva localmente primeiro (por segurança)
    try:
        with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
            json.dump(dados_para_salvar, f, ensure_ascii=False, indent=4)
    except Exception:
        pass # Ignora erro local se não tiver permissão no SO

    # 2. SALVAR NA NUVEM (JSONBIN)
    api_key, bin_id = get_jsonbin_config()
    if api_key and bin_id:
        try:
            url = f"https://api.jsonbin.io/v3/b/{bin_id}"
            headers = {
                "Content-Type": "application/json",
                "X-Master-Key": api_key,
                "X-Bin-Versioning": "false" # Subescreve direto para poupar espaço
            }
            # Envia o dicionário inteiro como JSON para a nuvem
            requests.put(url, json=dados_para_salvar, headers=headers)
        except Exception as e:
            st.sidebar.error(f"Atenção: Os dados foram salvos localmente, mas falharam na nuvem ({e}).")

# Configuração da página para melhor visualização em dispositivos móveis
st.set_page_config(page_title="Passagem de Turno", page_icon="📦", layout="centered")

def init_session_state():
    dados_salvos = carregar_dados() # Busca os dados físicos

    # Injeta os dados físicos no session_state
    if 'fornecedores' not in st.session_state:
        st.session_state['fornecedores'] = dados_salvos.get('fornecedores', {})
    if 'checklists_pendentes' not in st.session_state:
        st.session_state['checklists_pendentes'] = dados_salvos.get('checklists_pendentes', [])
    if 'divergencias' not in st.session_state:
        st.session_state['divergencias'] = dados_salvos.get('divergencias', [])
    if 'pendencias_turno' not in st.session_state:
        st.session_state['pendencias_turno'] = dados_salvos.get('pendencias_turno', "")
    if 'paletes_inicio' not in st.session_state:
        st.session_state['paletes_inicio'] = dados_salvos.get('paletes_inicio', 0)
    if 'paletes_fim' not in st.session_state:
        st.session_state['paletes_fim'] = dados_salvos.get('paletes_fim', 0)
    if 'veiculos_inicio' not in st.session_state:
        st.session_state['veiculos_inicio'] = dados_salvos.get('veiculos_inicio', 0)
    if 'veiculos_fim' not in st.session_state:
        st.session_state['veiculos_fim'] = dados_salvos.get('veiculos_fim', 0)
    if 'carretas_inicio' not in st.session_state:
        st.session_state['carretas_inicio'] = dados_salvos.get('carretas_inicio', "")
    if 'carretas_fim' not in st.session_state:
        st.session_state['carretas_fim'] = dados_salvos.get('carretas_fim', "")

def main():
    # Garantimos que a memória (session_state) esteja configurada
    init_session_state()

    st.title("📦 Passagem de Turno")
    st.markdown("Preencha as informações durante o turno.")
    st.markdown("---")

    # Separamos as áreas usando Tabs para não ter rolagem infinita no celular
    # Isso deixa a interface limpa e focada em uma tarefa por vez
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚛 Fornecedores",
        "📝 Ckl. Pendentes",
        "⚠️ Divergências",
        "📌 Status Turno",
        "✅ Relatório Final"
    ])

    # ------------------
    # ABA 1: FORNECEDORES
    # ------------------
    with tab1:
        st.subheader("Fornecedores Descarregados")
        # Usamos st.form para agrupar os inputs e processar tudo de uma vez ao submeter
        with st.form("form_fornecedores", clear_on_submit=True):
            nome = st.text_input("Nome do Fornecedor").strip().title()
            transportadora = st.text_input("Transportadora").strip().upper()
            paletes = st.number_input("Quantidade de Paletes", min_value=0, step=1)
            checklists = st.number_input("Checklists Finalizados", min_value=0, step=1)

            # Botão com use_container_width=True para facilitar o clique no celular
            submit_fornecedores = st.form_submit_button("Adicionar Fornecedor", use_container_width=True)

            if submit_fornecedores:
                # Agora requer tanto o fornecedor como a transportadora
                if nome and transportadora:
                    # Chave de agrupamento passa a ser o combo Fornecedor + Transportadora
                    chave_agrupamento = f"{nome} - {transportadora}"

                    # SE já existe, soma. SENÃO, cria novo.
                    if chave_agrupamento in st.session_state['fornecedores']:
                        st.session_state['fornecedores'][chave_agrupamento]['paletes'] += paletes
                        st.session_state['fornecedores'][chave_agrupamento]['checklists'] += checklists
                    else:
                        st.session_state['fornecedores'][chave_agrupamento] = {
                            'fornecedor': nome,
                            'transportadora': transportadora,
                            'paletes': paletes,
                            'checklists': checklists
                        }
                    salvar_dados() # <--- ADICIONE ESTA LINHA AQUI
                    st.success(f"Fornecedor '{nome}' atualizado!")
                else:
                    st.error("Por favor, insira o nome do fornecedor e a transportadora.")

        # Mostra o que já foi salvo para garantir que o usuário acompanhe os registros
        if st.session_state['fornecedores']:
            st.markdown("### 📊 Resumo Atual")
            for chave, dados in list(st.session_state['fornecedores'].items()):
                col1, col2 = st.columns([4, 1])
                with col1:
                    forn = dados.get('fornecedor', chave) # Pega o fornecedor do dic, ou usa a chave como fallback
                    transp = dados.get('transportadora', 'N/I')
                    st.write(f"- **{forn} ({transp})**: {dados['paletes']} paletes | {dados['checklists']} checklists")
                with col2:
                    # Botão para excluir o fornecedor, usando a chave única de agrupamento
                    if st.button("❌", key=f"del_{chave}"):
                        del st.session_state['fornecedores'][chave]
                        salvar_dados() # <--- ADICIONE ESTA LINHA AQUI
                        st.rerun()

    # ------------------
    # ABA 2: CHECKLISTS PENDENTES
    # ------------------
    with tab2:
        st.subheader("Checklists Pendentes")
        with st.form("form_checklists", clear_on_submit=True):
            lote = st.text_input("Lote")
            codigo = st.text_input("Código")
            produto = st.text_input("Nome do Produto")

            submit_checklists = st.form_submit_button("Adicionar Pendência", use_container_width=True)
            if submit_checklists:
                if lote and codigo and produto:
                    st.session_state['checklists_pendentes'].append({
                        "Lote": lote,
                        "Código": codigo,
                        "Produto": produto
                    })
                    salvar_dados() # <--- ADICIONE ESTA LINHA AQUI
                    st.success("Checklist pendente adicionado à lista!")
                else:
                    st.error("Preencha todos os campos para adicionar.")

        if st.session_state['checklists_pendentes']:
            st.markdown("### 📋 Pendentes Atuais")
            for i, item in enumerate(st.session_state['checklists_pendentes']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{i+1}.** Cód: {item['Código']} | {item['Produto']} | Lote: {item['Lote']}")
                with col2:
                    if st.button("❌", key=f"del_ckl_{ i}"):
                        st.session_state['checklists_pendentes'].pop(i)
                        salvar_dados() # <--- ADICIONE ESTA LINHA AQUI
                        st.rerun()

    # ------------------
    # ABA 3: DIVERGÊNCIAS
    # ------------------
    with tab3:
        st.subheader("Registrar Divergência")
        with st.form("form_divergencias", clear_on_submit=True):
            lote_div = st.text_input("Lote (Divergência)")
            codigo_div = st.text_input("Código (Divergência)")
            produto_div = st.text_input("Nome do Produto")
            motivo_div = st.text_area("Motivo da Divergência")

            submit_divergencias = st.form_submit_button("Registrar Divergência", use_container_width=True)
            if submit_divergencias:
                if lote_div and codigo_div and produto_div and motivo_div:
                    st.session_state['divergencias'].append({
                        "Lote": lote_div,
                        "Código": codigo_div,
                        "Produto": produto_div,
                        "Motivo": motivo_div
                    })
                    salvar_dados() # <--- ADICIONE ESTA LINHA AQUI
                    st.success("Divergência registrada com sucesso!")
                else:
                    st.error("Preencha todos os campos da divergência.")

        if st.session_state['divergencias']:
            st.markdown("### ⚠️ Divergências Cadastradas")
            for i, item in enumerate(st.session_state['divergencias']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"- **Cód:** {item['Código']} | **{item['Produto']}** | **Lote:** {item['Lote']}")
                    st.write(f"  👉 *Motivo:* {item['Motivo']}")
                with col2:
                    if st.button("❌", key=f"del_div_{ i}"):
                        st.session_state['divergencias'].pop(i)
                        salvar_dados() # <--- ADICIONE ESTA LINHA AQUI
                        st.rerun()

    # ------------------
    # ABA 4: PENDÊNCIAS E STATUS DO TURNO
    # ------------------
    with tab4:
        st.subheader("Status do Pátio e Pendências")
        st.info("Registre a contagem de paletes, veículos aguardando, carretas e pendências gerais.")

        col_inicio, col_fim = st.columns(2)
        with col_inicio:
            p_inicio = st.number_input("Paletes no Chão (Início)", min_value=0, step=1, value=st.session_state['paletes_inicio'])
            v_inicio = st.number_input("Veículos Aguardando (Início)", min_value=0, step=1, value=st.session_state['veiculos_inicio'])
            # Transforma em textarea
            c_inicio = st.text_area("Carretas no Início (Nome da Transportadora - um por linha)", value=st.session_state['carretas_inicio'], height=100)
        with col_fim:
            p_fim = st.number_input("Paletes no Chão (Final)", min_value=0, step=1, value=st.session_state['paletes_fim'])
            v_fim = st.number_input("Veículos Aguardando (Final)", min_value=0, step=1, value=st.session_state['veiculos_fim'])
            c_fim = st.text_area("Carretas no Final (Nome da Transportadora - um por linha)", value=st.session_state['carretas_fim'], height=100)

        pendencias = st.text_area("Anotações Gerais (Pendências)", value=st.session_state['pendencias_turno'], height=150)

        if st.button("Salvar Status", use_container_width=True):
            st.session_state['paletes_inicio'] = p_inicio
            st.session_state['paletes_fim'] = p_fim
            st.session_state['veiculos_inicio'] = v_inicio
            st.session_state['veiculos_fim'] = v_fim
            st.session_state['carretas_inicio'] = c_inicio
            st.session_state['carretas_fim'] = c_fim
            st.session_state['pendencias_turno'] = pendencias
            salvar_dados() # <--- ADICIONE ESTA LINHA AQUI
            st.success("Status e anotações salvos!")

    # ------------------streamlit run app.py
    # ABA 5: GERAR RELATÓRIO
    # ------------------
    with tab5:
        st.subheader("Gerar Passagem de Turno")
        st.markdown("Revise as abas anteriores e clique no botão abaixo para consolidar seu relatório.")
        if st.button("🚀 Gerar e Copiar Relatório Final", type="primary", use_container_width=True):

            # Montando o relatório estruturado com emojis para o WhatsApp
            relatorio = "📋 *PASSAGEM DE TURNO - ALMOXARIFADO*\n\n"

            # BLOCO FORNECEDORES
            relatorio += "🚛 *FORNECEDORES DESCARREGADOS:*\n"
            if st.session_state['fornecedores']:
                total_paletes = sum(d['paletes'] for d in st.session_state['fornecedores'].values())
                total_checklists = sum(d['checklists'] for d in st.session_state['fornecedores'].values())
                for chave, d in st.session_state['fornecedores'].items():
                    forn = d.get('fornecedor', chave)
                    transp = d.get('transportadora', 'N/I')
                    relatorio += f"▫️ {forn} (Transp: {transp}): {d['paletes']} paletes | {d['checklists']} cklts Feitos\n"
                relatorio += f"**Total:** {total_paletes} paletes | {total_checklists} checklists Feitos\n\n"
            else:
                relatorio += "▫️ Nenhum fornecedor descarregado.\n\n"

            # BLOCO CHECKLISTS PENDENTES
            relatorio += "📝 *CHECKLISTS PENDENTES:*\n"
            if st.session_state['checklists_pendentes']:
                for item in st.session_state['checklists_pendentes']:
                    relatorio += f"▫️ Cód: {item['Código']} | {item['Produto']} | Lote: {item['Lote']}\n"
                relatorio += "\n"
            else:
                relatorio += "▫️ Nenhum checklist pendente.\n\n"

            # BLOCO DIVERGÊNCIAS
            relatorio += "⚠️ *DIVERGÊNCIAS:*\n"
            if st.session_state['divergencias']:
                for item in st.session_state['divergencias']:
                    relatorio += f"▫️ Cód: {item['Código']} | {item['Produto']} | Lote: {item['Lote']}\n"
                    relatorio += f"   👉 Motivo: {item['Motivo']}\n"
                relatorio += "\n"
            else:
                relatorio += "▫️ Nenhuma divergência registrada.\n\n"

            # Funções para contar carretas
            def conta_carretas(texto):
                # Conta quantas linhas preenchidas existem
                return len([l for l in str(texto).split('\n') if l.strip()])

            qtd_c_inicio = conta_carretas(st.session_state['carretas_inicio'])
            qtd_c_fim = conta_carretas(st.session_state['carretas_fim'])

            # BLOCO STATUS DO PÁTIO
            relatorio += "🏭 *STATUS DO PÁTIO:*\n"
            relatorio += f"▫️ Paletes no Chão\n"
            relatorio += f"   Início: {st.session_state['paletes_inicio']}\n"
            relatorio += f"   Final: {st.session_state['paletes_fim']}\n"
            relatorio += f"▫️ Veículos Aguardando\n"
            relatorio += f"   Início: {st.session_state['veiculos_inicio']}\n"
            relatorio += f"   Final: {st.session_state['veiculos_fim']}\n"
            relatorio += f"▫️ Carretas - Início do Turno ({qtd_c_inicio} Total)\n"
            if st.session_state['carretas_inicio'].strip():
                for c in str(st.session_state['carretas_inicio']).split('\n'):
                    if c.strip(): relatorio += f"   - {c.strip()}\n"
            else:
                relatorio += "   - Nenhuma carreta.\n"

            relatorio += f"▫️ Carretas - Final do Turno ({qtd_c_fim} Total)\n"
            if st.session_state['carretas_fim'].strip():
                for c in str(st.session_state['carretas_fim']).split('\n'):
                    if c.strip(): relatorio += f"   - {c.strip()}\n"
            else:
                relatorio += "   - Nenhuma carreta.\n\n"

            # BLOCO PENDÊNCIAS DO TURNO
            relatorio += "📌 *PENDÊNCIAS GERAIS DO TURNO:*\n"
            if st.session_state['pendencias_turno'].strip():
                relatorio += f"▫️ {st.session_state['pendencias_turno']}\n"
            else:
                relatorio += "▫️ Nenhuma pendência geral.\n"

            st.success("Relatório gerado com sucesso!")

            # Formatação mais "apresentável" em tela (estilo "Ticket")
            st.markdown("### 📝 Preview do Relatório")
            with st.container(border=True):
                st.markdown(relatorio)

            # Área de texto simples (fácil de selecionar tudo e copiar no celular)
            st.info("Para copiar: clique dentro da caixa abaixo, selecione tudo e copie.")
            st.text_area("Texto para WhatsApp:", value=relatorio, height=350)

            # Opção de Imagem PNG (Foto Premium Inspirada em Ticket/Relatório)
            if HAS_PIL:
                from PIL import Image, ImageDraw, ImageFont
                import datetime
                import textwrap
                import urllib.request
                import os

                # Definir Fuso Horário de Brasília (UTC-3)
                fuso_br = datetime.timezone(datetime.timedelta(hours=-3))

                # Vamos baixar fontes seguras (.ttf) que suportam acentuação latina perfeitamente (Noto Sans)
                # O problema dos "quadradinhos" nas letras acontecia pois a Roboto-Regular não continha os glifos usados (ex: ó, ã, í).
                def get_font(size, bold=False):
                    try:
                        font_name = "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"
                        font_url = f"https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/{font_name}"
                        font_path = font_name
                        if not os.path.exists(font_path):
                            urllib.request.urlretrieve(font_url, font_path)
                        return ImageFont.truetype(font_path, size)
                    except Exception:
                        return ImageFont.load_default()

                # Vamos dobrar a resolução original de todas as fontes para a imagem ficar em HD (Alta definição)
                # Multiplicador = 2x
                fonte_titulo_grande = get_font(72, bold=True)
                fonte_subtit = get_font(40, bold=False)
                fonte_secao = get_font(44, bold=True)
                fonte_label = get_font(32, bold=True)
                fonte_texto = get_font(32, bold=False)
                fonte_rodape = get_font(28, bold=False)

                # Paleta de Cores (Estilo Cimed: Amarelo e Preto)
                COR_CABE_FUNDO = (255, 215, 0)     # Amarelo Ouro Cimed mais vibrante p/ fundo cabeçalho e faixas de título
                COR_CABE_TEXTO = (20, 20, 20)      # Preto profundo pros textos dos títulos e destaques
                COR_AZUL_CLARO = (186, 221, 248)   # Fundo base do documento azul claro
                COR_BRANCO = (255, 255, 255)       # Quadro branco p/ textos
                COR_TEXTO_ESCURO = (30, 30, 30)    # Texto normal
                COR_CINZA_CLARO = (220, 220, 220)

                # Vamos preparar primeiro as sessões para calcular a altura total da imagem
                sessoes = []

                # 1. Fornecedores
                txt_forn = ""
                if st.session_state['fornecedores']:
                    for chave, d in st.session_state['fornecedores'].items():
                        forn = d.get('fornecedor', chave)
                        transp = d.get('transportadora', 'N/I')
                        txt_forn += f"• Fornecedor: {forn}\n  Transportadora: {transp}\n  Paletes: {d['paletes']} | Checklists: {d['checklists']}\n\n"
                else:
                    txt_forn += "Nenhum no turno.\n"
                sessoes.append(("FORNECEDORES DESCARREGADOS", txt_forn))

                # 2. Checklists
                txt_ckl = ""
                if st.session_state['checklists_pendentes']:
                    for item in st.session_state['checklists_pendentes']:
                        txt_ckl += f"• Cód {item['Código']} | {item['Produto']} | Lote: {item['Lote']}\n"
                else:
                    txt_ckl += "Nenhum pendente.\n"
                sessoes.append(("CHECKLISTS PENDENTES", txt_ckl))

                # 3. Divergências
                txt_div = ""
                if st.session_state['divergencias']:
                    for item in st.session_state['divergencias']:
                        txt_div += f"• Cód {item['Código']} | {item['Produto']} | Lote: {item['Lote']}\n"
                        # Wrap do motivo (para caber na largura HD)
                        m_wrap = textwrap.wrap(f"  > Motivo: {item['Motivo']}", width=110)
                        txt_div += "\n".join(m_wrap) + "\n\n"
                else:
                    txt_div += "Nenhuma.\n"
                sessoes.append(("DIVERGÊNCIAS", txt_div))

                # 4. Pendências e Pátio
                txt_pen = f"• Paletes no Chão:\n"
                txt_pen += f"  Inicio: {st.session_state['paletes_inicio']}\n"
                txt_pen += f"  Final: {st.session_state['paletes_fim']}\n\n"
                txt_pen += f"• Veículos Aguardando:\n"
                txt_pen += f"  Inicio: {st.session_state['veiculos_inicio']}\n"
                txt_pen += f"  Final: {st.session_state['veiculos_fim']}\n\n"

                txt_pen += f"• Carretas no Início do Turno ({qtd_c_inicio} no total):\n"
                if st.session_state['carretas_inicio'].strip():
                    for c in str(st.session_state['carretas_inicio']).split('\n'):
                        if c.strip(): txt_pen += f"  - {c.strip()}\n"
                else:
                    txt_pen += "  (Nenhuma)\n"

                txt_pen += f"\n• Carretas no Final do Turno ({qtd_c_fim} no total):\n"
                if st.session_state['carretas_fim'].strip():
                    for c in str(st.session_state['carretas_fim']).split('\n'):
                        if c.strip(): txt_pen += f"  - {c.strip()}\n"
                else:
                    txt_pen += "  (Nenhuma)\n"

                if st.session_state['pendencias_turno'].strip():
                    txt_pen += f"\n• Anotações Gerais:\n"
                    # Wrap do texto livre
                    anotacoes = st.session_state['pendencias_turno'].split('\n')
                    for linha in anotacoes:
                        txt_pen += "\n".join(textwrap.wrap(linha, width=80)) + "\n"
                sessoes.append(("STATUS DO PÁTIO E ANOTAÇÕES", txt_pen))

                # Cálculo de Altura de conteúdo
                altura_conteudo = 0
                linhas_sessao = []
                for titulo_sessao, texto_sessao in sessoes:
                    linhas = texto_sessao.strip().split('\n')
                    linhas_sessao.append((titulo_sessao, linhas))
                    # Matemática ajustada para resolução 2x (HD)
                    altura_conteudo += 280 + (len(linhas) * 52)

                # Dobramos todas as proporções fixas do layout
                altura_total = 500 + altura_conteudo + 200 # Cabeçalho(500) + conteudo + Rodape aumentado(200)
                LARGURA_IMG = 1700

                # Crianção do Canvas e Contexto
                img = Image.new('RGB', (LARGURA_IMG, altura_total), color=COR_AZUL_CLARO)
                d = ImageDraw.Draw(img)

                # ===============================
                # DESENHANDO CABEÇALHO SUPERIOR (Amarelo)
                # ===============================
                d.rectangle([(0, 0), (LARGURA_IMG, 280)], fill=COR_CABE_FUNDO)

                # Textos cabeçalho - preto nos títulos
                centro_x = LARGURA_IMG // 2
                agora = datetime.datetime.now(fuso_br)
                d.text((80, 80), "ALMOXARIFADO", fill=COR_CABE_TEXTO, font=fonte_secao)
                d.text((centro_x, 60), "Passagem de Turno", fill=COR_CABE_TEXTO, font=fonte_titulo_grande, anchor="ma")
                d.text((centro_x, 160), "RELATÓRIO DIÁRIO DE ATIVIDADES", fill=COR_CABE_TEXTO, font=fonte_subtit, anchor="ma")
                d.text((LARGURA_IMG - 80, 80), f"Gerado em: {agora.strftime('%d/%m/%Y %H:%M')}", fill=COR_CABE_TEXTO, font=fonte_rodape, anchor="ra")

                # Faixa Info (Cápsulas brancas estilo Forms debaixo do cabeçalho)
                y_capsula = 320

                # Caixas redesenhadas perfeitamente para suportar textos HD de canto a canto
                try:
                    d.rounded_rectangle([(60, y_capsula), (780, y_capsula+90)], fill=COR_BRANCO, radius=16)     # Dia da Semana (amplo)
                    d.rounded_rectangle([(810, y_capsula), (1330, y_capsula+90)], fill=COR_BRANCO, radius=16)   # Horário de Geração
                    d.rounded_rectangle([(1360, y_capsula), (LARGURA_IMG-60, y_capsula+90)], fill=COR_BRANCO, radius=16) # Sistema WebApp
                except AttributeError:
                    d.rectangle([(60, y_capsula), (780, y_capsula+90)], fill=COR_BRANCO)
                    d.rectangle([(810, y_capsula), (1330, y_capsula+90)], fill=COR_BRANCO)
                    d.rectangle([(1360, y_capsula), (LARGURA_IMG-60, y_capsula+90)], fill=COR_BRANCO)

                # Traduzir dia da semana manualmente para não depender de locale do OS
                dias_pt = ["DOMINGO", "SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA", "SÁBADO"]
                dia_semana_str = dias_pt[int(agora.strftime('%w'))]
                hora_str = agora.strftime('%H:%M')

                # Centralizando textos dentro das caixas
                d.text((90, y_capsula+24), f"Dia da Semana: ", fill=COR_CABE_TEXTO, font=fonte_label)
                tam1 = d.textlength("Dia da Semana: ", font=fonte_label)
                d.text((90 + tam1, y_capsula+24), dia_semana_str, fill=COR_TEXTO_ESCURO, font=fonte_texto)

                d.text((840, y_capsula+24), f"Horário de Geração: ", fill=COR_CABE_TEXTO, font=fonte_label)
                tam2 = d.textlength("Horário de Geração: ", font=fonte_label)
                d.text((840 + tam2, y_capsula+24), hora_str, fill=COR_TEXTO_ESCURO, font=fonte_texto)

                d.text((1390, y_capsula+24), "Sistema: ", fill=COR_CABE_TEXTO, font=fonte_label)
                tam3 = d.textlength("Sistema: ", font=fonte_label)
                d.text((1390 + tam3, y_capsula+24), "Web App", fill=COR_TEXTO_ESCURO, font=fonte_texto)

                # ===============================
                # DESENHANDO SESSÕES E LISTAS (HD)
                # ===============================
                y_atual = 480
                margem_esquerda = 80
                largura_quadro = LARGURA_IMG - (margem_esquerda*2)

                for titulo, linhas_texto in linhas_sessao:
                    # Bloco Fundo da sessão (branco) com mais padding pra ficar espaçoso
                    altura_bloco_texto = 60 + (len(linhas_texto) * 52) + 60
                    # Sombras / Borda Retângulo Banco
                    d.rectangle([(margem_esquerda, y_atual + 80), (margem_esquerda + largura_quadro, y_atual + 80 + altura_bloco_texto)], fill=COR_BRANCO)

                    # Faixa Titulo da Sessão (Amarelo)
                    d.rectangle([(margem_esquerda, y_atual), (margem_esquerda + largura_quadro, y_atual + 80)], fill=COR_CABE_FUNDO)
                    # Titulo da Barra em Preto Escuro
                    d.text((margem_esquerda + 40, y_atual + 16), titulo, fill=COR_CABE_TEXTO, font=fonte_secao)

                    # Imprimir as linhas de texto
                    y_texto_interno = y_atual + 130
                    for linha in linhas_texto:
                        if ":" in linha and not linha.startswith(" "):
                            partes = linha.split(":", 1)
                            # Desenha parte antes dos ":" com fonte bold e depois normal
                            d.text((margem_esquerda + 40, y_texto_interno), partes[0] + ":", fill=COR_CABE_TEXTO, font=fonte_label)
                            tam_label = d.textlength(partes[0] + ": ", font=fonte_label)
                            d.text((margem_esquerda + 40 + tam_label, y_texto_interno), partes[1], fill=COR_TEXTO_ESCURO, font=fonte_texto)
                        elif "Total" in linha or "Total:" in linha:
                            # Se for total, deixa todo o título em bold
                            d.text((margem_esquerda + 40, y_texto_interno), linha, fill=COR_CABE_TEXTO, font=fonte_label)
                        else:
                            d.text((margem_esquerda + 40, y_texto_interno), linha, fill=COR_TEXTO_ESCURO, font=fonte_texto)

                        y_texto_interno += 52 # Um pouco mais de espaço entre as linhas

                    y_atual += 80 + altura_bloco_texto + 80 # Avança mais espaçado para prxs sessão

                # Base (Assinatura do sistema)
                try:
                    d.rounded_rectangle([(margem_esquerda, altura_total-120), (LARGURA_IMG-margem_esquerda, altura_total-40)], fill=COR_BRANCO, radius=20)
                except AttributeError:
                    d.rectangle([(margem_esquerda, altura_total-120), (LARGURA_IMG-margem_esquerda, altura_total-40)], fill=COR_BRANCO)

                d.text((margem_esquerda + 40, altura_total-90), "Relatório submetido via App Passagem de Turno Almoxarifado ©", fill=COR_TEXTO_ESCURO, font=fonte_rodape)

                # Finaliza Imagem
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()

                st.markdown("---")
                st.download_button(
                    label="� Baixar Relatório (Foto de Alta Qualidade)",
                    data=byte_im,
                    file_name=f"Relatorio_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.png",
                    mime="image/png",
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.warning("A geração da Foto (PNG) requer no seu computador o pacote `pillow`. Pare o terminal e digite: `pip install pillow`")

            # --- Gerador CSV ---
            # Independentemente de ter PIL ou não, geramos o CSV
            st.markdown("### 📊 Banco de Dados (Excel)")
            st.info("Exporte os dados deste turno em tabela para alimentar suas planilhas de controle.")

            output_csv = io.StringIO()
            # Usando delimitador ';' padrão de Excel brasileiro
            writer = csv.writer(output_csv, delimiter=';')
            writer.writerow(['Data_Geração', 'Sessão', 'Identificação (Fornec/Cód)', 'Transportadora', 'Produto_Nome', 'Lote', 'Qtd_Paletes', 'Checklists_Feitos', 'Anotações_Motivos'])

            data_hora_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

            for chave, d in st.session_state['fornecedores'].items():
                forn = d.get('fornecedor', chave)
                transp = d.get('transportadora', 'N/I')
                writer.writerow([data_hora_str, 'FORNECEDOR', forn, transp, '', '', d['paletes'], d['checklists'], ''])

            for item in st.session_state['checklists_pendentes']:
                writer.writerow([data_hora_str, 'CHECKLIST_PENDENTE', item['Código'], '', item['Produto'], item['Lote'], '', '', ''])

            for item in st.session_state['divergencias']:
                writer.writerow([data_hora_str, 'DIVERGENCIA', item['Código'], '', item['Produto'], item['Lote'], '', '', item['Motivo']])

            status_str = f"Paletes(Inicio: {st.session_state['paletes_inicio']} | Fim: {st.session_state['paletes_fim']}) --- Veiculos(Inicio: {st.session_state['veiculos_inicio']} | Fim: {st.session_state['veiculos_fim']})"
            writer.writerow([data_hora_str, 'STATUS_PATIO', '', '', '', '', '', status_str])

            if st.session_state['pendencias_turno'].strip():
                anots = st.session_state['pendencias_turno'].replace('\n', ' // ')
                writer.writerow([data_hora_str, 'ANOTACOES_GERAIS', '', '', '', '', '', anots])

            # Codificação utf-8-sig para Microsoft Excel ler os acentos perfeitamente no formato CSV
            csv_data = output_csv.getvalue().encode('utf-8-sig')

            st.download_button(
                label="📊 Baixar Planilha de Dados (.CSV)",
                data=csv_data,
                file_name=f"BD_Turno_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.markdown("---")
            st.markdown("### 🛑 Encerrar Turno")
            if st.button("Apagar Dados e Iniciar Novo Turno", type="secondary", use_container_width=True):
                # Zera o arquivo físico apagando ele
                if os.path.exists(ARQUIVO_DADOS):
                    os.remove(ARQUIVO_DADOS)

                # Zera na Nuvem mandando estrutura vazia
                api_key, bin_id = get_jsonbin_config()
                if api_key and bin_id:
                    vazio = {
                        'fornecedores': {}, 'checklists_pendentes': [], 'divergencias': [],
                        'pendencias_turno': "", 'paletes_inicio': 0, 'paletes_fim': 0,
                        'veiculos_inicio': 0, 'veiculos_fim': 0,
                        'carretas_inicio': "", 'carretas_fim': ""
                    }
                    try:
                        url = f"https://api.jsonbin.io/v3/b/{bin_id}"
                        headers = {"Content-Type": "application/json", "X-Master-Key": api_key, "X-Bin-Versioning": "false"}
                        requests.put(url, json=vazio, headers=headers)
                    except:
                        pass # ignora falha na rede

                # Força o recarregamento da página (ele vai criar tudo vazio de novo)
                st.session_state.clear()
                st.rerun()

if __name__ == "__main__":
    main()
