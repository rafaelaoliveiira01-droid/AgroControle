from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.secret_key = "projeto-agro-chave"

DATABASE = "banco.db"

UPLOAD_FOLDER = os.path.join("static", "uploads", "perfis")

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# BANCO DE DADOS
# =========================================================

def conectar_banco():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def criar_banco():

    conn = conectar_banco()

    cur = conn.cursor()

    # =====================================================
    # DEFENSIVOS
    # =====================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS defensivos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL,

            carencia INTEGER NOT NULL DEFAULT 0,

            estoque REAL NOT NULL DEFAULT 0,

            categoria TEXT,

            fabricante TEXT,

            unidade TEXT,

            validade TEXT
        )
    """)

    # Compatibilidade com bancos antigos
    colunas_defensivos = [
        row["name"]
        for row in cur.execute(
            "PRAGMA table_info(defensivos)"
        ).fetchall()
    ]

    novas_colunas_defensivos = [
        ("categoria", "TEXT"),
        ("fabricante", "TEXT"),
        ("unidade", "TEXT"),
        ("validade", "TEXT")
    ]

    for coluna, tipo in novas_colunas_defensivos:

        if coluna not in colunas_defensivos:

            cur.execute(
                f"ALTER TABLE defensivos ADD COLUMN {coluna} {tipo}"
            )

    # =====================================================
    # TALHÕES
    # =====================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS talhoes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL
        )
    """)

    # =====================================================
    # APLICAÇÕES
    # =====================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS aplicacoes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            defensivo_id INTEGER NOT NULL,

            talhao_id INTEGER NOT NULL,

            data_aplicacao TEXT NOT NULL,

            quantidade REAL NOT NULL,

            responsavel TEXT NOT NULL,

            data_liberacao TEXT,

            FOREIGN KEY (defensivo_id)
                REFERENCES defensivos(id)
                ON DELETE CASCADE,

            FOREIGN KEY (talhao_id)
                REFERENCES talhoes(id)
                ON DELETE CASCADE
        )
    """)

    # =====================================================
    # USUÁRIOS
    # =====================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            senha TEXT NOT NULL,

            foto TEXT,

            nota TEXT,

            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # COMPATIBILIDADE COM BANCO ANTIGO - USUÁRIOS
    # =====================================================

    colunas_usuarios = [
        row["name"]
        for row in cur.execute(
            "PRAGMA table_info(usuarios)"
        ).fetchall()
    ]

    novas_colunas_usuarios = [
        ("nome", "TEXT"),
        ("email", "TEXT"),
        ("senha", "TEXT"),
        ("foto", "TEXT"),
        ("nota", "TEXT"),
        ("criado_em", "TEXT")
    ]

    for coluna, tipo in novas_colunas_usuarios:

        if coluna not in colunas_usuarios:

            cur.execute(
                f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}"
            )

    # =====================================================
    # DADOS INICIAIS DOS DEFENSIVOS
    # =====================================================

    quantidade_defensivos = cur.execute(
        "SELECT COUNT(*) FROM defensivos"
    ).fetchone()[0]

    if quantidade_defensivos == 0:

        cur.executemany("""
            INSERT INTO defensivos
            (
                nome,
                carencia,
                estoque,
                categoria,
                fabricante,
                unidade,
                validade
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [

            (
                "Glifosato",
                14,
                100,
                "Herbicida",
                "AgroQuímica",
                "Litros (L)",
                "2027-12-31"
            ),

            (
                "Fungicida X",
                7,
                50,
                "Fungicida",
                "Campo Forte",
                "Litros (L)",
                "2027-08-30"
            ),

            (
                "Inseticida Y",
                10,
                30,
                "Inseticida",
                "RuralTech",
                "Litros (L)",
                "2027-06-15"
            )
        ])

    # =====================================================
    # TALHÕES INICIAIS
    # =====================================================

    quantidade_talhoes = cur.execute(
        "SELECT COUNT(*) FROM talhoes"
    ).fetchone()[0]

    if quantidade_talhoes == 0:

        cur.executemany(
            "INSERT INTO talhoes (nome) VALUES (?)",
            [
                ("Talhão A",),
                ("Talhão B",),
                ("Talhão C",)
            ]
        )

    conn.commit()

    conn.close()


# =========================================================
# USUÁRIO LOGADO
# =========================================================

def usuario_atual():

    usuario_id = session.get("usuario_id")

    if not usuario_id:
        return None

    conn = conectar_banco()

    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (usuario_id,)
    ).fetchone()

    conn.close()

    return usuario


# =========================================================
# VARIÁVEIS DISPONÍVEIS EM TODOS OS HTMLS
# =========================================================

@app.context_processor
def contexto_global():

    return {
        "usuario_logado": usuario_atual(),
        "now_date": datetime.now().strftime("%Y-%m-%d")
    }


# =========================================================
# PROTEÇÃO DAS PÁGINAS
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("usuario_id"):

            flash(
                "Faça login para acessar o AgroControl.",
                "erro"
            )

            return redirect(
                url_for(
                    "login",
                    proxima=request.path
                )
            )

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# EXTENSÃO DE FOTO
# =========================================================

def extensao_permitida(nome):

    return (
        "." in nome
        and
        nome.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("usuario_id"):

        return redirect(
            url_for("index")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        senha = request.form.get(
            "senha",
            ""
        )

        conn = conectar_banco()

        usuario = conn.execute(
            """
            SELECT *
            FROM usuarios
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if (
            not usuario
            or
            not check_password_hash(
                usuario["senha"],
                senha
            )
        ):

            flash(
                "E-mail ou senha incorretos.",
                "erro"
            )

            return render_template(
                "login.html"
            )

        session["usuario_id"] = usuario["id"]

        flash(
            f"Bem-vinda, {usuario['nome']}!",
            "sucesso"
        )

        return redirect(
            url_for("index")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# CADASTRO DE USUÁRIO
# =========================================================

@app.route(
    "/cadastro-usuario",
    methods=["GET", "POST"]
)
def cadastro_usuario():

    if session.get("usuario_id"):

        return redirect(
            url_for("index")
        )

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        senha = request.form.get(
            "senha",
            ""
        )

        confirmar = request.form.get(
            "confirmar_senha",
            ""
        )

        if not nome or not email or not senha:

            flash(
                "Preencha todos os campos.",
                "erro"
            )

            return render_template(
                "cadastro_usuario.html"
            )

        if senha != confirmar:

            flash(
                "As senhas não coincidem.",
                "erro"
            )

            return render_template(
                "cadastro_usuario.html"
            )

        if len(senha) < 6:

            flash(
                "A senha deve ter pelo menos 6 caracteres.",
                "erro"
            )

            return render_template(
                "cadastro_usuario.html"
            )

        conn = conectar_banco()

        try:

            cursor = conn.execute(
                """
                INSERT INTO usuarios
                (
                    nome,
                    email,
                    senha
                )

                VALUES (?, ?, ?)
                """,
                (
                    nome,
                    email,
                    generate_password_hash(senha)
                )
            )

            conn.commit()

            session["usuario_id"] = cursor.lastrowid

            flash(
                "Cadastro realizado com sucesso!",
                "sucesso"
            )

            return redirect(
                url_for("index")
            )

        except sqlite3.IntegrityError:

            flash(
                "Este e-mail já está cadastrado.",
                "erro"
            )

        finally:

            conn.close()

    return render_template(
        "cadastro_usuario.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Você saiu da conta.",
        "sucesso"
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# MEU PERFIL
# =========================================================

@app.route("/perfil")
@login_required
def perfil():

    usuario = usuario_atual()

    return render_template(
        "perfil.html",
        usuario=usuario
    )


# =========================================================
# EDITAR MEU PERFIL
# =========================================================

@app.route(
    "/editar-perfil",
    methods=["GET", "POST"]
)
@login_required
def editar_perfil():

    usuario = usuario_atual()

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        # Esta nota pertence somente ao usuário logado.
        nota = request.form.get(
            "nota",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )

        foto = request.files.get(
            "foto"
        )

        if not nome or not email:

            flash(
                "Nome e e-mail são obrigatórios.",
                "erro"
            )

            return render_template(
                "editar_perfil.html",
                usuario=usuario
            )

        conn = conectar_banco()

        existente = conn.execute(
            """
            SELECT id
            FROM usuarios
            WHERE email = ?
            AND id != ?
            """,
            (
                email,
                usuario["id"]
            )
        ).fetchone()

        if existente:

            conn.close()

            flash(
                "Este e-mail já pertence a outro usuário.",
                "erro"
            )

            return render_template(
                "editar_perfil.html",
                usuario=usuario
            )

        nome_foto = usuario["foto"]

        # =================================================
        # FOTO DE PERFIL
        # =================================================

        if foto and foto.filename:

            if not extensao_permitida(
                foto.filename
            ):

                conn.close()

                flash(
                    "Formato de foto não permitido. "
                    "Use PNG, JPG, JPEG ou WEBP.",
                    "erro"
                )

                return render_template(
                    "editar_perfil.html",
                    usuario=usuario
                )

            nome_seguro = secure_filename(
                foto.filename
            )

            nome_foto = (
                f"usuario_"
                f"{usuario['id']}_"
                f"{int(datetime.now().timestamp())}_"
                f"{nome_seguro}"
            )

            caminho_foto = os.path.join(
                app.config["UPLOAD_FOLDER"],
                nome_foto
            )

            foto.save(
                caminho_foto
            )

        # =================================================
        # ALTERAR SENHA
        # =================================================

        if senha:

            if len(senha) < 6:

                conn.close()

                flash(
                    "A nova senha deve ter pelo menos 6 caracteres.",
                    "erro"
                )

                return render_template(
                    "editar_perfil.html",
                    usuario=usuario
                )

            conn.execute(
                """
                UPDATE usuarios

                SET
                    nome = ?,
                    email = ?,
                    senha = ?,
                    foto = ?,
                    nota = ?

                WHERE id = ?
                """,
                (
                    nome,
                    email,
                    generate_password_hash(senha),
                    nome_foto,
                    nota,
                    usuario["id"]
                )
            )

        else:

            conn.execute(
                """
                UPDATE usuarios

                SET
                    nome = ?,
                    email = ?,
                    foto = ?,
                    nota = ?

                WHERE id = ?
                """,
                (
                    nome,
                    email,
                    nome_foto,
                    nota,
                    usuario["id"]
                )
            )

        conn.commit()

        conn.close()

        flash(
            "Perfil atualizado com sucesso.",
            "sucesso"
        )

        return redirect(
            url_for("perfil")
        )

    return render_template(
        "editar_perfil.html",
        usuario=usuario
    )


# =========================================================
# EXCLUIR MEU PERFIL
# =========================================================

@app.route(
    "/excluir-perfil",
    methods=["POST"]
)
@login_required
def excluir_perfil():

    usuario = usuario_atual()

    conn = conectar_banco()

    conn.execute(
        """
        DELETE FROM usuarios
        WHERE id = ?
        """,
        (usuario["id"],)
    )

    conn.commit()

    conn.close()

    session.clear()

    flash(
        "Seu perfil foi excluído.",
        "sucesso"
    )

    return redirect(
        url_for("cadastro_usuario")
    )


# =========================================================
# LISTA DE USUÁRIOS
# =========================================================
# IMPORTANTE:
# Esta página mostra apenas os usuários cadastrados.
# A nota NÃO é enviada para o HTML.
# =========================================================

@app.route("/usuarios")
@login_required
def usuarios():

    conn = conectar_banco()

    lista = conn.execute(
        """
        SELECT
            id,
            nome,
            email,
            foto,
            criado_em

        FROM usuarios

        ORDER BY nome
        """
    ).fetchall()

    conn.close()

    return render_template(
        "usuarios.html",
        usuarios=lista
    )


# =========================================================
# PÁGINA INICIAL
# =========================================================

@app.route("/")
@login_required
def index():

    conn = conectar_banco()

    defensivos = conn.execute(
        """
        SELECT *
        FROM defensivos
        ORDER BY nome
        """
    ).fetchall()

    total_defensivos = conn.execute(
        """
        SELECT COUNT(*)
        FROM defensivos
        """
    ).fetchone()[0]

    estoque_total = conn.execute(
        """
        SELECT COALESCE(SUM(estoque), 0)
        FROM defensivos
        """
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        defensivos=defensivos,
        total_defensivos=total_defensivos,
        estoque_total=estoque_total
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = conectar_banco()

    total_defensivos = conn.execute(
        """
        SELECT COUNT(*)
        FROM defensivos
        """
    ).fetchone()[0]

    total_talhoes = conn.execute(
        """
        SELECT COUNT(*)
        FROM talhoes
        """
    ).fetchone()[0]

    total_aplicacoes = conn.execute(
        """
        SELECT COUNT(*)
        FROM aplicacoes
        """
    ).fetchone()[0]

    estoque_total = conn.execute(
        """
        SELECT COALESCE(SUM(estoque), 0)
        FROM defensivos
        """
    ).fetchone()[0]

    baixo_estoque = conn.execute(
        """
        SELECT COUNT(*)
        FROM defensivos
        WHERE estoque < 20
        """
    ).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        total_defensivos=total_defensivos,
        total_talhoes=total_talhoes,
        total_aplicacoes=total_aplicacoes,
        estoque_total=estoque_total,
        baixo_estoque=baixo_estoque
    )


# =========================================================
# ESTOQUE
# =========================================================

@app.route("/estoque")
@login_required
def estoque():

    conn = conectar_banco()

    defensivos = conn.execute(
        """
        SELECT *
        FROM defensivos
        ORDER BY nome
        """
    ).fetchall()

    conn.close()

    return render_template(
        "estoque.html",
        defensivos=defensivos
    )


# =========================================================
# NOVA APLICAÇÃO
# =========================================================

@app.route(
    "/cadastro",
    methods=["GET", "POST"]
)
@login_required
def cadastro():

    conn = conectar_banco()

    defensivos = conn.execute(
        """
        SELECT *
        FROM defensivos
        ORDER BY nome
        """
    ).fetchall()

    talhoes = conn.execute(
        """
        SELECT *
        FROM talhoes
        ORDER BY nome
        """
    ).fetchall()

    if request.method == "POST":

        defensivo_id = request.form.get(
            "defensivo_id"
        )

        talhao_id = request.form.get(
            "talhao_id"
        )

        data_aplicacao = request.form.get(
            "data_aplicacao"
        )

        quantidade = request.form.get(
            "quantidade"
        )

        responsavel = request.form.get(
            "responsavel",
            ""
        ).strip()

        try:

            quantidade_num = float(
                quantidade
            )

        except (TypeError, ValueError):

            quantidade_num = -1

        defensivo = conn.execute(
            """
            SELECT *
            FROM defensivos
            WHERE id = ?
            """,
            (defensivo_id,)
        ).fetchone()

        if (
            not defensivo
            or quantidade_num <= 0
            or not data_aplicacao
            or not responsavel
        ):

            conn.close()

            flash(
                "Preencha os dados corretamente.",
                "erro"
            )

            return render_template(
                "cadastro.html",
                defensivos=defensivos,
                talhoes=talhoes
            )

        if quantidade_num > defensivo["estoque"]:

            conn.close()

            flash(
                "A quantidade da aplicação é maior "
                "que o estoque disponível.",
                "erro"
            )

            return render_template(
                "cadastro.html",
                defensivos=defensivos,
                talhoes=talhoes
            )

        data_liberacao = (
            datetime.strptime(
                data_aplicacao,
                "%Y-%m-%d"
            )
            +
            timedelta(
                days=int(
                    defensivo["carencia"] or 0
                )
            )
        ).strftime("%Y-%m-%d")

        conn.execute(
            """
            INSERT INTO aplicacoes
            (
                defensivo_id,
                talhao_id,
                data_aplicacao,
                quantidade,
                responsavel,
                data_liberacao
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                defensivo_id,
                talhao_id,
                data_aplicacao,
                quantidade_num,
                responsavel,
                data_liberacao
            )
        )

        conn.execute(
            """
            UPDATE defensivos

            SET estoque = estoque - ?

            WHERE id = ?
            """,
            (
                quantidade_num,
                defensivo_id
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Aplicação cadastrada com sucesso.",
            "sucesso"
        )

        return redirect(
            url_for("aplicacoes")
        )

    conn.close()

    return render_template(
        "cadastro.html",
        defensivos=defensivos,
        talhoes=talhoes
    )


# =========================================================
# CADASTRO DE DEFENSIVO
# =========================================================

@app.route(
    "/cadastro-produto",
    methods=["GET", "POST"]
)
@login_required
def cadastro_produto():

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        categoria = request.form.get(
            "categoria",
            ""
        ).strip()

        fabricante = request.form.get(
            "fabricante",
            ""
        ).strip()

        quantidade = request.form.get(
            "quantidade",
            "0"
        )

        unidade = request.form.get(
            "unidade",
            ""
        ).strip()

        validade = request.form.get(
            "validade",
            ""
        )

        carencia = request.form.get(
            "carencia",
            "0"
        )

        try:

            quantidade = float(
                quantidade
            )

            carencia = int(
                carencia
            )

        except ValueError:

            flash(
                "Quantidade ou carência inválida.",
                "erro"
            )

            return render_template(
                "cadastro_produto.html"
            )

        if (
            not nome
            or quantidade < 0
            or carencia < 0
        ):

            flash(
                "Preencha os dados obrigatórios corretamente.",
                "erro"
            )

            return render_template(
                "cadastro_produto.html"
            )

        conn = conectar_banco()

        conn.execute(
            """
            INSERT INTO defensivos
            (
                nome,
                carencia,
                estoque,
                categoria,
                fabricante,
                unidade,
                validade
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                carencia,
                quantidade,
                categoria,
                fabricante,
                unidade,
                validade
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Defensivo cadastrado com sucesso.",
            "sucesso"
        )

        return redirect(
            url_for("estoque")
        )

    return render_template(
        "cadastro_produto.html"
    )


# =========================================================
# EDITAR DEFENSIVO
# =========================================================

@app.route(
    "/editar-defensivo/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def editar_defensivo(id):

    conn = conectar_banco()

    defensivo = conn.execute(
        """
        SELECT *
        FROM defensivos
        WHERE id = ?
        """,
        (id,)
    ).fetchone()

    if not defensivo:

        conn.close()

        flash(
            "Defensivo não encontrado.",
            "erro"
        )

        return redirect(
            url_for("estoque")
        )

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        categoria = request.form.get(
            "categoria",
            ""
        ).strip()

        fabricante = request.form.get(
            "fabricante",
            ""
        ).strip()

        quantidade = request.form.get(
            "quantidade",
            "0"
        )

        unidade = request.form.get(
            "unidade",
            ""
        ).strip()

        validade = request.form.get(
            "validade",
            ""
        )

        carencia = request.form.get(
            "carencia",
            "0"
        )

        try:

            quantidade = float(
                quantidade
            )

            carencia = int(
                carencia
            )

        except ValueError:

            conn.close()

            flash(
                "Quantidade ou carência inválida.",
                "erro"
            )

            return render_template(
                "editar_defensivo.html",
                defensivo=defensivo
            )

        conn.execute(
            """
            UPDATE defensivos

            SET
                nome = ?,
                categoria = ?,
                fabricante = ?,
                estoque = ?,
                unidade = ?,
                validade = ?,
                carencia = ?

            WHERE id = ?
            """,
            (
                nome,
                categoria,
                fabricante,
                quantidade,
                unidade,
                validade,
                carencia,
                id
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Defensivo atualizado com sucesso.",
            "sucesso"
        )

        return redirect(
            url_for("estoque")
        )

    conn.close()

    return render_template(
        "editar_defensivo.html",
        defensivo=defensivo
    )


# =========================================================
# EXCLUIR DEFENSIVO
# =========================================================

@app.route(
    "/excluir-defensivo/<int:id>",
    methods=["POST"]
)
@login_required
def excluir_defensivo(id):

    conn = conectar_banco()

    conn.execute(
        """
        DELETE FROM defensivos
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()

    conn.close()

    flash(
        "Defensivo excluído.",
        "sucesso"
    )

    return redirect(
        url_for("estoque")
    )


# =========================================================
# APLICAÇÕES
# =========================================================

@app.route("/aplicacoes")
@login_required
def aplicacoes():

    conn = conectar_banco()

    registros = conn.execute(
        """
        SELECT
            a.*,
            d.nome AS defensivo,
            d.carencia,
            t.nome AS talhao

        FROM aplicacoes a

        JOIN defensivos d
            ON d.id = a.defensivo_id

        JOIN talhoes t
            ON t.id = a.talhao_id

        ORDER BY
            a.data_aplicacao DESC,
            a.id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "aplicacoes.html",
        aplicacoes=registros
    )


# =========================================================
# EDITAR APLICAÇÃO
# =========================================================

@app.route(
    "/editar-aplicacao/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def editar_aplicacao(id):

    conn = conectar_banco()

    aplicacao = conn.execute(
        """
        SELECT
            a.*,
            d.nome AS defensivo,
            t.nome AS talhao

        FROM aplicacoes a

        JOIN defensivos d
            ON d.id = a.defensivo_id

        JOIN talhoes t
            ON t.id = a.talhao_id

        WHERE a.id = ?
        """,
        (id,)
    ).fetchone()

    defensivos = conn.execute(
        """
        SELECT *
        FROM defensivos
        ORDER BY nome
        """
    ).fetchall()

    talhoes = conn.execute(
        """
        SELECT *
        FROM talhoes
        ORDER BY nome
        """
    ).fetchall()

    if not aplicacao:

        conn.close()

        flash(
            "Aplicação não encontrada.",
            "erro"
        )

        return redirect(
            url_for("aplicacoes")
        )

    if request.method == "POST":

        defensivo_id = request.form.get(
            "defensivo_id"
        )

        talhao_id = request.form.get(
            "talhao_id"
        )

        data_aplicacao = request.form.get(
            "data_aplicacao"
        )

        try:

            quantidade = float(
                request.form.get(
                    "quantidade",
                    0
                )
            )

        except ValueError:

            quantidade = 0

        responsavel = request.form.get(
            "responsavel",
            ""
        ).strip()

        novo_defensivo = conn.execute(
            """
            SELECT *
            FROM defensivos
            WHERE id = ?
            """,
            (defensivo_id,)
        ).fetchone()

        if (
            not novo_defensivo
            or quantidade <= 0
            or not responsavel
        ):

            conn.close()

            flash(
                "Preencha os dados corretamente.",
                "erro"
            )

            return render_template(
                "editar_aplicacao.html",
                aplicacao=aplicacao,
                defensivos=defensivos,
                talhoes=talhoes
            )

        # Devolve a quantidade antiga ao estoque
        conn.execute(
            """
            UPDATE defensivos

            SET estoque = estoque + ?

            WHERE id = ?
            """,
            (
                aplicacao["quantidade"],
                aplicacao["defensivo_id"]
            )
        )

        estoque_disponivel = (
            novo_defensivo["estoque"]
            +
            (
                aplicacao["quantidade"]
                if novo_defensivo["id"]
                ==
                aplicacao["defensivo_id"]
                else 0
            )
        )

        if quantidade > estoque_disponivel:

            conn.rollback()

            conn.close()

            flash(
                "Estoque insuficiente para esta alteração.",
                "erro"
            )

            return render_template(
                "editar_aplicacao.html",
                aplicacao=aplicacao,
                defensivos=defensivos,
                talhoes=talhoes
            )

        data_liberacao = (
            datetime.strptime(
                data_aplicacao,
                "%Y-%m-%d"
            )
            +
            timedelta(
                days=int(
                    novo_defensivo["carencia"] or 0
                )
            )
        ).strftime("%Y-%m-%d")

        conn.execute(
            """
            UPDATE aplicacoes

            SET
                defensivo_id = ?,
                talhao_id = ?,
                data_aplicacao = ?,
                quantidade = ?,
                responsavel = ?,
                data_liberacao = ?

            WHERE id = ?
            """,
            (
                defensivo_id,
                talhao_id,
                data_aplicacao,
                quantidade,
                responsavel,
                data_liberacao,
                id
            )
        )

        conn.execute(
            """
            UPDATE defensivos

            SET estoque = estoque - ?

            WHERE id = ?
            """,
            (
                quantidade,
                defensivo_id
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Aplicação atualizada com sucesso.",
            "sucesso"
        )

        return redirect(
            url_for("aplicacoes")
        )

    conn.close()

    return render_template(
        "editar_aplicacao.html",
        aplicacao=aplicacao,
        defensivos=defensivos,
        talhoes=talhoes
    )


# =========================================================
# EXCLUIR APLICAÇÃO
# =========================================================

@app.route(
    "/excluir-aplicacao/<int:id>",
    methods=["POST"]
)
@login_required
def excluir_aplicacao(id):

    conn = conectar_banco()

    aplicacao = conn.execute(
        """
        SELECT *
        FROM aplicacoes
        WHERE id = ?
        """,
        (id,)
    ).fetchone()

    if aplicacao:

        conn.execute(
            """
            UPDATE defensivos

            SET estoque = estoque + ?

            WHERE id = ?
            """,
            (
                aplicacao["quantidade"],
                aplicacao["defensivo_id"]
            )
        )

        conn.execute(
            """
            DELETE FROM aplicacoes
            WHERE id = ?
            """,
            (id,)
        )

        conn.commit()

    conn.close()

    flash(
        "Aplicação excluída.",
        "sucesso"
    )

    return redirect(
        url_for("aplicacoes")
    )


# =========================================================
# RASTREABILIDADE
# =========================================================

@app.route("/rastreabilidade")
@login_required
def rastreabilidade():

    conn = conectar_banco()

    registros = conn.execute(
        """
        SELECT
            a.*,
            d.nome AS defensivo,
            d.carencia,
            t.nome AS talhao

        FROM aplicacoes a

        JOIN defensivos d
            ON d.id = a.defensivo_id

        JOIN talhoes t
            ON t.id = a.talhao_id

        ORDER BY
            a.data_aplicacao DESC,
            a.id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "rastreabilidade.html",
        aplicacoes=registros
    )


# =========================================================
# EDITAR TALHÃO
# =========================================================

@app.route(
    "/editar-talao/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def editar_talhao(id):

    conn = conectar_banco()

    talhao = conn.execute(
        """
        SELECT *
        FROM talhoes
        WHERE id = ?
        """,
        (id,)
    ).fetchone()

    if not talhao:

        conn.close()

        flash(
            "Talhão não encontrado.",
            "erro"
        )

        return redirect(
            url_for("rastreabilidade")
        )

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        if nome:

            conn.execute(
                """
                UPDATE talhoes

                SET nome = ?

                WHERE id = ?
                """,
                (
                    nome,
                    id
                )
            )

            conn.commit()

            conn.close()

            flash(
                "Talhão atualizado.",
                "sucesso"
            )

            return redirect(
                url_for("rastreabilidade")
            )

    conn.close()

    return render_template(
        "editar_talhao.html",
        talhao=talhao
    )


# =========================================================
# EXCLUIR TALHÃO
# =========================================================

@app.route(
    "/excluir-talao/<int:id>",
    methods=["POST"]
)
@login_required
def excluir_talao(id):

    conn = conectar_banco()

    conn.execute(
        """
        DELETE FROM talhoes
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()

    conn.close()

    flash(
        "Talhão excluído.",
        "sucesso"
    )

    return redirect(
        url_for("rastreabilidade")
    )


# =========================================================
# INICIAR SISTEMA
# =========================================================

if __name__ == "__main__":

    criar_banco()

    app.run(
        debug=True
    )