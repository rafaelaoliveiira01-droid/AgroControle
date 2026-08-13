from flask import Flask, render_template, request
from datetime import datetime, timedelta

app = Flask(__name__)


@app.route("/rastreabilidade", methods=["GET", "POST"])
def rastreabilidade():

    resultado = None

    if request.method == "POST":

        defensivo_id = int(request.form["defensivo"])
        talhao = request.form["talhao"]
        data_aplicacao = datetime.strptime(
            request.form["data_aplicacao"],
            "%Y-%m-%d"
        ).date()

        quantidade = float(request.form["quantidade"])
        responsavel = request.form["responsavel"]

        # Procura o defensivo selecionado
        defensivo = next(
            (
                item for item in estoque
                if item["id"] == defensivo_id
            ),
            None
        )

        # Verifica se o defensivo existe
        if defensivo is None:

            resultado = {
                "tipo": "erro",
                "mensagem": "Defensivo não encontrado."
            }

        # Verifica quantidade
        elif quantidade <= 0:

            resultado = {
                "tipo": "erro",
                "mensagem": "A quantidade deve ser maior que zero."
            }

        # Verifica estoque
        elif quantidade > defensivo["quantidade"]:

            resultado = {
                "tipo": "erro",
                "mensagem": (
                    f"Estoque insuficiente. "
                    f"Disponível: {defensivo['quantidade']} "
                    f"{defensivo['unidade']}."
                )
            }

        else:

            # Desconta a quantidade utilizada
            defensivo["quantidade"] -= quantidade

            # Calcula o fim da carência
            data_fim_carencia = (
                data_aplicacao
                + timedelta(days=defensivo["carencia"])
            )

            # Verifica a data atual
            data_atual = datetime.today().date()

            # Verifica se a colheita está liberada
            colheita_liberada = data_atual >= data_fim_carencia

            if colheita_liberada:

                mensagem_carencia = (
                    "Colheita liberada. "
                    "O período de carência foi encerrado."
                )

            else:

                mensagem_carencia = (
                    "Atenção: o período de carência ainda não terminou. "
                    "A colheita não está liberada."
                )

            # Registra a aplicação
            aplicacao = {
                "defensivo": defensivo["nome"],
                "talhao": talhao,
                "data": data_aplicacao.strftime("%d/%m/%Y"),
                "quantidade": quantidade,
                "unidade": defensivo["unidade"],
                "responsavel": responsavel,
                "carencia": defensivo["carencia"],
                "data_fim_carencia": data_fim_carencia.strftime(
                    "%d/%m/%Y"
                ),
                "colheita_liberada": colheita_liberada
            }

            aplicacoes.append(aplicacao)

            resultado = {
                "tipo": "sucesso",
                "mensagem": "Aplicação registrada com sucesso!",
                "carencia": mensagem_carencia,
                "data_fim_carencia": data_fim_carencia.strftime(
                    "%d/%m/%Y"
                ),
                "colheita_liberada": colheita_liberada
            }

    return render_template(
        "rastreabilidade.html",
        estoque=estoque,
        talhoes=talhoes,
        aplicacoes=aplicacoes,
        resultado=resultado
    )