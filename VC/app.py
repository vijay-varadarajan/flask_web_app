# import cs50, flask 
import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from datetime import datetime
from tempfile import mkdtemp
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///vet.db")

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


# Configure sessions
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response
 
# Homepage
@app.route('/')
def index():
    return render_template("home.html")
    

# Register query route
@app.route('/register', methods=["GET", "POST"])
def register():
     
    session.clear()
    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif request.form.get("confirm_password") != request.form.get("password"):
            return apology("passwords don't match", 400)

        username = request.form.get("username")

        hashed_password = generate_password_hash(request.form.get("password"))

        try:
            registrant = db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                username,
                hashed_password,
            )
        except:
            return apology("Username exists", 400)

        session["user_id"] = registrant

        flash("Registered!")
        return redirect("/")

    else:
        # Render page if requested via GET
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("Provide username", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        return redirect("/")
    else:
        return render_template("/report.html")

# Result (Vet clinics) display route

# Login and signup routes

# Logout - redirect to home page

# User page route

# User register pet route

# User pet injections tracker route

# Help / online counselling query route

# Online help / counselling links display route
