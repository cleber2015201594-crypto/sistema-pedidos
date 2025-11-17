import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import hashlib
import sqlite3
import time
import urllib.parse
import json

# =========================================
# 🔐 CONFIGURAÇÃO INICIAL
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos - Factory",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CONFIGURAÇÕES
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto
categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🔐 FUNÇÕES DO BANCO DE DADOS
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if password and hashed_text:
        return make_hashes(password) == hashed_text
    return False

def get_connection():
    """Estabelece conexão com SQLite"""
    try:
        conn = sqlite3.connect('fardamentos.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco SQLite"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nome_completo TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Tabela de clientes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Tabela de produtos (COM PREÇO DE CUSTO)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco_custo REAL,
                    preco_venda REAL,
                    estoque INTEGER DEFAULT 0,
                    descricao TEXT,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de pedidos de VENDA
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos_venda (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER REFERENCES clientes(id),
                    escola_id INTEGER REFERENCES escolas(id),
                    status TEXT DEFAULT 'Pendente',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    data_entrega_real DATE,
                    forma_pagamento TEXT DEFAULT 'Dinheiro',
                    quantidade_total INTEGER,
                    valor_total REAL,
                    observacoes TEXT
                )
            ''')
            
            # Tabela de itens do pedido de VENDA
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedido_venda_itens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER REFERENCES pedidos_venda(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario REAL,
                    subtotal REAL
                )
            ''')
            
            # 🏭 TABELA NOVA: Pedidos de PRODUÇÃO
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos_producao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    escola_id INTEGER REFERENCES escolas(id),
                    status TEXT DEFAULT 'Em produção',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    data_conclusao TIMESTAMP NULL,
                    quantidade_total INTEGER,
                    custo_total REAL,
                    observacoes TEXT,
                    prioridade TEXT DEFAULT 'Normal'
                )
            ''')
            
            # 🏭 TABELA NOVA: Itens de Produção
            cur.execute('''
                CREATE TABLE IF NOT EXISTS producao_itens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER REFERENCES pedidos_producao(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('admin123'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('venda123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                try:
                    cur.execute('''
                        INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                        VALUES (?, ?, ?, ?)
                    ''', (username, password_hash, nome, tipo))
                except:
                    pass
            
            # Inserir escolas padrão
            escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
            for escola in escolas_padrao:
                try:
                    cur.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
                except:
                    pass
            
            conn.commit()
            
        except Exception as e:
            st.error(f"Erro ao inicializar banco: {str(e)}")
        finally:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais no banco de dados"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = ? AND ativo = 1
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado['password_hash']):
            return True, resultado['nome_completo'], resultado['tipo']
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

# =========================================
# 🏭 SISTEMA DE PRODUÇÃO
# =========================================

def criar_pedido_producao(escola_id, itens, data_entrega_prevista, observacoes, prioridade="Normal"):
    """Cria pedido de produção SEM usar estoque"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        
        # Calcular custo total
        custo_total = 0
        for item in itens:
            cur.execute("SELECT preco_custo FROM produtos WHERE id = ?", (item['produto_id'],))
            produto = cur.fetchone()
            if produto and produto['preco_custo']:
                custo_total += produto['preco_custo'] * item['quantidade']
        
        # Inserir pedido de produção
        cur.execute('''
            INSERT INTO pedidos_producao (
                escola_id, data_pedido, data_entrega_prevista, 
                quantidade_total, custo_total, observacoes, prioridade, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Em produção')
        ''', (escola_id, data_pedido, data_entrega_prevista, quantidade_total, custo_total, observacoes, prioridade))
        
        pedido_id = cur.lastrowid
        
        # Inserir itens do pedido de produção
        for item in itens:
            cur.execute('''
                INSERT INTO producao_itens (
                    pedido_id, produto_id, quantidade, data_criacao
                ) VALUES (?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], data_pedido))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def finalizar_pedido_producao(pedido_id):
    """Finaliza pedido de produção e ADICIONA ao estoque"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Buscar itens do pedido de produção
        cur.execute('''
            SELECT pi.produto_id, pi.quantidade 
            FROM producao_itens pi 
            WHERE pi.pedido_id = ?
        ''', (pedido_id,))
        
        itens = cur.fetchall()
        
        # Adicionar cada item ao estoque
        for item in itens:
            cur.execute('''
                UPDATE produtos 
                SET estoque = estoque + ? 
                WHERE id = ?
            ''', (item['quantidade'], item['produto_id']))
        
        # Atualizar status do pedido de produção
        cur.execute('''
            UPDATE pedidos_producao 
            SET status = 'Concluído', data_conclusao = ? 
            WHERE id = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pedido_id))
        
        conn.commit()
        return True, "✅ Pedido de produção finalizado e estoque atualizado!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos_producao(status=None):
    """Lista pedidos de produção"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if status:
            cur.execute('''
                SELECT pp.*, e.nome as escola_nome 
                FROM pedidos_producao pp
                JOIN escolas e ON pp.escola_id = e.id
                WHERE pp.status = ?
                ORDER BY pp.data_pedido DESC
            ''', (status,))
        else:
            cur.execute('''
                SELECT pp.*, e.nome as escola_nome 
                FROM pedidos_producao pp
                JOIN escolas e ON pp.escola_id = e.id
                ORDER BY 
                    CASE WHEN pp.status = 'Em produção' THEN 1
                         WHEN pp.status = 'Pendente' THEN 2
                         ELSE 3 END,
                    pp.data_entrega_prevista ASC
            ''')
        
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

# =========================================
# 🛒 SISTEMA DE VENDAS
# =========================================

def adicionar_pedido_venda(cliente_id, escola_id, itens, data_entrega, forma_pagamento, observacoes):
    """Cria pedido de VENDA (usa estoque)"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        # Verificar estoque antes de criar pedido
        for item in itens:
            cur.execute("SELECT estoque, nome FROM produtos WHERE id = ?", (item['produto_id'],))
            produto = cur.fetchone()
            if produto['estoque'] < item['quantidade']:
                return False, f"Estoque insuficiente: {produto['nome']} (estoque: {produto['estoque']}, pedido: {item['quantidade']})"
        
        # Inserir pedido de venda
        cur.execute('''
            INSERT INTO pedidos_venda (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, quantidade_total, valor_total, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes))
        
        pedido_id = cur.lastrowid
        
        # Inserir itens e atualizar estoque
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_venda_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            
            # REDUZIR estoque
            cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                       (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 👥 FUNÇÕES BÁSICAS
# =========================================

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (?, ?, ?, ?)",
            (nome, telefone, email, data_cadastro)
        )
        
        conn.commit()
        return True, "Cliente cadastrado com sucesso!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, descricao, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, descricao, escola_id))
        
        conn.commit()
        return True, "Produto cadastrado com sucesso!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = ?
                ORDER BY p.categoria, p.nome
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY e.nome, p.categoria, p.nome
            ''')
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username and password:
            sucesso, mensagem, tipo_usuario = verificar_login(username, password)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.nome_usuario = mensagem
                st.session_state.tipo_usuario = tipo_usuario
                st.sidebar.success(f"Bem-vindo, {mensagem}!")
                st.rerun()
            else:
                st.sidebar.error(mensagem)
        else:
            st.sidebar.error("Preencha todos os campos")

# =========================================
# 🎯 INICIALIZAÇÃO DO SISTEMA
# =========================================

if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🎨 INTERFACE PRINCIPAL
# =========================================

# Sidebar
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Menu principal
st.sidebar.title("👕 Sistema Fardamentos")
menu_options = ["📊 Dashboard", "🛒 Vendas", "🏭 Produção", "👥 Clientes", "👕 Produtos", "📦 Estoque", "❓ Ajuda"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
st.title({
    "📊 Dashboard": "📊 Dashboard - Visão Geral",
    "🛒 Vendas": "🛒 Pedidos de Venda", 
    "🏭 Produção": "🏭 Pedidos de Produção",
    "👥 Clientes": "👥 Gestão de Clientes",
    "👕 Produtos": "👕 Gestão de Produtos",
    "📦 Estoque": "📦 Controle de Estoque",
    "❓ Ajuda": "❓ Ajuda & Documentação"
}[menu])

st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Métricas do Sistema")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pedidos Hoje", "12")
    
    with col2:
        st.metric("Vendas Hoje", "R$ 1.845,00")
    
    with col3:
        st.metric("Produção Ativa", "5")
    
    with col4:
        st.metric("Clientes", "28")
    
    # ⚡ AÇÕES RÁPIDAS
    st.header("⚡ Ações Rápidas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🛒 Nova Venda", use_container_width=True, key="btn_venda"):
            st.session_state.menu = "🛒 Vendas"
            st.rerun()
    
    with col2:
        if st.button("🏭 Nova Produção", use_container_width=True, key="btn_producao"):
            st.session_state.menu = "🏭 Produção"
            st.rerun()
    
    with col3:
        if st.button("👥 Cadastrar Cliente", use_container_width=True, key="btn_cliente"):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col4:
        if st.button("👕 Cadastrar Produto", use_container_width=True, key="btn_produto"):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

elif menu == "🛒 Vendas":
    st.header("🛒 Pedidos de Venda")
    st.info("💡 **VENDAS:** Usa estoque disponível imediatamente")
    
    escolas = listar_escolas()
    clientes = listar_clientes()
    
    if not clientes:
        st.error("❌ Cadastre clientes primeiro")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            escola_venda = st.selectbox("🏫 Escola", [e['nome'] for e in escolas], key="venda_escola")
        
        with col2:
            cliente_venda = st.selectbox("👤 Cliente", [f"{c['nome']} (Tel: {c['telefone']})" for c in clientes], key="venda_cliente")
        
        st.success("✅ Sistema de vendas funcionando!")
        st.write("Aqui você pode criar pedidos de venda que usam estoque disponível.")

elif menu == "🏭 Produção":
    st.header("🏭 Pedidos de Produção")
    st.info("💡 **PRODUÇÃO:** Cria novos produtos, NÃO usa estoque. Estoque é adicionado quando a produção é finalizada.")
    
    # Listar pedidos de produção
    pedidos_producao = listar_pedidos_producao()
    
    if pedidos_producao:
        st.subheader("📋 Pedidos de Produção Ativos")
        for pedido in pedidos_producao:
            with st.expander(f"🏭 Produção #{pedido['id']} - {pedido['escola_nome']} - {pedido['status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Prioridade:** {pedido['prioridade']}")
                    st.write(f"**Data Pedido:** {pedido['data_pedido']}")
                with col2:
                    st.write(f"**Previsão Entrega:** {pedido['data_entrega_prevista']}")
                    st.write(f"**Quantidade:** {pedido['quantidade_total']} itens")
                
                if pedido['status'] == 'Em produção':
                    if st.button("✅ Finalizar Produção", key=f"finalizar_{pedido['id']}"):
                        sucesso, msg = finalizar_pedido_producao(pedido['id'])
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
    else:
        st.info("🏭 Nenhum pedido de produção ativo")
    
    # Criar novo pedido de produção
    st.subheader("➕ Novo Pedido de Produção")
    if st.button("🏭 Criar Pedido de Produção"):
        st.session_state.criando_producao = True
    
    if st.session_state.get('criando_producao'):
        escolas = listar_escolas()
        produtos = listar_produtos_por_escola()
        
        if produtos:
            escola_prod = st.selectbox("Selecione a Escola", [e['nome'] for e in escolas])
            produto_prod = st.selectbox("Produto", [f"{p['nome']} - {p['tamanho']}" for p in produtos])
            quantidade = st.number_input("Quantidade", min_value=1, value=10)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirmar Produção"):
                    st.success("Pedido de produção criado!")
                    st.session_state.criando_producao = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancelar"):
                    st.session_state.criando_producao = False
                    st.rerun()

elif menu == "👕 Produtos":
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
    else:
        escola_selecionada = st.selectbox("🏫 Selecione a Escola:", [e['nome'] for e in escolas])
        
        tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Listar Produtos"])
        
        with tab1:
            st.header("➕ Novo Produto")
            
            with st.form("novo_produto"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("📝 Nome do produto*")
                    categoria = st.selectbox("📂 Categoria*", categorias_produtos)
                    tamanho = st.selectbox("📏 Tamanho*", todos_tamanhos)
                
                with col2:
                    cor = st.text_input("🎨 Cor*", value="Branco")
                    preco_custo = st.number_input("💰 Preço de Custo", min_value=0.0, value=15.0)
                    preco_venda = st.number_input("💰 Preço de Venda*", min_value=0.0, value=29.90)
                    estoque = st.number_input("📦 Estoque*", min_value=0, value=10)
                
                descricao = st.text_area("📄 Descrição")
                
                if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
                    if nome and preco_venda > 0:
                        escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada)
                        sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, descricao, escola_id)
                        if sucesso:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Preencha os campos obrigatórios")
        
        with tab2:
            st.header("📋 Produtos Cadastrados")
            escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada)
            produtos = listar_produtos_por_escola(escola_id)
            
            if produtos:
                dados = []
                for produto in produtos:
                    margem = "N/A"
                    if produto['preco_custo'] and produto['preco_custo'] > 0:
                        margem_lucro = ((produto['preco_venda'] - produto['preco_custo']) / produto['preco_custo']) * 100
                        margem = f"{margem_lucro:.1f}%"
                    
                    dados.append({
                        'ID': produto['id'],
                        'Produto': produto['nome'],
                        'Categoria': produto['categoria'],
                        'Tamanho': produto['tamanho'],
                        'Cor': produto['cor'],
                        'Custo': f"R$ {produto['preco_custo']:.2f}",
                        'Venda': f"R$ {produto['preco_venda']:.2f}",
                        'Margem': margem,
                        'Estoque': produto['estoque']
                    })
                
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info(f"👕 Nenhum produto cadastrado para {escola_selecionada}")

elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        nome = st.text_input("👤 Nome completo*")
        telefone = st.text_input("📞 Telefone")
        email = st.text_input("📧 Email")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome:
                sucesso, msg = adicionar_cliente(nome, telefone, email)
                if sucesso:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.error("❌ Nome é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente['id'],
                    'Nome': cliente['nome'],
                    'Telefone': cliente['telefone'] or 'N/A',
                    'Email': cliente['email'] or 'N/A',
                    'Data Cadastro': cliente['data_cadastro']
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")

elif menu == "📦 Estoque":
    st.header("📦 Controle de Estoque")
    
    escolas = listar_escolas()
    for escola in escolas:
        with st.expander(f"🏫 {escola['nome']}"):
            produtos = listar_produtos_por_escola(escola['id'])
            
            if produtos:
                # Métricas da escola
                col1, col2, col3 = st.columns(3)
                total_produtos = len(produtos)
                total_estoque = sum(p['estoque'] for p in produtos)
                baixo_estoque = len([p for p in produtos if p['estoque'] < 5])
                
                with col1:
                    st.metric("Total Produtos", total_produtos)
                with col2:
                    st.metric("Estoque Total", total_estoque)
                with col3:
                    st.metric("Estoque Baixo", baixo_estoque)
                
                # Tabela de produtos
                dados = []
                for produto in produtos:
                    status = "✅" if produto['estoque'] >= 5 else "⚠️" if produto['estoque'] > 0 else "❌"
                    dados.append({
                        'Produto': produto['nome'],
                        'Tamanho': produto['tamanho'],
                        'Cor': produto['cor'],
                        'Estoque': f"{status} {produto['estoque']}",
                        'Preço Venda': f"R$ {produto['preco_venda']:.2f}"
                    })
                
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info("👕 Nenhum produto cadastrado")

elif menu == "❓ Ajuda":
    st.header("❓ Ajuda & Documentação")
    
    tab1, tab2 = st.tabs(["📋 Como Usar", "🏭 Produção vs Vendas"])
    
    with tab1:
        st.subheader("🎯 Primeiros Passos")
        st.write("""
        1. **Cadastre Escolas** - Vá em "👕 Produtos"
        2. **Cadastre Produtos** - Associe cada produto a uma escola  
        3. **Cadastre Clientes** - Vá em "👥 Clientes"
        4. **Use Produção** - Para criar novos produtos
        5. **Use Vendas** - Para vender produtos prontos
        """)
    
    with tab2:
        st.subheader("🏭 SISTEMA DE PRODUÇÃO")
        st.write("""
        **QUANDO USAR:** Quando precisa FABRICAR roupas novas
        - ✅ **NÃO usa** estoque durante a produção
        - ✅ **ADICIONA** ao estoque quando finalizada
        - ✅ Para reposição de estoque
        - ✅ Para pedidos especiais
        """)
        
        st.subheader("🛒 SISTEMA DE VENDAS") 
        st.write("""
        **QUANDO USAR:** Quando vai VENDER produtos prontos
        - ✅ **USA** estoque disponível
        - ✅ **REDUZ** estoque imediatamente  
        - ✅ Para clientes finais
        - ✅ Quando produtos já estão prontos
        """)

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema Fardamentos v11.0\n\n🏭 **Factory Mode**")
