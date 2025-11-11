import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO AVANÇADO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def validar_senha_forte(senha):
    """Valida se a senha é forte"""
    if len(senha) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    if not any(c.isupper() for c in senha):
        return False, "Senha deve ter pelo menos uma letra maiúscula"
    if not any(c.islower() for c in senha):
        return False, "Senha deve ter pelo menos uma letra minúscula"
    if not any(c.isdigit() for c in senha):
        return False, "Senha deve ter pelo menos um número"
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in senha):
        return False, "Senha deve ter pelo menos um caractere especial"
    return True, "Senha válida"

# Usuários e senhas - ALTERE AQUI SUAS SENHAS!
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

# Verificar se está logado
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🚀 SISTEMA PRINCIPAL (SÓ ACESSA LOGADO)
# =========================================

# Configuração da página
st.set_page_config(
    page_title="Sistema de Pedidos",
    page_icon="📦",
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

# Carregar dados ao iniciar
carregar_dados()

# Menu principal
st.sidebar.title("📦 Sistema de Pedidos")
menu = st.sidebar.selectbox("Navegação", 
    ["Dashboard", "Pedidos", "Clientes", "Produtos", "Estoque", "Relatórios", "Usuários"])

# HEADER
st.title("📦 Sistema de Pedidos Completo")

# DASHBOARD
if menu == "Dashboard":
    st.header("📊 Dashboard - Métricas em Tempo Real")
    
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
    
    # Seção de Alertas
    st.subheader("⚠️ Alertas de Estoque")
    produtos_alerta = [p for p in st.session_state.produtos if p.get('estoque', 0) < 5]
    
    if produtos_alerta:
        for produto in produtos_alerta:
            st.warning(f"🚨 {produto['nome']} - Estoque: {produto.get('estoque', 0)} unidades")
    else:
        st.success("✅ Nenhum alerta de estoque no momento")
    
    # Gráfico de vendas
    st.subheader("📈 Vendas por Escola")
    if st.session_state.pedidos:
        df_vendas = pd.DataFrame(st.session_state.pedidos)
        vendas_por_escola = df_vendas['escola'].value_counts()
        fig = px.bar(vendas_por_escola, title="Vendas por Escola")
        st.plotly_chart(fig)
    else:
        st.info("Nenhum pedido cadastrado ainda")

# PEDIDOS
elif menu == "Pedidos":
    st.header("📦 Gestão de Pedidos")
    
    tab1, tab2, tab3 = st.tabs(["Novo Pedido", "Listar Pedidos", "Alterar Status"])
    
    with tab1:
        st.subheader("Cadastrar Novo Pedido")
        
        # Dados do cliente
        if st.session_state.clientes:
            cliente_selecionado = st.selectbox("Cliente", 
                [f"{c['nome']} - {c['escola']}" for c in st.session_state.clientes])
        else:
            st.warning("Cadastre clientes primeiro!")
            cliente_selecionado = None
        
        # Produtos
        if st.session_state.produtos:
            produtos_disponiveis = [p for p in st.session_state.produtos if p.get('estoque', 0) > 0]
            if produtos_disponiveis:
                produto_selecionado = st.selectbox("Produto", 
                    [f"{p['nome']} - R${p['preco']} - Estoque: {p.get('estoque', 0)}" 
                     for p in produtos_disponiveis])
                quantidade = st.number_input("Quantidade", min_value=1, value=1)
            else:
                st.error("❌ Nenhum produto com estoque disponível!")
                produto_selecionado = None
                quantidade = 0
        else:
            st.warning("Cadastre produtos primeiro!")
            produto_selecionado = None
            quantidade = 0
        
        data_entrega = st.date_input("Data de Entrega Prevista")
        observacoes = st.text_area("Observações")
        
        if st.button("Cadastrar Pedido") and cliente_selecionado and produto_selecionado:
            novo_pedido = {
                'id': len(st.session_state.pedidos) + 1,
                'cliente': cliente_selecionado.split(' - ')[0],
                'escola': cliente_selecionado.split(' - ')[1],
                'produto': produto_selecionado.split(' - ')[0],
                'quantidade': quantidade,
                'preco_unitario': float(produto_selecionado.split(' - ')[1].replace('R$', '')),
                'data_pedido': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'data_entrega_prevista': data_entrega.strftime("%d/%m/%Y"),
                'status': 'Pendente',
                'observacoes': observacoes
            }
            
            # Atualizar estoque
            produto_nome = produto_selecionado.split(' - ')[0]
            for produto in st.session_state.produtos:
                if produto['nome'] == produto_nome:
                    produto['estoque'] -= quantidade
                    break
            
            st.session_state.pedidos.append(novo_pedido)
            salvar_dados()
            st.success("✅ Pedido cadastrado com sucesso!")
    
    with tab2:
        st.subheader("Lista de Pedidos")
        if st.session_state.pedidos:
            df_pedidos = pd.DataFrame(st.session_state.pedidos)
            st.dataframe(df_pedidos)
        else:
            st.info("Nenhum pedido cadastrado")
    
    with tab3:
        st.subheader("Alterar Status do Pedido")
        if st.session_state.pedidos:
            pedido_selecionado = st.selectbox("Selecione o pedido", 
                [f"ID: {p['id']} - {p['cliente']} - {p['produto']}" for p in st.session_state.pedidos])
            
            novo_status = st.selectbox("Novo Status", 
                ["Pendente", "Entregue", "Cancelado"])
            
            if st.button("Atualizar Status"):
                pedido_id = int(pedido_selecionado.split(' - ')[0].replace('ID: ', ''))
                for pedido in st.session_state.pedidos:
                    if pedido['id'] == pedido_id:
                        pedido['status'] = novo_status
                        break
                salvar_dados()
                st.success("✅ Status atualizado com sucesso!")
        else:
            st.info("Nenhum pedido cadastrado")

# CLIENTES
elif menu == "Clientes":
    st.header("👥 Gestão de Clientes")
    
    tab1, tab2 = st.tabs(["Cadastrar Cliente", "Listar Clientes"])
    
    with tab1:
        st.subheader("Novo Cliente")
        nome_cliente = st.text_input("Nome do Cliente")
        escola_cliente = st.selectbox("Escola", st.session_state.escolas)
        telefone = st.text_input("Telefone")
        email = st.text_input("Email")
        
        if st.button("Cadastrar Cliente"):
            if nome_cliente:
                novo_cliente = {
                    'nome': nome_cliente,
                    'escola': escola_cliente,
                    'telefone': telefone,
                    'email': email
                }
                st.session_state.clientes.append(novo_cliente)
                salvar_dados()
                st.success("✅ Cliente cadastrado com sucesso!")
            else:
                st.error("❌ Nome do cliente é obrigatório!")
    
    with tab2:
        st.subheader("Clientes Cadastrados")
        if st.session_state.clientes:
            df_clientes = pd.DataFrame(st.session_state.clientes)
            st.dataframe(df_clientes)
            
            # Relatório por escola
            st.subheader("📊 Clientes por Escola")
            clientes_por_escola = df_clientes['escola'].value_counts()
            fig = px.pie(values=clientes_por_escola.values, 
                        names=clientes_por_escola.index, 
                        title="Distribuição de Clientes por Escola")
            st.plotly_chart(fig)
        else:
            st.info("Nenhum cliente cadastrado")

# PRODUTOS
elif menu == "Produtos":
    st.header("👕 Gestão de Produtos")
    
    tab1, tab2 = st.tabs(["Cadastrar Produto", "Listar Produtos"])
    
    with tab1:
        st.subheader("Novo Produto")
        nome_produto = st.text_input("Nome do Produto")
        preco_produto = st.number_input("Preço (R$)", min_value=0.0, step=0.01)
        estoque_inicial = st.number_input("Estoque Inicial", min_value=0, value=0)
        categoria = st.selectbox("Categoria", ["Uniforme", "Material", "Acessório", "Outros"])
        
        if st.button("Cadastrar Produto"):
            if nome_produto and preco_produto >= 0:
                novo_produto = {
                    'nome': nome_produto,
                    'preco': preco_produto,
                    'estoque': estoque_inicial,
                    'categoria': categoria
                }
                st.session_state.produtos.append(novo_produto)
                salvar_dados()
                st.success("✅ Produto cadastrado com sucesso!")
            else:
                st.error("❌ Preencha todos os campos obrigatórios!")
    
    with tab2:
        st.subheader("Produtos Cadastrados")
        if st.session_state.produtos:
            df_produtos = pd.DataFrame(st.session_state.produtos)
            st.dataframe(df_produtos)
        else:
            st.info("Nenhum produto cadastrado")

# ESTOQUE
elif menu == "Estoque":
    st.header("📦 Controle de Estoque")
    
    # Alertas de estoque baixo
    produtos_baixo_estoque = [p for p in st.session_state.produtos if p.get('estoque', 0) < 5]
    
    if produtos_baixo_estoque:
        st.error("⚠️ ALERTA - Produtos com Estoque Baixo:")
        for produto in produtos_baixo_estoque:
            st.error(f"🚨 {produto['nome']} - Apenas {produto.get('estoque', 0)} unidades restantes")
    else:
        st.success("✅ Estoque em dia - Nenhum produto com estoque crítico")
    
    # Lista completa de estoque
    st.subheader("Inventário Completo")
    if st.session_state.produtos:
        df_estoque = pd.DataFrame(st.session_state.produtos)
        
        # Adicionar coluna de status
        def status_estoque(quantidade):
            if quantidade == 0:
                return "🔴 Esgotado"
            elif quantidade < 5:
                return "🟡 Baixo"
            else:
                return "🟢 Normal"
        
        df_estoque['Status'] = df_estoque['estoque'].apply(status_estoque)
        st.dataframe(df_estoque)
        
        # Gráfico de estoque
        st.subheader("📊 Análise de Estoque")
        fig = px.bar(df_estoque, x='nome', y='estoque', color='Status',
                    title="Nível de Estoque por Produto")
        st.plotly_chart(fig)
    else:
        st.info("Nenhum produto cadastrado")

# RELATÓRIOS
elif menu == "Relatórios":
    st.header("📈 Relatórios Detalhados")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Vendas", "Clientes", "Estoque", "Pedidos"])
    
    with tab1:
        st.subheader("Relatório de Vendas")
        if st.session_state.pedidos:
            df_vendas = pd.DataFrame(st.session_state.pedidos)
            
            # Vendas por escola
            st.write("### Vendas por Escola")
            vendas_escola = df_vendas.groupby('escola').size()
            fig1 = px.bar(vendas_escola, title="Total de Vendas por Escola")
            st.plotly_chart(fig1)
            
            # Vendas por status
            st.write("### Vendas por Status")
            vendas_status = df_vendas['status'].value_counts()
            fig2 = px.pie(vendas_status, values=vendas_status.values, 
                         names=vendas_status.index, title="Distribuição por Status")
            st.plotly_chart(fig2)
            
            # Exportar dados
            if st.button("📥 Exportar Relatório de Vendas"):
                csv = df_vendas.to_csv(index=False)
                st.download_button(
                    label="Baixar CSV",
                    data=csv,
                    file_name=f"relatorio_vendas_{datetime.now().strftime('%d%m%Y')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("Nenhuma venda registrada")
    
    with tab2:
        st.subheader("Relatório de Clientes")
        if st.session_state.clientes:
            df_clientes = pd.DataFrame(st.session_state.clientes)
            st.dataframe(df_clientes)
            
            # Análise por escola
            st.write("### Clientes por Escola")
            clientes_escola = df_clientes['escola'].value_counts()
            fig = px.bar(clientes_escola, title="Clientes por Escola")
            st.plotly_chart(fig)
        else:
            st.info("Nenhum cliente cadastrado")
    
    with tab3:
        st.subheader("Relatório de Estoque")
        if st.session_state.produtos:
            df_estoque = pd.DataFrame(st.session_state.produtos)
            
            # Produtos por categoria
            st.write("### Produtos por Categoria")
            produtos_categoria = df_estoque['categoria'].value_counts()
            fig = px.pie(produtos_categoria, values=produtos_categoria.values,
                        names=produtos_categoria.index, title="Distribuição por Categoria")
            st.plotly_chart(fig)
            
            # Alertas detalhados
            st.write("### Alertas de Estoque")
            produtos_alerta = df_estoque[df_estoque['estoque'] < 5]
            if not produtos_alerta.empty:
                st.dataframe(produtos_alerta)
            else:
                st.success("✅ Nenhum produto com estoque baixo")
        else:
            st.info("Nenhum produto cadastrado")
    
    with tab4:
        st.subheader("Relatório de Pedidos")
        if st.session_state.pedidos:
            df_pedidos = pd.DataFrame(st.session_state.pedidos)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                status_filtro = st.multiselect("Filtrar por Status", 
                    options=df_pedidos['status'].unique(),
                    default=df_pedidos['status'].unique())
            
            with col2:
                escola_filtro = st.multiselect("Filtrar por Escola",
                    options=df_pedidos['escola'].unique(),
                    default=df_pedidos['escola'].unique())
            
            # Aplicar filtros
            df_filtrado = df_pedidos[
                (df_pedidos['status'].isin(status_filtro)) & 
                (df_pedidos['escola'].isin(escola_filtro))
            ]
            
            st.dataframe(df_filtrado)
            
            # Métricas do relatório
            total_valor = (df_filtrado['quantidade'] * df_filtrado['preco_unitario']).sum()
            st.metric("Valor Total Filtrado", f"R$ {total_valor:.2f}")
            
        else:
            st.info("Nenhum pedido cadastrado")

# =========================================
# 👥 GERENCIAMENTO DE USUÁRIOS
# =========================================
elif menu == "Usuários":
    st.header("👥 Gerenciamento de Usuários")
    
    if st.session_state.username != "admin":
        st.warning("⚠️ Apenas administradores podem gerenciar usuários")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["Adicionar Usuário", "Alterar Senha", "Usuários Cadastrados"])
    
    with tab1:
        st.subheader("Adicionar Novo Usuário")
        novo_usuario = st.text_input("Nome de usuário")
        nova_senha = st.text_input("Senha", type='password')
        confirmar_senha = st.text_input("Confirmar Senha", type='password')
        
        if st.button("Cadastrar Usuário"):
            if novo_usuario and nova_senha:
                if nova_senha == confirmar_senha:
                    senha_valida, mensagem = validar_senha_forte(nova_senha)
                    if senha_valida:
                        if novo_usuario not in usuarios:
                            usuarios[novo_usuario] = make_hashes(nova_senha)
                            st.success(f"✅ Usuário {novo_usuario} cadastrado com sucesso!")
                        else:
                            st.error("❌ Usuário já existe")
                    else:
                        st.error(f"❌ {mensagem}")
                else:
                    st.error("❌ Senhas não coincidem")
            else:
                st.error("❌ Preencha todos os campos")
    
    with tab2:
        st.subheader("Alterar Senha")
        usuario_alterar = st.selectbox("Selecione o usuário", list(usuarios.keys()))
        nova_senha_alt = st.text_input("Nova Senha", type='password', key="nova_senha_alt")
        confirmar_senha_alt = st.text_input("Confirmar Nova Senha", type='password', key="confirmar_senha_alt")
        
        if st.button("Alterar Senha"):
            if nova_senha_alt and confirmar_senha_alt:
                if nova_senha_alt == confirmar_senha_alt:
                    senha_valida, mensagem = validar_senha_forte(nova_senha_alt)
                    if senha_valida:
                        usuarios[usuario_alterar] = make_hashes(nova_senha_alt)
                        st.success(f"✅ Senha do usuário {usuario_alterar} alterada com sucesso!")
                    else:
                        st.error(f"❌ {mensagem}")
                else:
                    st.error("❌ Senhas não coincidem")
            else:
                st.error("❌ Preencha todos os campos")
    
    with tab3:
        st.subheader("Usuários do Sistema")
        st.write("**Usuários cadastrados:**")
        for usuario in usuarios:
            st.write(f"- {usuario}")
        
        st.info("💡 Use senhas fortes com letras, números e caracteres especiais")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("Sistema de Pedidos Completo v2.0")

if st.sidebar.button("🔄 Recarregar Dados"):
    carregar_dados()
    st.rerun()

# Notificação de alertas ao iniciar
if 'alertas_mostrados' not in st.session_state:
    st.session_state.alertas_mostrados = True
    produtos_baixo_estoque = [p for p in st.session_state.produtos if p.get('estoque', 0) < 5]
    if produtos_baixo_estoque:
        st.toast("⚠️ Alertas de estoque baixo detectados! Verifique a seção de Estoque.")
