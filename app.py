from flask import Flask, render_template

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


@app.route("/rastreabilidade")
def rastreabilidade():
    return render_template("rastreabilidade.html")


if __name__ == "__main__":
    app.run(debug=True)