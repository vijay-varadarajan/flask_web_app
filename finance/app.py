# Import required modules and functions
import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from datetime import datetime
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Default route of the application
@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])
    balance = cash[0]["cash"]

    rows = db.execute(
        "SELECT symbol, shares FROM portfolio WHERE user_id=?", session["user_id"]
    )

    holdings = []
    grand_total = 0

    for row in rows:

        data = lookup(row["symbol"])
        holdings.append(
            {
                "symbol": data["symbol"],
                "name": data["name"],
                "shares": row["shares"],
                "price": usd(data["price"]),
                "total": usd(data["price"] * row["shares"]),
            }
        )
        grand_total += data["price"] * row["shares"]

    grand_total += balance
    return render_template(
        "index.html", holdings=holdings, balance=usd(balance), total=usd(grand_total)
    )


# Buy route of the application
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        if not symbol:
            return apology("must provide symbol", 400)

        if not shares:
            return apology("Must provide number of shares", 400)

        # ensure number of shares is valid
        try:
            if int(shares) <= 0:
                return apology("must provide valid number of shares (integer)", 400)
        except:
            return apology("must provide valid number of shares (integer)", 400)

        stock = lookup(symbol)

        if stock == None:
            return apology("Invalid symbol", 400)

        price = float(stock["price"])
        cost = (price) * int(shares)

        rows = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])
        balance = rows[0]["cash"]

        balance -= cost
        if balance < 0:
            return apology("Cannot Afford", 400)

        db.execute("UPDATE users SET cash=? WHERE id=?", balance, session["user_id"])

        db.execute(
            "INSERT INTO exchanges (user_id, symbol, shares, price, total, balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            session["user_id"],
            symbol,
            shares,
            price,
            cost,
            balance,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        holding = db.execute(
            "SELECT shares FROM portfolio WHERE symbol=? AND user_id =?",
            symbol,
            session["user_id"],
        )

        # add to portfolio database
        # if symbol is new, add to portfolio
        if not holding:
            db.execute(
                "INSERT INTO portfolio (user_id, symbol, shares) VALUES (?, ?, ?)",
                session["user_id"],
                symbol,
                shares,
            )

        # if symbol is already in portfolio, update quantity of shares and total
        else:
            db.execute(
                "UPDATE portfolio SET shares = shares + ? WHERE symbol = ? AND user_id = ?",
                shares,
                symbol,
                session["user_id"],
            )

        flash("Bought!")
        return redirect("/")

    else:
        # Render page if requested via get
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Select transactions from database
    transactions = db.execute(
        "SELECT symbol, shares, price, total, date FROM exchanges WHERE user_id=? ORDER BY id DESC",
        session["user_id"],
    )

    # Display entire history of transactions
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
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

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        stock_symbol = request.form.get("symbol")
        if not stock_symbol:
            return apology("Must provide a symbol", 400)

        stock = lookup(stock_symbol.upper())

        if stock == None:
            return apology("Invalid symbol", 400)

        return render_template("quoted.html", stock=stock)

    else:
        # Render page if requested via GET
        return render_template("quote.html")


@app.route("/change_pwd", methods=["GET", "POST"])
@login_required
def change_password():
    """Let user change password"""
    if request.method == "POST":

        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        # Ensure current password is not empty
        if not current_password:
            return apology("must provide current password", 400)

        # Query database for user_id
        rows = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])

        # Ensure current password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], current_password):
            return apology("Invalid password", 400)

        # Ensure new password is not empty
        if not new_password:
            return apology("must provide new password", 400)

        # Ensure new password confirmation is not empty
        elif not confirm_new_password:
            return apology("must provide new password confirmation", 400)

        # Ensure new password and confirmation match
        elif new_password != confirm_new_password:
            return apology("new password and confirmation must match", 400)

        # Update database
        hash = generate_password_hash(new_password)
        rows = db.execute(
            "UPDATE users SET hash = ? WHERE id = ?", hash, session["user_id"]
        )

        # Show flash
        flash("Changed!")
        return redirect("/")

    else:
        # Render page if requested via GET
        return render_template("change_pwd.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif request.form.get("confirmation") != request.form.get("password"):
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


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        # get symbol and shares from form
        symbol = request.form.get("symbol").upper()
        shares = int(request.form.get("shares"))

        # No symbol given
        if not symbol:
            return apology("must provide symbol", 400)

        # No shares given
        if not shares:
            return apology("Must provide number of shares", 400)

        rows = db.execute(
            "SELECT symbol FROM portfolio WHERE user_id = ?", session["user_id"]
        )

        for row in rows:
            if row == rows:
                break
            else:
                pass

        cols = db.execute(
            "SELECT shares FROM portfolio WHERE symbol = ? AND user_id = ?",
            symbol,
            session["user_id"],
        )
        cols = cols[0]["shares"]

        # ensure number of shares is valid
        if (int(shares) <= 0) or (cols < shares):
            return apology("Provide valid number of shares", 400)

        # Lookup for stock value
        stock = lookup(symbol)

        price = float(stock["price"])
        cost = (price) * int(shares)

        rows = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])
        balance = rows[0]["cash"]

        # Update balance
        balance += cost
        db.execute("UPDATE users SET cash=? WHERE id=?", balance, session["user_id"])

        db.execute(
            "INSERT INTO exchanges (user_id, symbol, shares, price, total, balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            session["user_id"],
            symbol,
            (-(shares)),
            price,
            cost,
            balance,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Update portfolio
        db.execute(
            "UPDATE portfolio SET shares = shares - ? WHERE symbol=? AND user_id=?",
            shares,
            symbol,
            session["user_id"],
        )

        # Delete from stock portfolio if shares = 0
        db.execute(
            "DELETE FROM portfolio WHERE shares = '0' AND user_id=?", session["user_id"]
        )

        flash("Sold!")
        return redirect("/")

    else:
        # Render page if requested via GET
        symbols = db.execute(
            "SELECT symbol FROM portfolio WHERE user_id=?", session["user_id"]
        )
        return render_template("sell.html", symbols=symbols)
