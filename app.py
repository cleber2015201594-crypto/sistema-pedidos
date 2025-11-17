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
                    observacoes TEXT,
                    cupom_desconto TEXT,
                    valor_desconto REAL DEFAULT 0
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
            
            # Tabela de templates de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS templates_pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    escola_id INTEGER REFERENCES escolas(id),
                    itens TEXT,  -- JSON com os itens
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor')
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
# 🏭 SISTEMA DE PRODUÇÃO (NOVO)
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
        
        # Calcular custo total baseado no preço de custo dos produtos
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

def obter_detalhes_pedido_producao(pedido_id):
    """Obtém detalhes de um pedido de produção"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        
        # Informações do pedido
        cur.execute('''
            SELECT pp.*, e.nome as escola_nome 
            FROM pedidos_producao pp
            JOIN escolas e ON pp.escola_id = e.id
            WHERE pp.id = ?
        ''', (pedido_id,))
        
        pedido = cur.fetchone()
        
        if not pedido:
            return None
        
        # Itens do pedido
        cur.execute('''
            SELECT pi.*, p.nome as produto_nome, p.tamanho, p.cor, p.preco_custo,
                   (p.preco_custo * pi.quantidade) as custo_item
            FROM producao_itens pi
            JOIN produtos p ON pi.produto_id = p.id
            WHERE pi.pedido_id = ?
        ''', (pedido_id,))
        
        itens = cur.fetchall()
        
        return {
            'pedido': dict(pedido),
            'itens': [dict(item) for item in itens]
        }
    except Exception as e:
        return None
    finally:
        conn.close()

# =========================================
# 🔍 SISTEMA DE BUSCA
# =========================================

def buscar_produtos(termo, escola_id=None):
    """Busca produtos por nome, categoria, cor"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        termo = f"%{termo}%"
        
        if escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = ? AND (p.nome LIKE ? OR p.categoria LIKE ? OR p.cor LIKE ?)
                ORDER BY p.nome
            ''', (escola_id, termo, termo, termo))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.nome LIKE ? OR p.categoria LIKE ? OR p.cor LIKE ?
                ORDER BY p.nome
            ''', (termo, termo, termo))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        return []
    finally:
        conn.close()

# =========================================
# 📧 SISTEMA DE NOTIFICAÇÕES
# =========================================

def verificar_alertas_estoque():
    """Verifica produtos com estoque baixo"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id 
            WHERE p.estoque < 5
            ORDER BY p.estoque ASC
        ''')
        
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

# =========================================
# 📊 DASHBOARD MELHORADO
# =========================================

def obter_metricas_tempo_real():
    """Obtém métricas atualizadas para dashboard"""
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cur = conn.cursor()
        
        # Total de pedidos hoje
        cur.execute('''
            SELECT COUNT(*) as total FROM pedidos_venda 
            WHERE DATE(data_pedido) = DATE('now')
        ''')
        pedidos_hoje = cur.fetchone()['total']
        
        # Vendas do dia
        cur.execute('''
            SELECT COALESCE(SUM(valor_total), 0) as total FROM pedidos_venda 
            WHERE DATE(data_pedido) = DATE('now')
        ''')
        vendas_hoje = cur.fetchone()['total']
        
        # Pedidos pendentes
        cur.execute('''
            SELECT COUNT(*) as total FROM pedidos_venda 
            WHERE status = 'Pendente'
        ''')
        pedidos_pendentes = cur.fetchone()['total']
        
        # Pedidos em produção
        cur.execute('''
            SELECT COUNT(*) as total FROM pedidos_producao 
            WHERE status = 'Em produção'
        ''')
        producao_andamento = cur.fetchone()['total']
        
        # Alertas de estoque
        cur.execute('''
            SELECT COUNT(*) as total FROM produtos 
            WHERE estoque < 5
        ''')
        alertas_estoque = cur.fetchone()['total']
        
        return {
            'pedidos_hoje': pedidos_hoje,
            'vendas_hoje': vendas_hoje,
            'pedidos_pendentes': pedidos_pendentes,
            'producao_andamento': producao_andamento,
            'alertas_estoque': alertas_estoque
        }
    except Exception as e:
        return {}
    finally:
        conn.close()

# =========================================
# 🛒 FUNÇÕES DE VENDA (ESTOQUE)
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
# 👥 FUNÇÕES DE CLIENTES E PRODUTOS
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

# Inicializar banco
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
menu_options = ["📊 Dashboard", "🛒 Vendas", "🏭 Produção", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios", "❓ Ajuda"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
st.title({
    "📊 Dashboard": "📊 Dashboard - Visão Geral",
    "🛒 Vendas": "🛒 Pedidos de Venda", 
    "🏭 Produção": "🏭 Pedidos de Produção",
    "👥 Clientes": "👥 Gestão de Clientes",
    "👕 Produtos": "👕 Gestão de Produtos",
    "📦 Estoque": "📦 Controle de Estoque",
    "📈 Relatórios": "📈 Relatórios Detalhados",
    "❓ Ajuda": "❓ Ajuda & Documentação"
}[menu])

st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    # 📊 Métricas em tempo real
    metricas = obter_metricas_tempo_real()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Pedidos Hoje", metricas.get('pedidos_hoje', 0))
    
    with col2:
        st.metric("Vendas Hoje", f"R$ {metricas.get('vendas_hoje', 0):.2f}")
    
    with col3:
        st.metric("Vendas Pendentes", metricas.get('pedidos_pendentes', 0))
    
    with col4:
        st.metric("Produção", metricas.get('producao_andamento', 0))
    
    with col5:
        st.metric("Alertas Estoque", metricas.get('alertas_estoque', 0))
    
    # 🚨 Alertas de estoque
    alertas = verificar_alertas_estoque()
    if alertas:
        st.error(f"🚨 {len(alertas)} produtos com estoque baixo!")
        for alerta in alertas[:3]:
            st.warning(f"{alerta['nome']} - {alerta['escola_nome']}: {alerta['estoque']} unidades")
    
    # ⚡ AÇÕES RÁPIDAS CORRIGIDAS
    st.header("⚡ Ações Rápidas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🛒 Novo Pedido Venda", use_container_width=True, key="btn_venda"):
            st.session_state.menu = "🛒 Vendas"
            st.rerun()
    
    with col2:
        if st.button("🏭 Novo Pedido Produção", use_container_width=True, key="btn_producao"):
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
    st.header("🛒 Pedidos de Venda (COM Estoque)")
    st.info("💡 **VENDAS:** Usa estoque disponível imediatamente")
    
    escolas = listar_escolas()
    clientes = listar_clientes()
    
    if not clientes:
        st.error("❌ Cadastre clientes primeiro")
    elif not escolas:
        st.error("❌ Cadastre escolas primeiro")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            escola_venda = st.selectbox("🏫 Escola", [e['nome'] for e in escolas], key="venda_escola")
            escola_id = next(e['id'] for e in escolas if e['nome'] == escola_venda)
        
        with col2:
            cliente_venda = st.selectbox("👤 Cliente", [f"{c['nome']} (ID: {c['id']})" for c in clientes], key="venda_cliente")
            cliente_id = int(cliente_venda.split("(ID: ")[1].replace(")", ""))
        
        # Produtos da escola com estoque
        produtos = listar_produtos_por_escola(escola_id)
        produtos_com_estoque = [p for p in produtos if p['estoque'] > 0]
        
        if produtos_com_estoque:
            st.subheader("🛒 Adicionar Itens (Estoque Disponível)")
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                produto_selecionado = st.selectbox(
                    "Produto:",
                    [f"{p['nome']} - {p['tamanho']} - {p['cor']} (Estoque: {p['estoque']}) - R$ {p['preco_venda']:.2f}" 
                     for p in produtos_com_estoque],
                    key="venda_produto"
                )
            with col2:
                quantidade = st.number_input("Qtd", min_value=1, value=1, key="venda_qtd")
            with col3:
                if st.button("➕ Add Item", use_container_width=True, key="add_venda"):
                    if 'itens_venda' not in st.session_state:
                        st.session_state.itens_venda = []
                    
                    produto_id = next(p['id'] for p in produtos_com_estoque 
                                    if f"{p['nome']} - {p['tamanho']} - {p['cor']} (Estoque: {p['estoque']}) - R$ {p['preco_venda']:.2f}" == produto_selecionado)
                    produto = next(p for p in produtos_com_estoque if p['id'] == produto_id)
                    
                    if quantidade > produto['estoque']:
                        st.error(f"❌ Estoque insuficiente! Disponível: {produto['estoque']}")
                    else:
                        item = {
                            'produto_id': produto_id,
                            'nome': produto['nome'],
                            'tamanho': produto['tamanho'],
                            'cor': produto['cor'],
                            'quantidade': quantidade,
                            'preco_unitario': produto['preco_venda'],
                            'subtotal': produto['preco_venda'] * quantidade
                        }
                        st.session_state.itens_venda.append(item)
                        st.success("✅ Item adicionado!")
                        st.rerun()
            
            # Itens do pedido
            if 'itens_venda' in st.session_state and st.session_state.itens_venda:
                st.subheader("📋 Itens do Pedido de Venda")
                total_venda = sum(item['subtotal'] for item in st.session_state.itens_venda)
                
                for i, item in enumerate(st.session_state.itens_venda):
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                    with col1:
                        st.write(f"**{item['nome']}**")
                        st.write(f"{item['tamanho']} | {item['cor']}")
                    with col2:
                        st.write(f"Qtd: {item['quantidade']}")
                    with col3:
                        st.write(f"R$ {item['preco_unitario']:.2f}")
                    with col4:
                        st.write(f"R$ {item['subtotal']:.2f}")
                    with col5:
                        if st.button("❌", key=f"del_venda_{i}"):
                            st.session_state.itens_venda.pop(i)
                            st.rerun()
                
                st.success(f"**💰 Total: R$ {total_venda:.2f}**")
                
                # Finalizar venda
                col1, col2 = st.columns(2)
                with col1:
                    data_entrega = st.date_input("📅 Entrega Prevista", min_value=date.today(), key="venda_entrega")
                    forma_pagamento = st.selectbox(
                        "💳 Pagamento",
                        ["Dinheiro", "Cartão", "PIX", "Transferência"],
                        key="venda_pagamento"
                    )
                with col2:
                    observacoes = st.text_area("📝 Observações", key="venda_obs")
                
                if st.button("✅ Finalizar Venda", type="primary", key="finalizar_venda"):
                    sucesso, resultado = adicionar_pedido_venda(
                        cliente_id, escola_id, st.session_state.itens_venda, 
                        data_entrega, forma_pagamento, observacoes
                    )
                    if sucesso:
                        st.success(f"✅ Venda #{resultado} realizada! Estoque atualizado.")
                        st.balloons()
                        del st.session_state.itens_venda
                        st.rerun()
                    else:
                        st.error(f"❌ Erro: {resultado}")
        else:
            st.warning("📦 Nenhum produto com estoque disponível para esta escola")

elif menu == "🏭 Produção":
    st.header("🏭 Pedidos de Produção (SEM Estoque)")
    st.info("💡 **PRODUÇÃO:** Cria novos produtos, NÃO usa estoque. Estoque é adicionado quando a produção é finalizada.")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Cadastre escolas primeiro")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            escola_producao = st.selectbox("🏫 Escola", [e['nome'] for e in escolas], key="producao_escola")
            escola_id = next(e['id'] for e in escolas if e['nome'] == escola_producao)
        
        with col2:
            prioridade = st.selectbox("🎯 Prioridade", ["Normal", "Alta", "Urgente"], key="producao_prioridade")
        
        # Todos os produtos da escola (mesmo sem estoque)
        produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            st.subheader("🏭 Adicionar Itens para Produção")
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                produto_selecionado = st.selectbox(
                    "Produto:",
                    [f"{p['nome']} - {p['tamanho']} - {p['cor']} (Custo: R$ {p['preco_custo']:.2f})" 
                     for p in produtos],
                    key="producao_produto"
                )
            with col2:
                quantidade = st.number_input("Qtd", min_value=1, value=10, key="producao_qtd")
            with col3:
                if st.button("➕ Add Item", use_container_width=True, key="add_producao"):
                    if 'itens_producao' not in st.session_state:
                        st.session_state.itens_producao = []
                    
                    produto_id = next(p['id'] for p in produtos 
                                    if f"{p['nome']} - {p['tamanho']} - {p['cor']} (Custo: R$ {p['preco_custo']:.2f})" == produto_selecionado)
                    produto = next(p for p in produtos if p['id'] == produto_id)
                    
                    item = {
                        'produto_id': produto_id,
                        'nome': produto['nome'],
                        'tamanho': produto['tamanho'],
                        'cor': produto['cor'],
                        'quantidade': quantidade,
                        'custo_unitario': produto['preco_custo'] or 0,
                        'custo_total': (produto['preco_custo'] or 0) * quantidade
                    }
                    st.session_state.itens_producao.append(item)
                    st.success("✅ Item adicionado à produção!")
                    st.rerun()
            
            # Itens da produção
            if 'itens_producao' in st.session_state and st.session_state.itens_producao:
                st.subheader("📋 Itens para Produção")
                total_itens = sum(item['quantidade'] for item in st.session_state.itens_producao)
                custo_total = sum(item['custo_total'] for item in st.session_state.itens_producao)
                
                for i, item in enumerate(st.session_state.itens_producao):
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                    with col1:
                        st.write(f"**{item['nome']}**")
                        st.write(f"{item['tamanho']} | {item['cor']}")
                    with col2:
                        st.write(f"Qtd: {item['quantidade']}")
                    with col3:
                        st.write(f"Custo: R$ {item['custo_unitario']:.2f}")
                    with col4:
                        st.write(f"Total: R$ {item['custo_total']:.2f}")
                    with col5:
                        if st.button("❌", key=f"del_prod_{i}"):
                            st.session_state.itens_producao.pop(i)
                            st.rerun()
                
                st.info(f"**📦 Total Itens: {total_itens} | 💰 Custo Estimado: R$ {custo_total:.2f}**")
                
                # Finalizar produção
                col1, col2 = st.columns(2)
                with col1:
                    data_entrega = st.date_input("📅 Previsão Entrega", min_value=date.today(), key="prod_entrega")
                with col2:
                    observacoes = st.text_area("📝 Observações Produção", key="prod_obs")
                
                if st.button("✅ Criar Pedido Produção", type="primary", key="criar_producao"):
                    sucesso, resultado = criar_pedido_producao(
                        escola_id, st.session_state.itens_producao, 
                        data_entrega, observacoes, prioridade
                    )
                    if sucesso:
                        st.success(f"✅ Pedido Produção #{resultado} criado! Itens em produção.")
                        st.balloons()
                        del st.session_state.itens_producao
                        st.rerun()
                    else:
                        st.error(f"❌ Erro: {resultado}")
        
        # Listar pedidos de produção
        st.header("📋 Pedidos de Produção Ativos")
        pedidos_producao = listar_pedidos_producao()
        
        if pedidos_producao:
            for pedido in pedidos_producao:
                with st.expander(f"🏭 Produção #{pedido['id']} - {pedido['escola_nome']} - {pedido['status']} - 📅 {pedido['data_entrega_prevista']}"):
                    detalhes = obter_detalhes_pedido_producao(pedido['id'])
                    
                    if detalhes:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Escola:** {detalhes['pedido']['escola_nome']}")
                            st.write(f"**Status:** {detalhes['pedido']['status']}")
                            st.write(f"**Prioridade:** {detalhes['pedido']['prioridade']}")
                            st.write(f"**Data Pedido:** {detalhes['pedido']['data_pedido']}")
                        
                        with col2:
                            st.write(f"**Previsão Entrega:** {detalhes['pedido']['data_entrega_prevista']}")
                            st.write(f"**Quantidade Total:** {detalhes['pedido']['quantidade_total']} itens")
                            st.write(f"**Custo Total:** R$ {detalhes['pedido']['custo_total']:.2f}")
                            if detalhes['pedido']['data_conclusao']:
                                st.write(f"**Concluído em:** {detalhes['pedido']['data_conclusao']}")
                        
                        # Itens da produção
                        st.subheader("📦 Itens em Produção")
                        for item in detalhes['itens']:
                            st.write(f"- {item['produto_nome']} - {item['tamanho']} - {item['cor']}: {item['quantidade']} unidades")
                        
                        # Botão para finalizar produção
                        if detalhes['pedido']['status'] == 'Em produção':
                            if st.button("✅ Finalizar Produção", key=f"finalizar_{pedido['id']}"):
                                sucesso, msg = finalizar_pedido_producao(pedido['id'])
                                if sucesso:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("🏭 Nenhum pedido de produção ativo")

elif menu == "👕 Produtos":
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    # 🔍 Sistema de busca
    st.subheader("🔍 Buscar Produtos")
    termo_busca = st.text_input("Digite nome, categoria ou cor do produto:")
    
    escola_selecionada_nome = st.selectbox(
        "🏫 Selecione a Escola:",
        [e['nome'] for e in escolas],
        key="produtos_escola"
    )
    escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada_nome)
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Produto", "📋 Produtos da Escola", "🔍 Resultados da Busca"])
    
    with tab1:
        st.header(f"➕ Novo Produto - {escola_selecionada_nome}")
        
        with st.form("novo_produto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("📝 Nome do produto*")
                categoria = st.selectbox("📂 Categoria*", categorias_produtos)
                tamanho = st.selectbox("📏 Tamanho*", todos_tamanhos)
                cor = st.text_input("🎨 Cor*", value="Branco")
            
            with col2:
                preco_custo = st.number_input("💰 Preço de Custo", min_value=0.0, value=0.0, step=0.01)
                preco_venda = st.number_input("💰 Preço de Venda*", min_value=0.0, value=29.90, step=0.01)
                estoque = st.number_input("📦 Estoque inicial*", min_value=0, value=10)
                descricao = st.text_area("📄 Descrição")
            
            if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
                if nome and cor and preco_venda > 0:
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, descricao, escola_id)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome, Cor e Preço de Venda")
    
    with tab2:
        st.header(f"📋 Produtos - {escola_selecionada_nome}")
        produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            dados = []
            for produto in produtos:
                margem = "N/A"
                if produto['preco_custo'] and produto['preco_custo'] > 0:
                    margem_lucro = ((produto['preco_venda'] - produto['preco_custo']) / produto['preco_custo']) * 100
                    margem = f"{margem_lucro:.1f}%"
                
                status_estoque = "✅" if produto['estoque'] >= 5 else "⚠️" if produto['estoque'] > 0 else "❌"
                
                dados.append({
                    'ID': produto['id'],
                    'Produto': produto['nome'],
                    'Categoria': produto['categoria'],
                    'Tamanho': produto['tamanho'],
                    'Cor': produto['cor'],
                    'Custo': f"R$ {produto['preco_custo']:.2f}" if produto['preco_custo'] else "N/A",
                    'Venda': f"R$ {produto['preco_venda']:.2f}",
                    'Margem': margem,
                    'Estoque': f"{status_estoque} {produto['estoque']}",
                    'Descrição': produto['descricao'] or 'N/A'
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info(f"👕 Nenhum produto cadastrado para {escola_selecionada_nome}")
    
    with tab3:
        if termo_busca:
            st.header("🔍 Resultados da Busca")
            resultados = buscar_produtos(termo_busca, escola_id)
            
            if resultados:
                st.success(f"📦 Encontrados {len(resultados)} produtos")
                for produto in resultados:
                    with st.expander(f"{produto['nome']} - {produto['tamanho']} - {produto['cor']}"):
                        st.write(f"**Categoria:** {produto['categoria']}")
                        st.write(f"**Preço Custo:** R$ {produto['preco_custo']:.2f}" if produto['preco_custo'] else "**Preço Custo:** N/A")
                        st.write(f"**Preço Venda:** R$ {produto['preco_venda']:.2f}")
                        st.write(f"**Estoque:** {produto['estoque']} unidades")
                        st.write(f"**Descrição:** {produto['descricao'] or 'N/A'}")

elif menu == "❓ Ajuda":
    st.header("❓ Sistema de Fardamentos - Documentação Completa")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Visão Geral", "🏭 Sistema Produção", "🛒 Sistema Vendas", "🎯 Como Usar"])
    
    with tab1:
        st.subheader("👕 SISTEMA DE FARDAMENTOS - FACTORY")
        st.write("""
        ### 🎯 **OBJETIVO DO SISTEMA**
        
        Sistema completo para **fábrica de uniformes escolares** que gerencia:
        
        - 🏭 **Produção interna** de roupas
        - 🛒 **Vendas diretas** para clientes
        - 📦 **Controle de estoque** inteligente
        - 🏫 **Organização por escolas**
        - 💰 **Gestão financeira** completa
        
        ### 🔄 **FLUXO DO SISTEMA**
        
        ```
        📋 CADASTROS
          ↓
        🏭 PRODUÇÃO (Cria estoque)
          ↓
        📦 ESTOQUE (Produtos prontos)  
          ↓
        🛒 VENDAS (Usa estoque)
          ↓
        💰 RELATÓRIOS (Análise)
        ```
        
        ### 👥 **PERFIS DE USUÁRIO**
        
        - **Admin**: Acesso total ao sistema
        - **Vendedor**: Apenas vendas e clientes
        - **Produção**: Apenas controle de produção
        """)
    
    with tab2:
        st.subheader("🏭 SISTEMA DE PRODUÇÃO")
        st.write("""
        ### 🎯 **PARA QUE SERVE?**
        
        A produção é onde você **CRIA** novos produtos. Use quando:
        
        - ✂️ Precisa fabricar roupas novas
        - 📦 Estoque está baixo
        - 🎯 Tem pedidos específicos para produzir
        
        ### 🔄 **COMO FUNCIONA?**
        
        1. **Cria pedido de produção** → Não mexe no estoque
        2. **Produz os itens** → Em andamento
        3. **Finaliza produção** → **ESTOQUE É AUMENTADO**
        4. **Itens ficam disponíveis** para venda
        
        ### ⚠️ **IMPORTANTE**
        
        - ✅ Produção **ADICIONA** ao estoque quando finalizada
        - ❌ Produção **NÃO USA** estoque existente
        - 📊 Custo calculado automaticamente
        """)
    
    with tab3:
        st.subheader("🛒 SISTEMA DE VENDAS")  
        st.write("""
        ### 🎯 **PARA QUE SERVE?**
        
        As vendas são para **COMERCIALIZAR** produtos prontos. Use quando:
        
        - 🎒 Cliente quer comprar uniformes
        - 📦 Produtos já estão prontos em estoque
        - 🏫 Escola precisa repor estoque
        
        ### 🔄 **COMO FUNCIONA?**
        
        1. **Seleciona produtos** com estoque disponível
        2. **Cria pedido de venda** → **ESTOQUE É REDUZIDO**
        3. **Entrega para cliente** → Pedido concluído
        
        ### ⚠️ **IMPORTANTE**
        
        - ✅ Vendas **REDUZEM** estoque imediatamente
        - ❌ Só vende produtos com estoque disponível
        - 💰 Preço de venda (não custo)
        """)
    
    with tab4:
        st.subheader("🎯 COMO COMEÇAR?")
        st.write("""
        ### 📋 **PRIMEIROS PASSOS**
        
        1. **Cadastre as Escolas**
           - Vá em "👕 Produtos"
           - Cadastre Municipal, Desperta, São Tadeu
        
        2. **Cadastre Produtos**  
           - Defina preço de custo e venda
           - Associe cada produto a uma escola
        
        3. **Cadastre Clientes**
           - Informações básicas dos compradores
        
        ### 🏭 **QUANDO USAR PRODUÇÃO?**
        
        ```python
        # Use produção quando:
        - 🆕 Precisa fazer roupas novas
        - 📉 Estoque está acabando  
        - 🎯 Pedido especial da escola
        ```
        
        ### 🛒 **QUANDO USAR VENDAS?**
        
        ```python
        # Use vendas quando:
        - ✅ Produtos já estão prontos
        - 🏪 Cliente quer comprar agora
        - 📦 Tem estoque disponível
        ```
        
        ### 🔧 **SUPORTE**
        
        - 📧 Email: suporte@fardamentos.com
        - 📞 WhatsApp: (11) 99999-9999
        - 🕒 Horário: Seg-Sex, 8h-18h
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
