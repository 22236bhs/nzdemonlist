from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, select, Table, Column

DATABASE = "database.db"

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE}"
db = SQLAlchemy(app)


class Base(DeclarativeBase):
    pass


class Completions(Base):
    __tablename__ = "Completions"
    id : Mapped[int] = mapped_column(primary_key=True)
    player_id : Mapped[int] = mapped_column(ForeignKey("Users.id"))
    player : Mapped["Users"] = relationship(back_populates="user_completions")
    level_id : Mapped[int] = mapped_column(ForeignKey("Levels.id"))
    level : Mapped["Levels"] = relationship(back_populates="")
    completion_link : Mapped[str] = mapped_column(String())
    FPS : Mapped[int] = mapped_column(Integer())
    CBF : Mapped[int] = mapped_column(Integer())
    CBS : Mapped[int] = mapped_column(Integer())
    accepted : Mapped[int] = mapped_column(Integer())
    index : Mapped[int] = mapped_column(Integer())


class Users(Base):
    __tablename__ = "Users"
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(String())
    points : Mapped[int] = mapped_column(Integer())
    password_hash : Mapped[str] = mapped_column(String())
    admin : Mapped[int] = mapped_column(Integer())
    user_completions : Mapped[list["Completions"]] = relationship(back_populates="player")


class Levels(Base):
    __tablename__ = "Levels"
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(String())
    placement : Mapped[int] = mapped_column(Integer())
    verifier_id : Mapped[int] = mapped_column(ForeignKey("Users.id"))
    verification_id : Mapped[int] = mapped_column(ForeignKey("Completions.id"))
    verification : Mapped["Completions"] = relationship()
    publisher_id : Mapped[int] = mapped_column(ForeignKey("Users.id"))

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