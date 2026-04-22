import sqlite3
from flask import Flask, render_template

database = "database.db"

app = Flask(__name__)

@app.route("/")
def list():
    pass


@app.route("/level/<int:id>")
def level(id):
    pass


if __name__ == "__main__":
    app.run(debug=True)