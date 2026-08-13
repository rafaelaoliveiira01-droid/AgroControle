from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "projeto-agro-chave"

DATABASE = "banco.db"


def conectar_banco():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    return conexao



def criar_banco():
    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defensivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            carencia INTEGER NOT NULL,
            estoque REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS talhoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aplicacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            defensivo_id INTEGER NOT NULL,
            talhao_id INTEGER NOT NULL,
            data_aplicacao TEXT NOT NULL,
            quantidade REAL NOT NULL,
            responsavel TEXT NOT NULL,
            data_liberacao TEXT NOT NULL,
            FOREIGN KEY (defensivo_id) REFERENCES defensivos(id),
            FOREIGN KEY (talhao_id) REFERENCES talhoes(id)
        )
    """)

    # Defensivos de exemplo
    quantidade = cursor.execute(
        "SELECT COUNT(*) FROM defensivos"
    ).fetchone()[0]

    if quantidade == 0:
        cursor.execute("""
            INSERT INTO defensivos (nome, carencia, estoque)
            VALUES
            ('Defensivo VerdeMax', 14, 100),
            ('Defensivo AgroSafe', 7, 80),
            ('Defensivo Campo Forte', 21, 120)
        """)

    # Talhões de exemplo
    quantidade = cursor.execute(
        "SELECT COUNT(*) FROM talhoes"
    ).fetchone()[0]

    if quantidade == 0:
        cursor.execute("""
            INSERT INTO talhoes (nome)
            VALUES
            ('Talhão 01'),
            ('Talhão 02'),
            ('Talhão 03')
        """)

    conexao.commit()
    conexao.close()


@app.route("/")
def index():

    conexao = conectar_banco()

    defensivos = conexao.execute(
        "SELECT * FROM defensivos"
    ).fetchall()

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
            "data_aplicacao": aplicacao["data_aplicacao"],
            "quantidade": aplicacao["quantidade"],
            "responsavel": aplicacao["responsavel"],
            "data_liberacao": aplicacao["data_liberacao"],
            "status": status,
            "mensagem": mensagem
        })

    return render_template(
        "index.html",
        defensivos=defensivos,
        aplicacoes=dados_aplicacoes
    )


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    conexao = conectar_banco()

    defensivos = conexao.execute(
        "SELECT * FROM defensivos"
    ).fetchall()

    talhoes = conexao.execute(
        "SELECT * FROM talhoes"
    ).fetchall()

    if request.method == "POST":

        defensivo_id = request.form["defensivo_id"]
        talhao_id = request.form["talhao_id"]
        data_aplicacao = request.form["data_aplicacao"]
        quantidade = float(request.form["quantidade"])
        responsavel = request.form["responsavel"]

        defensivo = conexao.execute(
            "SELECT * FROM defensivos WHERE id = ?",
            (defensivo_id,)
        ).fetchone()

        if defensivo is None:
            flash("Defensivo não encontrado!", "erro")
            conexao.close()
            return redirect(url_for("cadastro"))

        # Verifica estoque
        if quantidade <= 0:
            flash("Informe uma quantidade válida!", "erro")
            conexao.close()
            return redirect(url_for("cadastro"))

        if quantidade > defensivo["estoque"]:
            flash(
                "Quantidade maior que o estoque disponível!",
                "erro"
            )
            conexao.close()
            return redirect(url_for("cadastro"))

        # Calcula a data de término da carência
        data = datetime.strptime(
            data_aplicacao,
            "%Y-%m-%d"
        ).date()

        data_liberacao = data + timedelta(
            days=defensivo["carencia"]
        )

        # Salva a aplicação
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
            data_liberacao.strftime("%Y-%m-%d")
        ))

        # Desconta do estoque
        novo_estoque = defensivo["estoque"] - quantidade

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

        return redirect(url_for("index"))

    conexao.close()

    return render_template(
        "cadastro.html",
        defensivos=defensivos,
        talhoes=talhoes
    )

@app.route("/estoque")
def estoque():

    conexao = conectar_banco()

    defensivos = conexao.execute("""
        SELECT *
        FROM defensivos
        ORDER BY nome
    """).fetchall()

    conexao.close()

    return render_template(
        "estoque.html",
        defensivos=defensivos
    )

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
            ON aplicacoes.defensivo_id = defensivos.id

        INNER JOIN talhoes
            ON aplicacoes.talhao_id = talhoes.id

        ORDER BY aplicacoes.data_aplicacao DESC
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
            "defensivo": aplicacao["defensivo"],
            "talhao": aplicacao["talhao"],
            "data_aplicacao": aplicacao["data_aplicacao"],
            "quantidade": aplicacao["quantidade"],
            "responsavel": aplicacao["responsavel"],
            "data_liberacao": aplicacao["data_liberacao"],
            "status": status
        })

    return render_template(
        "rastreabilidade.html",
        aplicacoes=lista
    )

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
            ON aplicacoes.defensivo_id = defensivos.id
        INNER JOIN talhoes
            ON aplicacoes.talhao_id = talhoes.id
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
            "defensivo": aplicacao["defensivo"],
            "talhao": aplicacao["talhao"],
            "data_aplicacao": aplicacao["data_aplicacao"],
            "quantidade": aplicacao["quantidade"],
            "responsavel": aplicacao["responsavel"],
            "data_liberacao": aplicacao["data_liberacao"],
            "status": status
        })

    return render_template(
        "aplicacoes.html",
        aplicacoes=lista
    )

@app.route("/cadastro-produto", methods=["GET", "POST"])
def cadastro_produto():

    conexao = conectar_banco()

    if request.method == "POST":

        nome = request.form["nome"].strip()
        estoque = float(request.form["estoque"])
        carencia = int(request.form["carencia"])

        if not nome:
            flash("Informe o nome do produto!", "erro")
            conexao.close()
            return redirect(url_for("cadastro_produto"))

        if estoque < 0:
            flash("O estoque não pode ser negativo!", "erro")
            conexao.close()
            return redirect(url_for("cadastro_produto"))

        if carencia < 0:
            flash("O período de carência não pode ser negativo!", "erro")
            conexao.close()
            return redirect(url_for("cadastro_produto"))

        conexao.execute("""
            INSERT INTO defensivos
            (nome, carencia, estoque)
            VALUES (?, ?, ?)
        """, (
            nome,
            carencia,
            estoque
        ))

        conexao.commit()
        conexao.close()

        flash(
            "Produto cadastrado com sucesso! 🌱",
            "sucesso"
        )

        return redirect(url_for("estoque"))

    conexao.close()

    return render_template("cadastro_produto.html")


# ==========================
# INICIAR SISTEMA
# ==========================

if __name__ == "__main__":
    criar_banco()
    app.run(debug=True)