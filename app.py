import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Usuários e senhas 
usuarios = {
    "admin": make_hashes("Admin@2024!"),
    "vendedor": make_hashes("Vendas@123")
}

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username in usuarios and check_hashes(password, usuarios[username]):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.sidebar.success(f"Bem-vindo, {username}!")
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha inválidos")
    return False

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🚀 SISTEMA PRINCIPAL - CORRIGIDO
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.write(f"👤 Usuário: **{st.session_state.username}**")

# Inicialização dos dados
if 'pedidos' not in st.session_state:
    st.session_state.pedidos = []
if 'clientes' not in st.session_state:
    st.session_state.clientes = []
if 'produtos' not in st.session_state:
    st.session_state.produtos = []
if 'escolas' not in st.session_state:
    st.session_state.escolas = ["Municipal", "Desperta", "São Tadeu"]

# CONFIGURAÇÕES ESPECÍFICAS - TAMANHOS CORRETOS
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

# VÍNCULO ENTRE ESCOLAS E TAMANHOS - CORRIGIDO
escolas_config = {
    "Municipal": {
        "tamanhos_preferidos": ["2", "4", "6", "8", "10", "12", "P", "M", "G", "GG"],
        "cores_preferidas": ["Branco", "Azul Marinho", "Cinza"]
    },
    "Desperta": {
        "tamanhos_preferidos": ["2", "4", "6", "8", "10", "12", "PP"],
        "cores_preferidas": ["Branco", "Verde", "Preto"]
    },
    "São Tadeu": {
        "tamanhos_preferidos": ["2", "4", "6", "8", "10", "12", "P"],
        "cores_preferidas": ["Branco", "Vermelho", "Azul Royal"]
    }
}

# PRODUTOS REAIS
tipos_camisetas = [
    "Camiseta Básica", 
    "Camiseta Regata", 
    "Camiseta Manga Longa"
]

tipos_calcas = [
    "Calça Jeans",
    "Calça Tactel", 
    "Calça Moletom",
    "Bermuda",
    "Short",
    "Short Saia"
]

tipos_agasalhos = [
    "Blusão",
    "Moletom"
]

# Funções auxiliares
def salvar_dados():
    dados = {
        'pedidos': st.session_state.pedidos,
        'clientes': st.session_state.clientes,
        'produtos': st.session_state.produtos
    }
    with open('dados.json', 'w') as f:
        json.dump(dados, f)

def carregar_dados():
    if os.path.exists('dados.json'):
        with open('dados.json', 'r') as f:
            dados = json.load(f)
            st.session_state.pedidos = dados.get('pedidos', [])
            st.session_state.clientes = dados.get('clientes', [])
            st.session_state.produtos = dados.get('produtos', [])

carregar_dados()

# =========================================
# 🎨 NAVEGAÇÃO CORRIGIDA - FUNCIONAL
# =========================================

st.sidebar.title("👕 Sistema de Fardamentos")

# Menu na sidebar - CORRIGIDO
menu = st.sidebar.radio(
    "Navegação",
    ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Fardamentos", "📦 Estoque", "📈 Relatórios"]
)

# HEADER DINÂMICO
if menu == "📊 Dashboard":
    st.title("📊 Dashboard - Visão Geral")
elif menu == "📦 Pedidos":
    st.title("📦 Gestão de Pedidos") 
elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
elif menu == "👕 Fardamentos":
    st.title("👕 Gestão de Fardamentos")
elif menu == "📦 Estoque":
    st.title("📦 Controle de Estoque")
elif menu == "📈 Relatórios":
    st.title("📈 Relatórios Detalhados")

st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA - CORRIGIDAS
# =========================================

# DASHBOARD
if menu == "📊 Dashboard":
    st.header("🎯 Métricas em Tempo Real")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = len(st.session_state.pedidos)
        st.metric("Total de Pedidos", total_pedidos)
    
    with col2:
        pedidos_pendentes = len([p for p in st.session_state.pedidos if p['status'] == 'Pendente'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        clientes_ativos = len(st.session_state.clientes)
        st.metric("Clientes Ativos", clientes_ativos)
    
    with col4:
        produtos_baixo_estoque = len([p for p in st.session_state.produtos if p.get('estoque', 0) < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque, delta=-produtos_baixo_estoque)
    
    # Cards de Ação Rápida
    st.header("🚀 Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.success("Vá para a aba '📦 Pedidos' para cadastrar um novo pedido!")
    
    with col2:
        if st.button("➕ Novo Cliente", use_container_width=True):
            st.success("Vá para a aba '👥 Clientes' para cadastrar um novo cliente!")
    
    with col3:
        if st.button("👕 Novo Fardamento", use_container_width=True):
            st.success("Vá para a aba '👕 Fardamentos' para cadastrar um novo fardamento!")
    
    # Seção de Alertas
    st.header("⚠️ Alertas de Estoque")
    produtos_alerta = [p for p in st.session_state.produtos if p.get('estoque', 0) < 5]
    
    if produtos_alerta:
        for produto in produtos_alerta:
            st.warning(f"🚨 {produto['nome']} - Tamanho: {produto.get('tamanho', 'N/A')} - Estoque: {produto.get('estoque', 0)} unidades")
    else:
        st.success("✅ Nenhum alerta de estoque no momento")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Vendas por Escola")
        if st.session_state.pedidos:
            df_vendas = pd.DataFrame(st.session_state.pedidos)
            vendas_por_escola = df_vendas['escola'].value_counts()
            fig = px.bar(vendas_por_escola, title="Vendas por Escola")
            st.plotly_chart(fig)
        else:
            st.info("📋 Nenhum pedido cadastrado ainda")
    
    with col2:
        st.subheader("🎯 Status dos Pedidos")
        if st.session_state.pedidos:
            df_vendas = pd.DataFrame(st.session_state.pedidos)
            vendas_status = df_vendas['status'].value_counts()
            fig = px.pie(vendas_status, values=vendas_status.values, 
                        names=vendas_status.index, title="Distribuição por Status")
            st.plotly_chart(fig)
        else:
            st.info("📋 Nenhum pedido para analisar")

# PEDIDOS
elif menu == "📦 Pedidos":
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Novo Pedido", "📋 Listar Pedidos", "🔄 Alterar Status", "✏️ Editar Pedido"])
    
    with tab1:
        st.header("📝 Novo Pedido de Fardamento")
        
        # Dados do cliente
        if st.session_state.clientes:
            cliente_selecionado = st.selectbox("Cliente", 
                [f"{c['nome']} - {c['escola']}" for c in st.session_state.clientes])
            
            if cliente_selecionado:
                escola_cliente = cliente_selecionado.split(' - ')[1]
                st.success(f"🏫 Escola: {escola_cliente}")
                
                # Mostrar tamanhos da escola
                if escola_cliente in escolas_config:
                    tamanhos_escola = escolas_config[escola_cliente]["tamanhos_preferidos"]
                    st.info(f"📏 Tamanhos desta escola: {', '.join(tamanhos_escola)}")
        else:
            st.warning("👥 Cadastre clientes primeiro!")
            cliente_selecionado = None
            escola_cliente = None
        
        # Produtos filtrados pela escola
        if st.session_state.produtos and cliente_selecionado:
            # Filtro por tipo
            tipo_filtro = st.selectbox("🔍 Filtrar por tipo:", 
                ["Todos", "Camisetas", "Calças/Shorts", "Agasalhos"])
            
            produtos_filtrados = st.session_state.produtos
            
            # Aplicar filtro de tipo
            if tipo_filtro != "Todos":
                if tipo_filtro == "Camisetas":
                    produtos_filtrados = [p for p in produtos_filtrados if any(tipo in p['nome'] for tipo in tipos_camisetas)]
                elif tipo_filtro == "Calças/Shorts":
                    produtos_filtrados = [p for p in produtos_filtrados if any(tipo in p['nome'] for tipo in tipos_calcas)]
                elif tipo_filtro == "Agasalhos":
                    produtos_filtrados = [p for p in produtos_filtrados if any(tipo in p['nome'] for tipo in tipos_agasalhos)]
            
            # Filtrar por tamanhos da escola
            if escola_cliente in escolas_config:
                tamanhos_preferidos = escolas_config[escola_cliente]["tamanhos_preferidos"]
                produtos_filtrados = [p for p in produtos_filtrados if p.get('tamanho') in tamanhos_preferidos]
            
            produtos_disponiveis = [p for p in produtos_filtrados if p.get('estoque', 0) > 0]
            
            if produtos_disponiveis:
                produto_selecionado = st.selectbox("👕 Selecione o fardamento", 
                    [f"{p['nome']} - Tamanho: {p.get('tamanho', 'Único')} - Cor: {p.get('cor', 'N/A')} - R${p['preco']:.2f} - Estoque: {p.get('estoque', 0)}" 
                     for p in produtos_disponiveis])
                quantidade = st.number_input("🔢 Quantidade", min_value=1, value=1)
            else:
                st.error("❌ Nenhum fardamento disponível com estoque!")
                produto_selecionado = None
                quantidade = 0
        else:
            if not cliente_selecionado:
                st.warning("👥 Selecione um cliente primeiro!")
            else:
                st.warning("👕 Cadastre fardamentos primeiro!")
            produto_selecionado = None
            quantidade = 0
        
        data_entrega = st.date_input("📅 Data de Entrega Prevista")
        observacoes = st.text_area("📝 Observações", placeholder="Cor específica, detalhes, etc...")
        
        if st.button("✅ Cadastrar Pedido", type="primary") and cliente_selecionado and produto_selecionado:
            novo_pedido = {
                'id': len(st.session_state.pedidos) + 1,
                'cliente': cliente_selecionado.split(' - ')[0],
                'escola': cliente_selecionado.split(' - ')[1],
                'produto': produto_selecionado.split(' - ')[0],
                'tamanho': produto_selecionado.split('Tamanho: ')[1].split(' - ')[0],
                'cor': produto_selecionado.split('Cor: ')[1].split(' - ')[0],
                'quantidade': quantidade,
                'preco_unitario': float(produto_selecionado.split('R$')[1].split(' - ')[0]),
                'data_pedido': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'data_entrega_prevista': data_entrega.strftime("%d/%m/%Y"),
                'status': 'Pendente',
                'observacoes': observacoes
            }
            
            # Atualizar estoque
            produto_nome = produto_selecionado.split(' - ')[0]
            produto_tamanho = produto_selecionado.split('Tamanho: ')[1].split(' - ')[0]
            for produto in st.session_state.produtos:
                if produto['nome'] == produto_nome and produto.get('tamanho') == produto_tamanho:
                    produto['estoque'] -= quantidade
                    break
            
            st.session_state.pedidos.append(novo_pedido)
            salvar_dados()
            st.success("🎉 Pedido cadastrado com sucesso!")
            st.balloons()
    
    with tab2:
        st.header("📋 Lista de Pedidos")
        if st.session_state.pedidos:
            df_pedidos = pd.DataFrame(st.session_state.pedidos)
            df_pedidos = df_pedidos.sort_values('id', ascending=False)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                status_filtro = st.multiselect("🔍 Filtrar por status:", 
                    options=df_pedidos['status'].unique(),
                    default=df_pedidos['status'].unique())
            with col2:
                escola_filtro = st.multiselect("🏫 Filtrar por escola:",
                    options=df_pedidos['escola'].unique(),
                    default=df_pedidos['escola'].unique())
            
            df_filtrado = df_pedidos[
                (df_pedidos['status'].isin(status_filtro)) & 
                (df_pedidos['escola'].isin(escola_filtro))
            ]
            
            st.dataframe(df_filtrado, use_container_width=True)
            st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df_pedidos)} pedidos")
        else:
            st.info("📋 Nenhum pedido cadastrado")
    
    with tab3:
        st.header("🔄 Alterar Status do Pedido")
        if st.session_state.pedidos:
            pedido_selecionado = st.selectbox("📦 Selecione o pedido", 
                [f"ID: {p['id']} - {p['cliente']} - {p['produto']} - Status: {p['status']}" for p in st.session_state.pedidos])
            
            novo_status = st.selectbox("🎯 Novo Status", 
                ["Pendente", "Cortando", "Costurando", "Pronto", "Entregue", "Cancelado"])
            
            if st.button("🔄 Atualizar Status", type="primary"):
                pedido_id = int(pedido_selecionado.split(' - ')[0].replace('ID: ', ''))
                for pedido in st.session_state.pedidos:
                    if pedido['id'] == pedido_id:
                        pedido['status'] = novo_status
                        break
                salvar_dados()
                st.success("✅ Status atualizado com sucesso!")
        else:
            st.info("📋 Nenhum pedido cadastrado")
    
    with tab4:
        st.header("✏️ Editar Pedido")
        if st.session_state.pedidos:
            pedido_editar = st.selectbox("📦 Selecione o pedido para editar", 
                [f"ID: {p['id']} - {p['cliente']} - {p['produto']}" for p in st.session_state.pedidos],
                key="editar_pedido")
            
            if pedido_editar:
                pedido_id = int(pedido_editar.split(' - ')[0].replace('ID: ', ''))
                pedido = next((p for p in st.session_state.pedidos if p['id'] == pedido_id), None)
                
                if pedido:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**👕 Produto:** {pedido['produto']}")
                        st.write(f"**📏 Tamanho:** {pedido.get('tamanho', 'N/A')}")
                        nova_quantidade = st.number_input("🔢 Nova Quantidade", 
                            min_value=1, value=pedido['quantidade'], key="qtd_edit")
                    with col2:
                        nova_data = st.date_input("📅 Nova Data de Entrega", 
                            value=datetime.strptime(pedido['data_entrega_prevista'], "%d/%m/%Y"),
                            key="data_edit")
                        novas_observacoes = st.text_area("📝 Novas Observações", 
                            value=pedido['observacoes'], key="obs_edit")
                    
                    if st.button("💾 Salvar Alterações", type="primary"):
                        # Reverter estoque antigo e aplicar novo
                        produto_antigo = next((p for p in st.session_state.produtos 
                            if p['nome'] == pedido['produto'] and p.get('tamanho') == pedido.get('tamanho')), None)
                        
                        if produto_antigo:
                            diferenca = nova_quantidade - pedido['quantidade']
                            produto_antigo['estoque'] -= diferenca
                            
                            if produto_antigo['estoque'] < 0:
                                st.error("❌ Estoque insuficiente para esta quantidade!")
                                produto_antigo['estoque'] += diferenca
                            else:
                                pedido['quantidade'] = nova_quantidade
                                pedido['data_entrega_prevista'] = nova_data.strftime("%d/%m/%Y")
                                pedido['observacoes'] = novas_observacoes
                                salvar_dados()
                                st.success("✅ Pedido atualizado com sucesso!")
                        else:
                            st.error("❌ Produto não encontrado no estoque")
        else:
            st.info("📋 Nenhum pedido cadastrado")

# CLIENTES
elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        nome_cliente = st.text_input("👤 Nome do Cliente")
        escola_cliente = st.selectbox("🏫 Escola", st.session_state.escolas)
        telefone = st.text_input("📞 Telefone (WhatsApp)")
        email = st.text_input("📧 Email (opcional)")
        
        # Mostrar configurações da escola selecionada
        if escola_cliente in escolas_config:
            st.success("🎯 Configuração da Escola:")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**📏 Tamanhos:** {', '.join(escolas_config[escola_cliente]['tamanhos_preferidos'])}")
            with col2:
                st.write(f"**🎨 Cores:** {', '.join(escolas_config[escola_cliente]['cores_preferidas'])}")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome_cliente:
                novo_cliente = {
                    'nome': nome_cliente,
                    'escola': escola_cliente,
                    'telefone': telefone,
                    'email': email,
                    'data_cadastro': datetime.now().strftime("%d/%m/%Y")
                }
                st.session_state.clientes.append(novo_cliente)
                salvar_dados()
                st.success("✅ Cliente cadastrado com sucesso!")
            else:
                st.error("❌ Nome do cliente é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        if st.session_state.clientes:
            df_clientes = pd.DataFrame(st.session_state.clientes)
            
            # Estatísticas por escola
            st.subheader("📊 Distribuição por Escola")
            clientes_por_escola = df_clientes['escola'].value_counts()
            fig = px.pie(clientes_por_escola, values=clientes_por_escola.values, 
                        names=clientes_por_escola.index, title="Clientes por Escola")
            st.plotly_chart(fig)
            
            st.dataframe(df_clientes, use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")

# FARDAMENTOS - COM CAMPO ESCOLA
elif menu == "👕 Fardamentos":
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Fardamento", "📋 Listar Fardamentos", "✏️ Editar Fardamento"])
    
    with tab1:
        st.header("➕ Novo Fardamento")
        
        # Categoria principal
        categoria_principal = st.selectbox("📦 Tipo de Fardamento", 
            ["Camisetas", "Calças/Shorts", "Agasalhos"])
        
        # NOVO CAMPO: ESCOLA DO FARDAMENTO
        escola_fardamento = st.selectbox("🏫 Escola do Fardamento", st.session_state.escolas)
        
        # Detalhes específicos por categoria
        if categoria_principal == "Camisetas":
            nome_produto = st.selectbox("👕 Modelo de Camiseta", tipos_camisetas)
            preco_sugerido = 29.90
        elif categoria_principal == "Calças/Shorts":
            nome_produto = st.selectbox("🩳 Modelo", tipos_calcas)
            preco_sugerido = 49.90
        else:  # Agasalhos
            nome_produto = st.selectbox("🧥 Modelo de Agasalho", tipos_agasalhos)
            preco_sugerido = 79.90
        
        # TAMANHOS COMPLETOS - FILTRADOS PELA ESCOLA
        st.subheader("📏 Seleção de Tamanho")
        
        # Mostrar apenas tamanhos da escola selecionada
        if escola_fardamento in escolas_config:
            tamanhos_escola = escolas_config[escola_fardamento]["tamanhos_preferidos"]
            st.info(f"🎯 Tamanhos disponíveis para {escola_fardamento}: {', '.join(tamanhos_escola)}")
            tamanho_selecionado = st.selectbox("Selecione o tamanho:", tamanhos_escola)
        else:
            tamanho_selecionado = st.selectbox("Selecione o tamanho:", todos_tamanhos)
        
        # Campos comuns
        cor = st.text_input("🎨 Cor Principal", value="Branco")
        preco_produto = st.number_input("💰 Preço (R$)", min_value=0.0, step=0.01, value=preco_sugerido)
        estoque_inicial = st.number_input("📦 Estoque Inicial", min_value=0, value=10)
        descricao = st.text_area("📝 Descrição Adicional", placeholder="Gola V, malha fria, etc...")
        
        if st.button("✅ Cadastrar Fardamento", type="primary"):
            if nome_produto and tamanho_selecionado:
                novo_produto = {
                    'nome': nome_produto,
                    'categoria': categoria_principal,
                    'escola': escola_fardamento,  # NOVO CAMPO
                    'tamanho': tamanho_selecionado,
                    'cor': cor,
                    'preco': preco_produto,
                    'estoque': estoque_inicial,
                    'descricao': descricao,
                    'data_cadastro': datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.session_state.produtos.append(novo_produto)
                salvar_dados()
                st.success("✅ Fardamento cadastrado com sucesso!")
                st.balloons()
            else:
                st.error("❌ Preencha todos os campos obrigatórios!")
    
    with tab2:
        st.header("📋 Fardamentos Cadastrados")
        if st.session_state.produtos:
            df_produtos = pd.DataFrame(st.session_state.produtos)
            
            # Filtros
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                cat_filtro = st.selectbox("🔍 Filtrar por categoria:", 
                    ["Todas"] + list(df_produtos['categoria'].unique()))
            with col2:
                escola_filtro = st.selectbox("🏫 Filtrar por escola:",
                    ["Todas"] + list(df_produtos['escola'].unique()))
            with col3:
                tamanho_filtro = st.selectbox("📏 Filtrar por tamanho:",
                    ["Todos"] + list(df_produtos['tamanho'].unique()))
            with col4:
                cor_filtro = st.selectbox("🎨 Filtrar por cor:",
                    ["Todas"] + list(df_produtos['cor'].unique()))
            
            df_filtrado = df_produtos
            if cat_filtro != "Todas":
                df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_filtro]
            if escola_filtro != "Todas":
                df_filtrado = df_filtrado[df_filtrado['escola'] == escola_filtro]
            if tamanho_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['tamanho'] == tamanho_filtro]
            if cor_filtro != "Todas":
                df_filtrado = df_filtrado[df_filtrado['cor'] == cor_filtro]
            
            st.dataframe(df_filtrado, use_container_width=True)
            st.info(f"📊 Mostrando {len(df_filtrado)} de {len(df_produtos)} fardamentos")
        else:
            st.info("👕 Nenhum fardamento cadastrado")
    
    with tab3:
        st.header("✏️ Editar Fardamento")
        if st.session_state.produtos:
            produto_editar = st.selectbox("👕 Selecione o fardamento para editar", 
                [f"{p['nome']} - Escola: {p.get('escola', 'N/A')} - Tamanho: {p.get('tamanho', 'Único')} - Cor: {p.get('cor', 'N/A')} - Estoque: {p.get('estoque', 0)}" 
                 for p in st.session_state.produtos])
            
            if produto_editar:
                produto_nome = produto_editar.split(' - ')[0]
                produto_escola = produto_editar.split('Escola: ')[1].split(' - ')[0]
                produto_tamanho = produto_editar.split('Tamanho: ')[1].split(' - ')[0]
                
                produto = next((p for p in st.session_state.produtos 
                    if p['nome'] == produto_nome and p.get('escola') == produto_escola and p.get('tamanho') == produto_tamanho), None)
                
                if produto:
                    col1, col2 = st.columns(2)
                    with col1:
                        novo_preco = st.number_input("💰 Novo Preço (R$)", 
                            value=produto['preco'], min_value=0.0, step=0.01)
                        novo_estoque = st.number_input("📦 Novo Estoque", 
                            value=produto['estoque'], min_value=0)
                    with col2:
                        nova_cor = st.text_input("🎨 Nova Cor", value=produto.get('cor', ''))
                        nova_descricao = st.text_area("📝 Nova Descrição", 
                            value=produto.get('descricao', ''))
                    
                    if st.button("💾 Salvar Alterações", type="primary"):
                        produto['preco'] = novo_preco
                        produto['estoque'] = novo_estoque
                        produto['cor'] = nova_cor
                        produto['descricao'] = nova_descricao
                        salvar_dados()
                        st.success("✅ Fardamento atualizado com sucesso!")
        else:
            st.info("👕 Nenhum fardamento cadastrado")

# ESTOQUE
elif menu == "📦 Estoque":
    tab1, tab2, tab3 = st.tabs(["📊 Ajustar Estoque", "📋 Inventário Completo", "⚠️ Alertas"])
    
    with tab1:
        st.header("📊 Ajuste Rápido de Estoque")
        if st.session_state.produtos:
            produto_ajustar = st.selectbox("👕 Selecione o fardamento", 
                [f"{p['nome']} - Escola: {p.get('escola', 'N/A')} - Tamanho: {p.get('tamanho', 'Único')} - Cor: {p.get('cor', 'N/A')} - Estoque: {p.get('estoque', 0)}" 
                 for p in st.session_state.produtos])
            
            acao = st.radio("🎯 Ação:", ["➕ Adicionar Estoque", "➖ Remover Estoque", "🎯 Definir Estoque Exato"])
            quantidade = st.number_input("🔢 Quantidade", min_value=1, value=1)
            
            if st.button("🔄 Aplicar Ajuste", type="primary"):
                produto_nome = produto_ajustar.split(' - ')[0]
                produto_escola = produto_ajustar.split('Escola: ')[1].split(' - ')[0]
                produto_tamanho = produto_ajustar.split('Tamanho: ')[1].split(' - ')[0]
                
                produto = next((p for p in st.session_state.produtos 
                    if p['nome'] == produto_nome and p.get('escola') == produto_escola and p.get('tamanho') == produto_tamanho), None)
                
                if produto:
                    estoque_antigo = produto['estoque']
                    
                    if acao == "➕ Adicionar Estoque":
                        produto['estoque'] += quantidade
                        st.success(f"✅ +{quantidade} unidades adicionadas | Estoque: {estoque_antigo} → {produto['estoque']}")
                    elif acao == "➖ Remover Estoque":
                        if produto['estoque'] >= quantidade:
                            produto['estoque'] -= quantidade
                            st.success(f"✅ -{quantidade} unidades removidas | Estoque: {estoque_antigo} → {produto['estoque']}")
                        else:
                            st.error("❌ Estoque insuficiente!")
                    else:  # Definir Estoque Exato
                        produto['estoque'] = quantidade
                        st.success(f"✅ Estoque definido: {estoque_antigo} → {quantidade} unidades")
                    
                    salvar_dados()
        else:
            st.info("👕 Nenhum fardamento cadastrado")
    
    with tab2:
        st.header("📋 Inventário Completo")
        if st.session_state.produtos:
            df_estoque = pd.DataFrame(st.session_state.produtos)
            
            # Status de estoque
            def status_estoque(quantidade):
                if quantidade == 0:
                    return "🔴 Esgotado"
                elif quantidade < 3:
                    return "🟡 Crítico"
                elif quantidade < 10:
                    return "🟢 Normal"
                else:
                    return "🔵 Alto"
            
            df_estoque['Status'] = df_estoque['estoque'].apply(status_estoque)
            df_estoque = df_estoque.sort_values(['escola', 'categoria', 'tamanho', 'estoque'])
            
            st.dataframe(df_estoque, use_container_width=True)
            
            # Estatísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                total_itens = len(df_estoque)
                st.metric("📦 Total de Itens", total_itens)
            with col2:
                esgotados = len(df_estoque[df_estoque['estoque'] == 0])
                st.metric("🔴 Itens Esgotados", esgotados)
            with col3:
                estoque_baixo = len(df_estoque[df_estoque['estoque'] < 5])
                st.metric("🟡 Estoque Baixo", estoque_baixo)
            
        else:
            st.info("👕 Nenhum fardamento cadastrado")
    
    with tab3:
        st.header("⚠️ Alertas de Estoque")
        if st.session_state.produtos:
            # Produtos esgotados
            produtos_esgotados = [p for p in st.session_state.produtos if p.get('estoque', 0) == 0]
            produtos_baixo = [p for p in st.session_state.produtos if 0 < p.get('estoque', 0) < 5]
            
            if produtos_esgotados:
                st.error("🔴 PRODUTOS ESGOTADOS:")
                for produto in produtos_esgotados:
                    st.error(f"❌ {produto['nome']} - Escola: {produto.get('escola', 'N/A')} - Tamanho: {produto.get('tamanho', 'N/A')} - Cor: {produto.get('cor', 'N/A')}")
            
            if produtos_baixo:
                st.warning("🟡 ESTOQUE BAIXO (menos de 5 unidades):")
                for produto in produtos_baixo:
                    st.warning(f"⚠️ {produto['nome']} - Escola: {produto.get('escola', 'N/A')} - Tamanho: {produto.get('tamanho', 'N/A')} - Estoque: {produto.get('estoque', 0)}")
            
            if not produtos_esgotados and not produtos_baixo:
                st.success("✅ Todos os produtos com estoque adequado!")
        else:
            st.info("👕 Nenhum fardamento cadastrado")

# RELATÓRIOS
elif menu == "📈 Relatórios":
    tab1, tab2, tab3 = st.tabs(["💰 Vendas", "📦 Estoque", "👥 Clientes"])
    
    with tab1:
        st.header("💰 Relatório de Vendas")
        if st.session_state.pedidos:
            df_vendas = pd.DataFrame(st.session_state.pedidos)
            
            # Vendas por escola
            st.subheader("🏫 Vendas por Escola")
            vendas_escola = df_vendas['escola'].value_counts()
            fig1 = px.bar(vendas_escola, title="Vendas por Escola")
            st.plotly_chart(fig1)
            
            # Vendas por tamanho
            st.subheader("📏 Vendas por Tamanho")
            if 'tamanho' in df_vendas.columns:
                vendas_tamanho = df_vendas['tamanho'].value_counts()
                fig2 = px.pie(vendas_tamanho, values=vendas_tamanho.values, 
                             names=vendas_tamanho.index, title="Vendas por Tamanho")
                st.plotly_chart(fig2)
            
            # Exportar
            if st.button("📥 Exportar Relatório de Vendas", type="primary"):
                csv = df_vendas.to_csv(index=False)
                st.download_button(
                    label="⬇️ Baixar CSV",
                    data=csv,
                    file_name=f"relatorio_vendas_{datetime.now().strftime('%d%m%Y')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("📋 Nenhuma venda registrada")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v5.1")

if st.sidebar.button("🔄 Recarregar Dados"):
    carregar_dados()
    st.rerun()

# Notificação de alertas
if 'alertas_mostrados' not in st.session_state:
    st.session_state.alertas_mostrados = True
    produtos_baixo_estoque = [p for p in st.session_state.produtos if p.get('estoque', 0) < 5]
    if produtos_baixo_estoque:
        st.toast("⚠️ Alertas de estoque baixo detectados! Verifique a seção de Estoque.")
