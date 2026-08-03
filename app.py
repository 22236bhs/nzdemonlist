from flask import Flask, render_template, request, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, select, Table, Column, update, func
from werkzeug.security import check_password_hash, generate_password_hash
import config
import time

DATABASE = "database.db"

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE}"
db = SQLAlchemy(app)
app.secret_key = "8T3198T31RG318F318G31F8137F8"


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


def GetUser():
    if "user" in session:
        userID = session.get("user")
        if IsLoggedIn():
            return db.session.execute(select(Users).where(Users.id == userID)).scalar_one_or_none()
        else:
            return False
    else:
        return False


def IsLoggedIn():
    if "loggedin" in session:
        return session.get("loggedin")
    else:
        return False


def LogInUser(userID):
    session["user"] = userID
    session["loggedin"] = True


def SignOutUser():
    session["user"] = 0
    session["loggedin"] = False


def SetMessage(route : str, message : str):
    if not "message" in session:
        session["message"] = {}
    session["message"][route] = message
    session.modified = True


def GetMessage(route : str):
    if "message" in session:
        if route in session["message"]:
            message = session["message"][route]
            SetMessage(route, "")
            return message
        else:
            return ""
    else:
        return ""


def PushError(number, code):
    return render_template("error_page.html",
                           error_code=number,
                           title=f"{number} Error",
                           error=code), number


def LoggedOutRedirect():
    return render_template(
        "logged_out_redirect.html",
        title="Logged Out"
        )


def IsInt(x):
    try:
        x = int(x)
    except:
        return False
    else:
        return True


def IsAdmin():
    if IsLoggedIn():
        if db.session.execute(select(Admins).where(Admins.player_id == GetUser().id)).scalar_one_or_none():
            return True
    return False


def AdminPageReject():
    return render_template(
        "adminrejection.html",
        title="Access Denied"
        )


@app.route("/")
def list():
    data = db.session().execute(select(Levels).order_by(Levels.placement)).scalars()
    return render_template("list.html", data=data, title="Demonlist")


@app.route("/level/<int:id>")
def level(id):
    data = db.session().execute(select(Levels).where(Levels.id == id)).scalar_one_or_none()
    if not data:
        abort(404)
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
    playerData = db.session().execute(select(Users).where(Users.id == id)).scalar_one_or_none()
    if not playerData:
        abort(404)
    return render_template(
        "player.html",
        player=playerData,
        title=playerData.name,
        back="/leaderboard"
    )


@app.route("/profile")
def profile():
    if IsLoggedIn():
        return render_template(
            "profile_logged_in.html",
            user=GetUser(),
            title="Profile",
            back="/",
            isadmin=IsAdmin()
        )
    else:
        return render_template(
            "profile_logged_out.html",
            title="Profile",
            back="/",
        )


@app.route("/logout")
def logout():
    SignOutUser()
    return app.redirect("/profile")


@app.route("/signup")
def signup():
    if IsLoggedIn():
        return app.redirect("/profile")
    
    message = GetMessage("signup")

    return render_template(
        "signup.html",
        title="Sign Up",
        back="/profile",
        message=message,
        userMaxL=config.usernameMaxLength,
        passMaxL=config.passwordMaxLength
    )


@app.route("/signup/register", methods=["GET", "POST"])
def signupregister():
    if IsLoggedIn():
        return render_template("profile")

    success = True

    username = request.form.get("username")
    password = request.form.get("password")
    confirmPassword = request.form.get("confirm-password")

    if (not username) or (len(username) > config.usernameMaxLength):
        SetMessage("signup", "Invalid Input")
        success = False
    
    
    elif (not password) or (len(password) > config.passwordMaxLength):
        SetMessage("signup", "Invalid Input")
        success = False

    elif username in db.session().execute(select(Users.name).where(Users.name == username)).scalars():
        SetMessage("signup", config.usernameTaken)
        success = False
    
    elif confirmPassword != password:
        SetMessage("signup", config.confirmPasswordFail)
        success = False
    

    if not success:
        return app.redirect("/signup")
    
    else:
        password_hash = generate_password_hash(password)
        db.session().add(Users(name=username, password_hash=password_hash, admin=0, points=0))
        db.session().commit()
        LogInUser(db.session().execute(select(Users).where(Users.name == username)).scalar_one().id)
        return app.redirect("/profile")


@app.route("/login")
def login():
    if IsLoggedIn():
        return app.redirect("/profile")
    
    message = GetMessage("login")

    return render_template(
        "login.html",
        title="Log In",
        back="/profile",
        message=message,
        userMaxL=config.usernameMaxLength,
        passMaxL=config.passwordMaxLength
    )


@app.route("/login/register", methods=["GET", "POST"])
def loginregister():
    if IsLoggedIn():
        return app.redirect("/profile")
    
    success = True

    username = request.form.get("username")
    password = request.form.get("password")

    if (not username) or (len(username) > config.usernameMaxLength):
        SetMessage("login", "Invalid Input")
        success = False
    
    elif (not password) or (len(password) > config.passwordMaxLength):
        SetMessage("login", "Invalid Input")
        success = False
    

    if not success:
        return app.redirect("/login")
    else:
        user = db.session().execute(select(Users).where(Users.name == username)).scalar_one_or_none()
        if not user:
            SetMessage("login", config.loginFail)
            return app.redirect("/login")
           
        else:
            if check_password_hash(user.password_hash, password):
                LogInUser(user.id)
                return app.redirect("/profile")
            SetMessage("login", config.loginFail)
            return app.redirect("/login")


@app.route("/submission")
def submitrecord():
    if not IsLoggedIn():
        return LoggedOutRedirect()
    
    levels = db.session.execute(select(Levels).order_by(Levels.placement)).scalars()

    return render_template(
        "record_submission.html",
        title="Submit Record",
        back="/profile",
        levels=levels,
        message = GetMessage("submission"),
        linkMaxL = config.submissionCompletionLinkMaxL,
        cbfOptions=config.cbfOptions
    )


@app.route("/submission/submit", methods=["GET", "POST"])
def submitrecordform():
    if not IsLoggedIn():
        return LoggedOutRedirect()
    
    levelID = request.form.get("level")
    completionLink = request.form.get("completion_link")
    fps = request.form.get("FPS")
    cbf = request.form.get("CBF")

    success = True

    if (not levelID) or (not completionLink) or (not fps) or (not cbf):
        success = False
    
    elif len(completionLink) > config.submissionCompletionLinkMaxL:
        success = False
    
    elif not IsInt(cbf):
        success = False

    elif int(cbf) < 0 or int(cbf) > 2:
        success = False
    
    elif not IsInt(fps):
        success = False
    
    elif int(fps) < 1:
        success = False

    if not success:
        SetMessage("submission", config.submissionFail)
        return app.redirect("/submission")

    if db.session.execute(select(Completions).where(Completions.level_id == levelID).where(Completions.player_id == GetUser().id)).scalar_one_or_none():
        SetMessage("submission", config.submissionAlreadyExists)
        return app.redirect("/submission")
    
    nextIndex = len(db.session.execute(select(Completions).where(Completions.level_id == levelID)).fetchall()) + 1


    completion = Completions(
        player_id=GetUser().id,
        level_id=levelID,
        completion_link=completionLink,
        FPS=fps,
        CBF=cbf,
        accepted=0,
        index=nextIndex
        )
    
    db.session.add(completion) 

    completionID = db.session.execute(select(Completions.id).where(Completions.level_id == levelID).where(Completions.player_id == GetUser().id)).first()[0]

    submission = Submissions(completion_id=completionID, time=time.time())

    db.session.add(submission)

    db.session.commit()

    SetMessage("submission", config.submissionSuccess)
    
    return app.redirect("/submission")


@app.route("/reviewrecords")
def reviewrecordpage():
    if not IsAdmin():
        return AdminPageReject()

    submissions = db.session.execute(select(Submissions).order_by(Submissions.time.asc())).scalars().fetchmany(15)
    

    return render_template(
        "recordreviewlist.html",
        submissions=submissions,
        title="Submission Review List"
        )


@app.route("/reviewrecord/<int:id>")
def reviewrecord(id):
    if not IsAdmin():
        return AdminPageReject()

    completionID = db.session().execute(select(Submissions.completion_id).where(Submissions.id == id)).scalar_one()
    submissionDetails = db.session().execute(select(Completions).where(Completions.id == completionID)).scalar_one()

    return render_template(
        "recordreviewpage.html",
        title="Review Submission",
        back="/reviewrecords",
        info=submissionDetails
    )


@app.errorhandler(404)
def error404(e):
    return PushError(404, e)


if __name__ == "__main__":
    app.run(debug=True)