from flask import Flask, render_template, request
from datetime import datetime, timedelta

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")


@app.route("/estoque")
def estoque():
    return render_template("estoque.html")


@app.route("/rastreabilidade", methods=["GET", "POST"])
def rastreabilidade():

    resultado = None

    if request.method == "POST":

        defensivo = request.form["defensivo"]

        data_aplicacao = datetime.strptime(
            request.form["data_aplicacao"],
            "%Y-%m-%d"
        ).date()

        carencia = int(request.form["carencia"])

        data_fim = data_aplicacao + timedelta(days=carencia)

        data_atual = datetime.today().date()

        liberada = data_atual >= data_fim

        if liberada:
            mensagem = "Colheita liberada. O período de carência foi encerrado."
        else:
            mensagem = "Atenção: o período de carência ainda não terminou. A colheita não está liberada."

        resultado = {
            "defensivo": defensivo,
            "data_aplicacao": data_aplicacao.strftime("%d/%m/%Y"),
            "carencia": carencia,
            "data_fim": data_fim.strftime("%d/%m/%Y"),
            "liberada": liberada,
            "mensagem": mensagem
        }

    return render_template(
        "rastreabilidade.html",
        resultado=resultado
    )


if __name__ == "__main__":
    app.run(debug=True)