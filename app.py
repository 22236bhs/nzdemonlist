from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, select, Table, Column, update
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import config

DATABASE = "database.db"

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE}"
db = SQLAlchemy(app)

currentUser = None
success = False
signupFailMessage = ""

def CalculatePoints(playerID) -> None:
    conn = db.session()
    user = conn.execute(select(Users).where(Users.id == playerID)).scalar_one()
    totalPoints = 0
    for completion in user.user_completions:
        totalPoints += completion.level.points
    conn.execute(update(Users).where(Users.id == playerID).values(points=totalPoints))
    conn.commit()
    


class Base(DeclarativeBase):
    pass


class Completions(Base):
    __tablename__ = "Completions"
    id : Mapped[int] = mapped_column(primary_key=True)
    player_id : Mapped[int] = mapped_column(ForeignKey("Users.id"))
    player : Mapped["Users"] = relationship(back_populates="user_completions")
    level_id : Mapped[int] = mapped_column(ForeignKey("Levels.id"))
    level : Mapped["Levels"] = relationship(primaryjoin="Completions.level_id == Levels.id",
                                            back_populates="level_completions")
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
    verifier : Mapped["Users"] = relationship(primaryjoin="Levels.verifier_id == Users.id")
    verification_id : Mapped[int] = mapped_column(ForeignKey("Completions.id"))
    verification : Mapped["Completions"] = relationship(primaryjoin="Levels.verification_id == Completions.id")
    publisher_id : Mapped[int] = mapped_column(ForeignKey("Users.id"))
    publisher : Mapped["Users"] = relationship(primaryjoin="Levels.publisher_id == Users.id")
    level_completions : Mapped[list["Completions"]] = relationship(primaryjoin="Completions.level_id == Levels.id",
                                                                   back_populates="level")
    points : Mapped[int] = mapped_column(Integer())


class Submissions(Base):
    __tablename__ = "Submissions"
    id : Mapped[int] = mapped_column(primary_key=True)
    completion_id : Mapped[int] = mapped_column(ForeignKey("Completions.id"))
    completion : Mapped["Completions"] = relationship()
    raw : Mapped[str] = mapped_column(String())
    time : Mapped[int] = mapped_column(Integer())

class AdminRanks(Base):
    __tablename__ = "Admin Ranks"
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(String())
    description : Mapped[str] = mapped_column(String())


class Admins(Base):
    __tablename__ = "Admins"
    id : Mapped[int] = mapped_column(primary_key=True)
    rank_id : Mapped["int"] = mapped_column(ForeignKey("Admin Ranks.id"))
    rank : Mapped["AdminRanks"] = relationship()
    player_id : Mapped["int"] = mapped_column(ForeignKey("Users.id"))
    player : Mapped["Users"] = relationship()
    


@app.route("/")
def list():
    data = db.session().execute(select(Levels).order_by(Levels.placement)).scalars()
    return render_template("list.html", data=data, title="Demonlist")


@app.route("/level/<int:id>")
def level(id):
    data = db.session().execute(select(Levels).where(Levels.id == id)).scalar_one()
    return render_template("level.html", level=data, title=data.name, back="/")

@app.route("/leaderboard")
def leaderboard():
    players = db.session().execute(select(Users).where(select(Completions).where(Completions.player_id == Users.id).exists()).order_by(Users.points.desc())).scalars()
    return render_template(
        "leaderboard.html",
        players=players,
        title="Leaderboard",
        back="/"
    )


@app.route("/leaderboard/<int:id>")
def player(id):
    playerData = db.session().execute(select(Users).where(Users.id == id)).scalar_one()
    return render_template(
        "player.html",
        player=playerData,
        title=playerData.name,
        back="/leaderboard"
    )


@app.route("/profile")
def profile():
    if currentUser:
        return render_template(
            "profile_logged_in.html",
            user=currentUser,
            title="Profile",
            back="/"
        )
    else:
        return render_template(
            "profile_logged_out.html",
            title="Profile",
            back="/"
        )


@app.route("/logout")
def logout():
    global currentUser
    currentUser = None
    return app.redirect("/profile")


@app.route("/signup")
def signup():
    global signupFailMessage
    message = signupFailMessage
    signupFailMessage = ""
    return render_template(
        "signup.html",
        title="Sign Up",
        back="/profile",
        message=message,
        userMaxL=config.usernameMaxLength,
        passMaxL=config.passwordMaxLength
    )


@app.route("/signup/register", methods=["GET", "POST"])
def signupRegister():
    global currentUser, signupFailMessage

    success = True

    username = request.form.get("username")
    password = request.form.get("password")
    

    if (not username) or (len(username) > config.usernameMaxLength):
        signupFailMessage = "Invalid Username"
        success = False
    
    
    elif (not password) or (len(password) > config.passwordMaxLength):
        signupFailMessage = "Invalid Password"
        success = False

    elif username in db.session().execute(select(Users.name).where(Users.name == username)).scalars():
        signupFailMessage = "Username already taken"
        success = False
    




    if not success:
        return app.redirect("/signup")
    
    else:
        password_hash = generate_password_hash(password)
        db.session().add(Users(name=username, password_hash=password_hash, admin=0, points=0))
        db.session().commit()
        currentUser = db.session().execute(select(Users).where(Users.name == username)).scalar_one()
        return app.redirect("/profile")



@app.route("/login")
def login():
    return render_template(
        "login.html",
        title="Log In",
        back="/profile"
    )


if __name__ == "__main__":
    app.run(debug=True)