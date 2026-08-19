from flask import Flask, render_template, request, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, select, update, text
from werkzeug.security import check_password_hash, generate_password_hash
import config
import time

DATABASE = "database.db"

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE}"
db = SQLAlchemy(app)
app.secret_key = "8T3198T31RG318F318G31F8137F8"


class Base(DeclarativeBase):
    pass


class Completions(Base):
    __tablename__ = "Completions"
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    player: Mapped["Users"] = relationship(back_populates="user_completions")
    level_id: Mapped[int] = mapped_column(ForeignKey("Levels.id"))
    level: Mapped["Levels"] = relationship(
        primaryjoin="Completions.level_id == Levels.id",
        back_populates="level_completions")
    completion_link: Mapped[str] = mapped_column(String())
    FPS: Mapped[int] = mapped_column(Integer())
    CBF: Mapped[int] = mapped_column(Integer())
    accepted: Mapped[int] = mapped_column(Integer())
    index: Mapped[int] = mapped_column(Integer())


class Users(Base):
    __tablename__ = "Users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String())
    points: Mapped[int] = mapped_column(Integer())
    password_hash: Mapped[str] = mapped_column(String())
    admin: Mapped[int] = mapped_column(Integer())
    user_completions: Mapped[list["Completions"]] = relationship(
        back_populates="player")


class Levels(Base):
    __tablename__ = "Levels"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String())
    placement: Mapped[int] = mapped_column(Integer())
    verifier_id: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    verifier: Mapped["Users"] = relationship(
        primaryjoin="Levels.verifier_id == Users.id")
    verification_id: Mapped[int] = mapped_column(ForeignKey("Completions.id"))
    verification: Mapped["Completions"] = relationship(
        primaryjoin="Levels.verification_id == Completions.id")
    publisher_id: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    publisher: Mapped["Users"] = relationship(
        primaryjoin="Levels.publisher_id == Users.id")
    level_completions: Mapped[list["Completions"]] = relationship(
        primaryjoin="Completions.level_id == Levels.id",
        back_populates="level")
    points: Mapped[int] = mapped_column(Integer())


class Submissions(Base):
    __tablename__ = "Submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    completion_id: Mapped[int] = mapped_column(ForeignKey("Completions.id"))
    completion: Mapped["Completions"] = relationship()
    time: Mapped[int] = mapped_column(Integer())


class AdminRanks(Base):
    __tablename__ = "Admin Ranks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String())
    description: Mapped[str] = mapped_column(String())


class Admins(Base):
    __tablename__ = "Admins"
    id: Mapped[int] = mapped_column(primary_key=True)
    rank_id: Mapped["int"] = mapped_column(ForeignKey("Admin Ranks.id"))
    rank: Mapped["AdminRanks"] = relationship()
    player_id: Mapped["int"] = mapped_column(ForeignKey("Users.id"))
    player: Mapped["Users"] = relationship()


def GetUser():
    # Returns the SQL user object for the signed in user, if logged in
    if "user" in session:
        userID = session.get("user")
        if IsLoggedIn():
            return db.session.execute(
                select(Users).where(Users.id == userID)).scalar_one_or_none()
        else:
            return False
    else:
        return False


def IsLoggedIn():
    # Returns true if the user is logged in, otherwise returns false
    if "loggedin" in session:
        return session.get("loggedin")
    else:
        return False


def LogInUser(userID: int):
    # Inserts the user details into the session cookies
    session["user"] = userID
    session["loggedin"] = True


def SignOutUser():
    # Resets the user details in the session cookies
    session["user"] = 0
    session["loggedin"] = False


def SetMessage(route: str, message: str, error: bool = True):
    # Stores a message for a specified route in the session cookies
    if "message" not in session:
        session["message"] = {}
    session["message"][route] = [message, error]
    session.modified = True


def GetMessage(route: str):
    # Gets the message for a specific route in the session cookies
    if "message" in session:
        if route in session["message"]:
            message = session["message"][route]
            # Messages displayed should only show up once,
            # so the message clears when it is displayed
            SetMessage(route, "")
            return message
        else:
            return ""
    else:
        return ""


def PushError(number: int, code: str):
    # Pushes the user to an error page template
    return render_template("error_page.html",
                           error_code=number,
                           title=f"{number} Error",
                           error=code), number


def LoggedOutRedirect():
    # Pushes the user to a logged out page.
    # This is done if they try to access a page that requires to be logged in
    return render_template(
        "logged_out_redirect.html",
        title="Logged Out"
        )


def IsInt(x):
    # Brute forces if the parameter can be converted to int.
    # This doesn't have to be efficient because it is not used frequently
    try:
        x = int(x)
    except ValueError:
        return False
    else:
        return True


def IsAdmin():
    # Checks if the logged in user has admin permissions.
    # Returns false if the user is not logged in
    if IsLoggedIn():
        if db.session.execute(
            select(Admins).where(
                Admins.player_id == GetUser().id)).scalar_one_or_none():
            return True
    return False


def AdminPageReject():
    # Pushes the user to a permission denied page.
    # This is when a user tries to access a page that requires admin perms
    return render_template(
        "adminrejection.html",
        title="Access Denied"
        )


def PlayerAddLevelPoints(playerID: int, levelID: int) -> None:
    # Adds the points of a level to a player's points.
    conn = db.session()
    user = conn.execute(
        select(Users).where(Users.id == playerID)).scalar_one()
    level = conn.execute(
        select(Levels).where(Levels.id == levelID)).scalar_one()
    newPoints = user.points + level.points
    conn.execute(
        update(Users).where(Users.id == playerID).values(points=newPoints))
    conn.commit()


def CalculateAllPlayerPoints():
    # Recalculates the points of every player.
    # This has to be done when a level is added since it changes a lot
    # of point values of other levels
    conn = db.session()
    conn.execute(update(Users).values(points=0))
    users = conn.execute(select(Users)).scalars()
    for user in users:
        points = 0
        for comp in user.user_completions:
            points += comp.level.points
        conn.execute(
            update(Users).where(Users.id == user.id).values(points=points))

    conn.commit()


def IsValidLength(text: str, maxL: int, minL: int):
    return (len(text) <= maxL and len(text) >= minL)


# Demonlist page
@app.route("/")
def list():
    data = db.session().execute(
        select(Levels).order_by(Levels.placement)).scalars()
    return render_template("list.html", data=data, title="Demonlist")


# Level page
@app.route("/level/<int:id>")
def level(id):
    data = db.session().execute(
        select(Levels).where(Levels.id == id)).scalar_one_or_none()

    # Return page not found error if the level doesn't exist
    if not data:
        abort(404)
    return render_template("level.html", level=data, title=data.name, back="/")


# Leaderboard page
@app.route("/leaderboard")
def leaderboard():
    conn = db.session()
    # Fetches all players that have beaten at least one level
    players = conn.execute(
        select(Users).where(
            select(Completions).where(
                Completions.player_id == Users.id).exists()
                ).order_by(Users.points.desc())).fetchall()

    playersFinal = []
    for player in players:
        # Fetch the completions of each player
        beaten = conn.execute(text(f'''SELECT Levels.name
                                FROM Levels
                                WHERE Levels.id in (
                                    SELECT level_id
                                    FROM Completions
                                    WHERE player_id = {player[0].id})
                                ORDER BY Levels.placement ASC;''')).fetchall()

        # Bundles player info with their hardest level,
        # and their beaten level count
        playersFinal.append([player[0], beaten[0][0], len(beaten)])

    return render_template(
        "leaderboard.html",
        players=playersFinal,
        title="Leaderboard",
    )


# Player page
@app.route("/leaderboard/<int:id>")
def player(id):
    playerData = db.session().execute(
        select(Users).where(Users.id == id)).scalar_one_or_none()

    # Return page not found error if the player doesn't exist
    if not playerData:
        abort(404)

    return render_template(
        "player.html",
        player=playerData,
        title=playerData.name,
        back="/leaderboard"
    )


# Profile page
@app.route("/profile")
def profile():
    # Opens a different page depending on whether the user,
    # is logged in or not
    if IsLoggedIn():
        return render_template(
            "profile_logged_in.html",
            user=GetUser(),
            title="Profile",
            isadmin=IsAdmin()
        )
    else:
        return render_template(
            "profile_logged_out.html",
            title="Profile",
        )


# Route to log out user
@app.route("/logout")
def logout():
    SignOutUser()
    return app.redirect("/profile")


# Signup page
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
        userMinL=config.usernameMinLength,
        passMaxL=config.passwordMaxLength,
        passMinL=config.passwordMinLength
    )


# Signup form submission route
@app.route("/signup/register", methods=["GET", "POST"])
def signupregister():
    if IsLoggedIn():
        return render_template("profile")

    success = True

    username = request.form.get("username")
    password = request.form.get("password")
    confirmPassword = request.form.get("confirm-password")

    # Checks if the form inputs are valid before processing

    if (not username) or (not IsValidLength(username,
                                            config.usernameMaxLength,
                                            config.usernameMinLength)):

        SetMessage("signup", "Invalid Input")
        success = False

    elif (not password) or (not IsValidLength(password,
                                              config.passwordMaxLength,
                                              config.passwordMinLength)):

        SetMessage("signup", "Invalid Input")
        success = False

    # Reject sign up if username is taken
    elif username in db.session().execute(
            select(Users.name).where(Users.name == username)).scalars():
        SetMessage("signup", config.usernameTaken)
        success = False

    # Confirm password must match password,
    # so signup is rejected otherwise
    elif confirmPassword != password:
        SetMessage("signup", config.confirmPasswordFail)
        success = False

    if not success:
        return app.redirect("/signup")

    else:
        # Hash the user password and create the new User object
        password_hash = generate_password_hash(password)

        db.session().add(Users(
            name=username,
            password_hash=password_hash,
            admin=0,
            points=0))

        db.session().commit()
        LogInUser(db.session().execute(
            select(Users).where(Users.name == username)).scalar_one().id)
        return app.redirect("/profile")


# Login page
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
        userMinL=config.usernameMinLength,
        passMaxL=config.passwordMaxLength,
        passMinL=config.passwordMinLength
    )


# Login form submission route
@app.route("/login/register", methods=["GET", "POST"])
def loginregister():
    if IsLoggedIn():
        return app.redirect("/profile")

    success = True

    username = request.form.get("username")
    password = request.form.get("password")

    # Check that the form inputs are valid before processing
    if (not username) or (not IsValidLength(username,
                                            config.usernameMaxLength,
                                            config.usernameMinLength)):

        success = False

    elif (not password) or (not IsValidLength(password,
                                              config.passwordMaxLength,
                                              config.passwordMinLength)):

        success = False

    if not success:
        SetMessage("login", "Invalid Input")
        return app.redirect("/login")
    else:
        user = db.session().execute(
            select(Users).where(Users.name == username)).scalar_one_or_none()

        # Reject login if username doesn't exist in database
        if not user:
            SetMessage("login", config.loginFail)
            return app.redirect("/login")

        else:
            # Log in user if entered password is correct.
            if check_password_hash(user.password_hash, password):
                LogInUser(user.id)
                return app.redirect("/profile")
            else:
                SetMessage("login", config.loginFail)
                return app.redirect("/login")


# Record submission page
@app.route("/submission")
def submitrecord():
    if not IsLoggedIn():
        return LoggedOutRedirect()

    # Get the ids of the user's completed levels
    ids = [i.level.id for i in GetUser().user_completions]

    # Get the Level objects for each level that exists in the database
    levels = db.session.execute(
        select(Levels).order_by(Levels.placement)).scalars()

    # Bundle each Level object with a boolean of whether the user,
    # has beaten it or not
    levels = [[i, 1] if i.id in ids else [i, 0] for i in levels]

    return render_template(
        "record_submission.html",
        title="Submit Record",
        back="/profile",
        levels=levels,
        message=GetMessage("submission"),
        linkMaxL=config.submissionCompletionLinkMaxL,
        cbfOptions=config.cbfOptions
    )


# Record submission form submission route
@app.route("/submission/submit", methods=["GET", "POST"])
def submitrecordform():
    if not IsLoggedIn():
        return LoggedOutRedirect()

    levelID = request.form.get("level")
    completionLink = request.form.get("completion_link")
    fps = request.form.get("FPS")
    cbf = request.form.get("CBF")

    success = True

    # Check that the form inputs are valid before processing
    if (not levelID) or (not completionLink) or (not fps) or (not cbf):
        success = False

    elif len(completionLink) > config.submissionCompletionLinkMaxL:
        success = False

    elif not IsInt(cbf):
        success = False

    elif not int(cbf) in config.cbfOptions:
        success = False

    elif not IsInt(fps):
        success = False

    elif int(fps) < 1:
        success = False

    # Reject submission if level doesn't exist
    elif not db.session.execute(
            select(Levels).where(Levels.id == levelID)).scalar_one_or_none():

        success = False

    if not success:
        SetMessage("submission", config.submissionFail)
        return app.redirect("/submission")

    # Reject submission if the user already has a submission
    # for the particular level
    if db.session.execute(
        select(Completions).where(
            Completions.level_id == levelID).where
            (Completions.player_id == GetUser().id)).scalar_one_or_none():

        SetMessage("submission", config.submissionAlreadyExists)
        return app.redirect("/submission")

    # Create Completion object and add to database
    completion = Completions(
        player_id=GetUser().id,
        level_id=levelID,
        completion_link=completionLink,
        FPS=fps,
        CBF=cbf,
        accepted=0,
        index=0
        )

    db.session.add(completion)

    # Get the id of the newly added completion
    completionID = db.session.execute(
        select(Completions.id).where(
            Completions.level_id == levelID).where(
                Completions.player_id == GetUser().id)).first()[0]

    # Create the Submissions object for the completion with the
    # current time and add to database
    submission = Submissions(completion_id=completionID, time=time.time())

    db.session.add(submission)

    db.session.commit()

    SetMessage("submission", config.submissionSuccess, False)

    return app.redirect("/submission")


# Admin: record submission listing page
@app.route("/reviewrecords")
def reviewrecordpage():
    if not IsAdmin():
        return AdminPageReject()

    # Gather submissions ordered by time submitted.
    # Only gets a certain amount based on a config variable
    submissions = db.session.execute(
        select(Submissions).order_by(
            Submissions.time.asc())).scalars().fetchmany(
                config.maxSubmissionDisplayCount)

    message = GetMessage("/reviewrecords")
    return render_template(
        "recordreviewlist.html",
        submissions=submissions,
        title="Submission Review List",
        back="/profile",
        message=message
        )


# Admin: Record review page for a particular submission
@app.route("/reviewrecord/<int:id>")
def reviewrecord(id):
    if not IsAdmin():
        return AdminPageReject()

    # Get the completion id corresponding to the submission
    completionID = db.session().execute(
        select(Submissions.completion_id).where(
            Submissions.id == id)).scalar_one_or_none()

    # If the completion doesn't exist, return page not found error
    if not completionID:
        abort(404)

    # Get the details of the submission
    submissionDetails = db.session().execute(
        select(Completions).where(
            Completions.id == completionID)).scalar_one()

    return render_template(
        "recordreviewpage.html",
        title="Review Submission",
        back="/reviewrecords",
        info=submissionDetails,
        subID=id,
        cbfOptions=config.cbfOptions
    )


# Admin: Decision for a particular record submission
@app.route("/reviewrecord/<int:subid>/<int:accepted>")
def reviewrecordchoice(subid, accepted):
    if not IsAdmin():
        return AdminPageReject()

    conn = db.session()

    # Get the completion id corresponding to the submission
    compID = conn.execute(
        select(Submissions.completion_id).where(
            Submissions.id == subid)).scalar_one_or_none()

    # If the completion doesn't exist, return a page not found error
    if not compID:
        abort(404)

    # Get completion information
    completion = conn.execute(
        select(Completions).where(Completions.id == compID)).scalar()

    if accepted:
        # If the decision was to accept the submission,
        # get the next completion index and set the completion to accepted,
        # and set the index to the next index.
        nextIndex = db.session.execute(
            select(Completions.index).where(
                Completions.level_id == completion.level.id).order_by(
                    Completions.index.desc())).scalar() + 1

        conn.execute(update(Completions).where(
            Completions.id == compID).values(accepted=1, index=nextIndex))

        # Recalculate player's points
        PlayerAddLevelPoints(completion.player_id, completion.level_id)
        SetMessage("/reviewrecords", "Record Accepted", False)
    else:
        # If the record is rejected, delete it the completion from the database
        conn.execute(text(f"DELETE FROM Completions WHERE id == {compID};"))
        SetMessage("/reviewrecords", "Record Rejected")

    # Delete the submission
    conn.execute(text(f"DELETE FROM Submissions WHERE id == {subid};"))
    conn.commit()

    return app.redirect("/reviewrecords")


# Route for 404 error handling
@app.errorhandler(404)
def error404(e):
    return PushError(404, e)


# Route for 505 error handling
@app.errorhandler(505)
def error505(e):
    return PushError(505, e)


if __name__ == "__main__":
    app.run(debug=True)
