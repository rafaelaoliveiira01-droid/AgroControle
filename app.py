from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta


app = Flask(__name__)

app.secret_key = "projeto-agro-chave"

DATABASE = "banco.db"


# ==========================================
# CONEXÃO COM O BANCO
# ==========================================

def conectar_banco():

    conexao = sqlite3.connect(DATABASE)

    conexao.row_factory = sqlite3.Row

    return conexao


# ==========================================
# CRIAÇÃO E ATUALIZAÇÃO DO BANCO
# ==========================================

def criar_banco():

    conexao = conectar_banco()

    cursor = conexao.cursor()


    # ======================================
    # TABELA DE DEFENSIVOS
    # ======================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defensivos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL,

            carencia INTEGER NOT NULL,

            estoque REAL NOT NULL

        )
    """)


    # ======================================
    # VERIFICA NOVAS COLUNAS
    # ======================================

    colunas = conexao.execute(
        "PRAGMA table_info(defensivos)"
    ).fetchall()


    nomes_colunas = [

        coluna["name"]

        for coluna in colunas

    ]


    if "categoria" not in nomes_colunas:

        conexao.execute("""
            ALTER TABLE defensivos
            ADD COLUMN categoria TEXT
        """)


    if "fabricante" not in nomes_colunas:

        conexao.execute("""
            ALTER TABLE defensivos
            ADD COLUMN fabricante TEXT
        """)


    if "unidade" not in nomes_colunas:

        conexao.execute("""
            ALTER TABLE defensivos
            ADD COLUMN unidade TEXT
        """)


    if "validade" not in nomes_colunas:

        conexao.execute("""
            ALTER TABLE defensivos
            ADD COLUMN validade TEXT
        """)


    # ======================================
    # TABELA DE TALHÕES
    # ======================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS talhoes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL

        )
    """)


    # ======================================
    # TABELA DE APLICAÇÕES
    # ======================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aplicacoes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            defensivo_id INTEGER NOT NULL,

            talhao_id INTEGER NOT NULL,

            data_aplicacao TEXT NOT NULL,

            quantidade REAL NOT NULL,

            responsavel TEXT NOT NULL,

            data_liberacao TEXT NOT NULL,

            FOREIGN KEY (defensivo_id)
                REFERENCES defensivos(id),

            FOREIGN KEY (talhao_id)
                REFERENCES talhoes(id)

        )
    """)


    # ======================================
    # DEFENSIVOS DE EXEMPLO
    # ======================================

    quantidade_defensivos = cursor.execute(
        "SELECT COUNT(*) FROM defensivos"
    ).fetchone()[0]


    if quantidade_defensivos == 0:

        cursor.execute("""
            INSERT INTO defensivos
            (
                nome,
                carencia,
                estoque
            )

            VALUES

            (
                'Defensivo VerdeMax',
                14,
                100
            ),

            (
                'Defensivo AgroSafe',
                7,
                80
            ),

            (
                'Defensivo Campo Forte',
                21,
                120
            )
        """)


    # ======================================
    # TALHÕES DE EXEMPLO
    # ======================================

    quantidade_talhoes = cursor.execute(
        "SELECT COUNT(*) FROM talhoes"
    ).fetchone()[0]


    if quantidade_talhoes == 0:

        cursor.execute("""
            INSERT INTO talhoes
            (
                nome
            )

            VALUES

            ('Talhão 01'),

            ('Talhão 02'),

            ('Talhão 03')
        """)


    conexao.commit()

    conexao.close()


# ==========================================
# PÁGINA INICIAL
# ==========================================

@app.route("/")
def index():

    conexao = conectar_banco()


    defensivos = conexao.execute("""
        SELECT *
        FROM defensivos
        ORDER BY nome
    """).fetchall()


    aplicacoes = conexao.execute("""
        SELECT

            aplicacoes.*,

            defensivos.nome AS defensivo,

            talhoes.nome AS talhao,

            defensivos.carencia

        FROM aplicacoes

        INNER JOIN defensivos

            ON aplicacoes.defensivo_id = defensivos.id

        INNER JOIN talhoes

            ON aplicacoes.talhao_id = talhoes.id

        ORDER BY aplicacoes.id DESC

    """).fetchall()


    conexao.close()


    hoje = datetime.now().date()


    dados_aplicacoes = []


    for aplicacao in aplicacoes:

        data_liberacao = datetime.strptime(
            aplicacao["data_liberacao"],
            "%Y-%m-%d"
        ).date()


        if hoje < data_liberacao:

            status = "aguardando"

            mensagem = "Colheita ainda não liberada"

        else:

            status = "liberada"

            mensagem = "Colheita liberada"


        dados_aplicacoes.append({

            "id": aplicacao["id"],

            "defensivo": aplicacao["defensivo"],

            "talhao": aplicacao["talhao"],

            "data_aplicacao":
                aplicacao["data_aplicacao"],

            "quantidade":
                aplicacao["quantidade"],

            "responsavel":
                aplicacao["responsavel"],

            "data_liberacao":
                aplicacao["data_liberacao"],

            "status": status,

            "mensagem": mensagem

        })


    return render_template(

        "index.html",

        defensivos=defensivos,

        aplicacoes=dados_aplicacoes

    )


# ==========================================
# CADASTRO DE APLICAÇÃO
# ==========================================

@app.route(
    "/cadastro",
    methods=["GET", "POST"]
)
def cadastro():

    conexao = conectar_banco()


    defensivos = conexao.execute("""
        SELECT *
        FROM defensivos
        ORDER BY nome
    """).fetchall()


    talhoes = conexao.execute("""
        SELECT *
        FROM talhoes
        ORDER BY nome
    """).fetchall()


    if request.method == "POST":

        try:

            defensivo_id = request.form[
                "defensivo_id"
            ]

            talhao_id = request.form[
                "talhao_id"
            ]

            data_aplicacao = request.form[
                "data_aplicacao"
            ]

            quantidade = float(
                request.form["quantidade"]
            )

            responsavel = request.form[
                "responsavel"
            ].strip()


        except (KeyError, ValueError):

            flash(
                "Preencha corretamente todos os campos!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro")
            )


        # ==================================
        # VALIDAÇÃO
        # ==================================

        if not data_aplicacao:

            flash(
                "Informe a data da aplicação!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro")
            )


        if not responsavel:

            flash(
                "Informe o responsável pela aplicação!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro")
            )


        if quantidade <= 0:

            flash(
                "Informe uma quantidade maior que zero!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro")
            )


        # ==================================
        # BUSCA DEFENSIVO
        # ==================================

        defensivo = conexao.execute(
            """
            SELECT *
            FROM defensivos
            WHERE id = ?
            """,
            (defensivo_id,)
        ).fetchone()


        if defensivo is None:

            flash(
                "Defensivo não encontrado!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro")
            )


        # ==================================
        # VERIFICA ESTOQUE
        # ==================================

        if quantidade > defensivo["estoque"]:

            flash(
                "Quantidade maior que o estoque disponível!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro")
            )


        # ==================================
        # CALCULA CARÊNCIA
        # ==================================

        try:

            data = datetime.strptime(
                data_aplicacao,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Data da aplicação inválida!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro")
            )


        data_liberacao = data + timedelta(

            days=defensivo["carencia"]

        )


        # ==================================
        # SALVA APLICAÇÃO
        # ==================================

        conexao.execute("""
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

        """, (

            defensivo_id,

            talhao_id,

            data_aplicacao,

            quantidade,

            responsavel,

            data_liberacao.strftime(
                "%Y-%m-%d"
            )

        ))


        # ==================================
        # DESCONTA DO ESTOQUE
        # ==================================

        novo_estoque = (

            defensivo["estoque"]

            - quantidade

        )


        conexao.execute("""
            UPDATE defensivos

            SET estoque = ?

            WHERE id = ?

        """, (

            novo_estoque,

            defensivo_id

        ))


        conexao.commit()

        conexao.close()


        flash(
            "Aplicação registrada e estoque atualizado!",
            "sucesso"
        )


        return redirect(
            url_for("index")
        )


    conexao.close()


    return render_template(

        "cadastro.html",

        defensivos=defensivos,

        talhoes=talhoes

    )


# ==========================================
# ESTOQUE
# ==========================================

@app.route("/estoque")
def estoque():

    conexao = conectar_banco()


    defensivos = conexao.execute("""
        SELECT *
        FROM defensivos
        ORDER BY nome
    """).fetchall()


    conexao.close()


    hoje = datetime.now().date()


    produtos = []


    for defensivo in defensivos:

        validade = defensivo["validade"]


        status_validade = "normal"

        mensagem_validade = ""


        if validade:

            try:

                data_validade = datetime.strptime(
                    validade,
                    "%Y-%m-%d"
                ).date()


                if data_validade < hoje:

                    status_validade = "vencido"

                    mensagem_validade = (
                        "Produto vencido!"
                    )


                elif (
                    data_validade - hoje
                ).days <= 30:

                    status_validade = "proximo"

                    mensagem_validade = (
                        "Produto próximo do vencimento."
                    )


            except ValueError:

                status_validade = "normal"


        produtos.append({

            "id": defensivo["id"],

            "nome": defensivo["nome"],

            "categoria": defensivo["categoria"],

            "fabricante": defensivo["fabricante"],

            "estoque": defensivo["estoque"],

            "unidade": defensivo["unidade"],

            "validade": defensivo["validade"],

            "carencia": defensivo["carencia"],

            "status_validade": status_validade,

            "mensagem_validade":
                mensagem_validade

        })


    return render_template(

        "estoque.html",

        defensivos=produtos

    )


# ==========================================
# CADASTRO DE PRODUTO
# ==========================================

@app.route(
    "/cadastro-produto",
    methods=["GET", "POST"]
)
def cadastro_produto():

    conexao = conectar_banco()


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
            ""
        ).strip()


        unidade = request.form.get(
            "unidade",
            ""
        ).strip()


        validade = request.form.get(
            "validade",
            ""
        ).strip()


        # ==================================
        # CAMPOS OBRIGATÓRIOS
        # ==================================

        if (

            not nome

            or not categoria

            or not fabricante

            or not quantidade

            or not unidade

            or not validade

        ):

            flash(
                "Preencha todos os campos obrigatórios!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro_produto")
            )


        # ==================================
        # QUANTIDADE
        # ==================================

        try:

            quantidade = float(
                quantidade
            )


            if quantidade <= 0:

                flash(
                    "A quantidade deve ser maior que zero!",
                    "erro"
                )

                conexao.close()

                return redirect(
                    url_for("cadastro_produto")
                )


        except ValueError:

            flash(
                "Informe uma quantidade válida!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro_produto")
            )


        # ==================================
        # CARÊNCIA
        # ==================================

        carencia = request.form.get(
            "carencia",
            "0"
        ).strip()


        try:

            carencia = int(carencia)


            if carencia < 0:

                flash(
                    "A carência não pode ser negativa!",
                    "erro"
                )

                conexao.close()

                return redirect(
                    url_for("cadastro_produto")
                )


        except ValueError:

            flash(
                "Informe uma carência válida!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro_produto")
            )


        # ==================================
        # VALIDADE
        # ==================================

        try:

            datetime.strptime(
                validade,
                "%Y-%m-%d"
            ).date()


        except ValueError:

            flash(
                "Informe uma data de validade válida!",
                "erro"
            )

            conexao.close()

            return redirect(
                url_for("cadastro_produto")
            )


        # ==================================
        # SALVA NO BANCO
        # ==================================

        conexao.execute("""
            INSERT INTO defensivos
            (
                nome,

                categoria,

                fabricante,

                estoque,

                unidade,

                validade,

                carencia

            )

            VALUES (?, ?, ?, ?, ?, ?, ?)

        """, (

            nome,

            categoria,

            fabricante,

            quantidade,

            unidade,

            validade,

            carencia

        ))


        conexao.commit()

        conexao.close()


        flash(
            "Defensivo cadastrado com sucesso! 🌱",
            "sucesso"
        )


        return redirect(
            url_for("estoque")
        )


    conexao.close()


    return render_template(
        "cadastro_produto.html"
    )


# ==========================================
# RASTREABILIDADE
# ==========================================

@app.route("/rastreabilidade")
def rastreabilidade():

    conexao = conectar_banco()


    aplicacoes = conexao.execute("""
        SELECT

            aplicacoes.*,

            defensivos.nome AS defensivo,

            talhoes.nome AS talhao

        FROM aplicacoes

        INNER JOIN defensivos

            ON aplicacoes.defensivo_id =
               defensivos.id

        INNER JOIN talhoes

            ON aplicacoes.talhao_id =
               talhoes.id

        ORDER BY
            aplicacoes.data_aplicacao DESC

    """).fetchall()


    conexao.close()


    hoje = datetime.now().date()


    lista = []


    for aplicacao in aplicacoes:

        data_liberacao = datetime.strptime(
            aplicacao["data_liberacao"],
            "%Y-%m-%d"
        ).date()


        if hoje < data_liberacao:

            status = "aguardando"

        else:

            status = "liberada"


        lista.append({

            "id": aplicacao["id"],

            "defensivo":
                aplicacao["defensivo"],

            "talhao":
                aplicacao["talhao"],

            "data_aplicacao":
                aplicacao["data_aplicacao"],

            "quantidade":
                aplicacao["quantidade"],

            "responsavel":
                aplicacao["responsavel"],

            "data_liberacao":
                aplicacao["data_liberacao"],

            "status": status

        })


    return render_template(

        "rastreabilidade.html",

        aplicacoes=lista

    )


# ==========================================
# LISTAGEM DE APLICAÇÕES
# ==========================================

@app.route("/aplicacoes")
def aplicacoes():

    conexao = conectar_banco()


    aplicacoes = conexao.execute("""
        SELECT

            aplicacoes.*,

            defensivos.nome AS defensivo,

            talhoes.nome AS talhao

        FROM aplicacoes

        INNER JOIN defensivos

            ON aplicacoes.defensivo_id =
               defensivos.id

        INNER JOIN talhoes

            ON aplicacoes.talhao_id =
               talhoes.id

        ORDER BY aplicacoes.id DESC

    """).fetchall()


    conexao.close()


    hoje = datetime.now().date()


    lista = []


    for aplicacao in aplicacoes:

        data_liberacao = datetime.strptime(
            aplicacao["data_liberacao"],
            "%Y-%m-%d"
        ).date()


        if hoje < data_liberacao:

            status = "aguardando"

        else:

            status = "liberada"


        lista.append({

            "id": aplicacao["id"],

            "defensivo":
                aplicacao["defensivo"],

            "talhao":
                aplicacao["talhao"],

            "data_aplicacao":
                aplicacao["data_aplicacao"],

            "quantidade":
                aplicacao["quantidade"],

            "responsavel":
                aplicacao["responsavel"],

            "data_liberacao":
                aplicacao["data_liberacao"],

            "status": status

        })


    return render_template(

        "aplicacoes.html",

        aplicacoes=lista

    )


# ==========================================
# FLUXOGRAMA
# ==========================================

@app.route("/fluxograma")
def fluxograma():

    return render_template(
        "fluxograma.html"
    )


# ==========================================
# INICIAR SISTEMA
# ==========================================

if __name__ == "__main__":

    criar_banco()

    app.run(
        debug=True
    )