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


@app.route("/leaderboard")
def leaderboard():
    pass


@app.route("/leaderboard/<int:id>")
def player():
    pass


@app.route("/signin")
def signin():
    pass

if __name__ == "__main__":
    app.run(debug=True)