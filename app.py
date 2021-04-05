import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from cs50 import SQL
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, monetary, search
import redis

# Configure application
app = Flask(__name__)
app.testing = True

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd
try:
    profile = os.environ["profile"]
except KeyError as e:
    print("No profile available, assuming Heroku")
    profile = "heroku"
    
if profile == "local":
    print('setting up local')
    # Configure session to use filesystem (instead of signed cookies)
    app.config["SESSION_FILE_DIR"] = mkdtemp()
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    # Configure CS50 Library to use SQLite database
    db = SQL("sqlite:///finance.db")
else:
    #Configure redis session cache
    app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.config["SESSION_REDIS"] = redis.from_url(os.environ['REDIS_URL'])
    app.config["SESSION_TYPE"] = "redis"
    app.config["PERMANENT_SESSION_LIFETIME"] = 1800
    #Configure database according to environment
    db = SQL(os.environ['DATABASE_URL'])

Session(app)

# API Key for IEX
os.environ.setdefault('API_KEY', 'pk_1c8bf68d588841d28f87a357709737bb')

# Show portfolio of stocks
@app.route("/")
@login_required
def index():
    shares_dict = db.execute("SELECT * FROM shares WHERE user_id = :user_id",
                             user_id=session["user_id"])

    # Update stock price and shares value
    for i in range(len(shares_dict)):
        db.execute("UPDATE shares SET stock_price = :stock_price, shares_value = :shares_value WHERE user_id = :user_id AND stock_symbol = :stock_symbol",
                   user_id=session["user_id"],
                   stock_symbol=shares_dict[i]["stock_symbol"],
                   stock_price=monetary(
                       lookup(shares_dict[i]["stock_symbol"])['price']),
                   shares_value=monetary(shares_dict[i]["shares"] * lookup(shares_dict[i]["stock_symbol"])['price']))

    # Display user portfolio
    print(session["user_id"])
    user_cash = monetary(db.execute(
        "SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])[0]["cash"])
    query = db.execute("SELECT SUM(shares_value) FROM shares WHERE user_id = :user_id",
                            user_id=session["user_id"])
    print(query)
    if profile == "local":
        sum_shares = query[0]["SUM(shares_value)"]
    else:
        sum_shares = query[0]["sum"]
    if not sum_shares:
        user_value = user_cash
    else:
        user_value = monetary(user_cash + sum_shares)
    return render_template("index.html", shares_data=shares_dict, user_cash=user_cash, user_value=user_value)


# Buy shares of stock
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")

    else:
        # Error - no stock symbol provided
        if not request.form.get("symbol"):
            return apology("Please provide a stock symbol.")

        # Error - invalid stock symbol
        if not lookup(request.form.get("symbol")):
            return apology("Stock symbol not valid.")

        # Error - non-integer number of shares
        requested_shares = float(request.form.get("shares"))
        if not (requested_shares).is_integer():
            return apology("Number of shares must be an integer.")

        # Error - not enough cash to buy shares
        cost = lookup(request.form.get("symbol"))['price'] * requested_shares
        user_cash = db.execute(
            "SELECT * FROM users WHERE id = :id", id=session["user_id"])[0]['cash']
        if cost > user_cash:
            return apology("Not enough cash to buy shares")

        # Register purchase
        db.execute("INSERT INTO transactions (transaction_type, user_id, stock_symbol, stock_name, stock_price, shares) VALUES (:transaction_type, :user_id, :stock_symbol, :stock_name, :stock_price, :shares)",
                   transaction_type='Bought',
                   user_id=session["user_id"],
                   stock_symbol=request.form.get("symbol"),
                   stock_name=lookup(request.form.get("symbol"))['name'],
                   stock_price=lookup(request.form.get("symbol"))['price'],
                   shares=request.form.get("shares"))

        # Update user shares portfolio
        user_shares = db.execute("SELECT * FROM shares WHERE user_id = :user_id AND stock_symbol = :stock_symbol",
                                 user_id=session["user_id"],
                                 stock_symbol=request.form.get("symbol"))

        if len(user_shares) == 1:
            current_shares = user_shares[0]['shares']
            updated_shares = current_shares + requested_shares
            db.execute("UPDATE shares SET shares = :shares WHERE user_id = :user_id AND stock_symbol = :stock_symbol",
                       shares=updated_shares,
                       user_id=session["user_id"],
                       stock_symbol=request.form.get("symbol"))

        else:
            db.execute("INSERT INTO shares (user_id, stock_symbol, stock_name, shares, stock_price, shares_value) VALUES (:user_id, :stock_symbol, :stock_name, :shares, :stock_price, :shares_value)",
                       user_id=session["user_id"],
                       stock_symbol=request.form.get("symbol"),
                       stock_name=lookup(request.form.get("symbol"))['name'],
                       shares=requested_shares,
                       stock_price=monetary(
                           lookup(request.form.get("symbol"))['price']),
                       shares_value=monetary(requested_shares * lookup(request.form.get("symbol"))['price']))

        # Update user balance
        db.execute("UPDATE users SET cash = :balance WHERE id = :id",
                   balance=(user_cash - cost), id=session["user_id"])
        return redirect("/")


# Show history of transactions
@app.route("/history")
@login_required
def history():
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = :user_id",
                              user_id=session["user_id"])
    return render_template("history.html", transactions=transactions)


# Log user in
@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Please provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Please provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET
    else:
        return render_template("login.html")


# Log user out
@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


# Get stock quote
@app.route("/quote", methods=["GET"])
@login_required
def quote():
    return render_template("quote.html")
 

# Rest method to get symbols
@app.route("/symbols/<symbol>", methods=["GET"])
@login_required
def symbols(symbol):
    try: symbol
    except NameError: x = None
    if symbol is not None: 
        return jsonify(search(symbol))
        
    else:
        #get all - paginated
        return jsonify(search())


# Rest method to get symbol quote
@app.route("/quote/<symbol>", methods=["POST"])
@login_required
def quote_rest(symbol):
    try: symbol
    except NameError: x = None
    
    # Error - no stock symbol provided
    if not symbol:
        return apology("Please provide a stock symbol.")

    # Error - invalid stock symbol
    if not lookup(symbol):
        return apology("Stock symbol not valid.")
        
    return jsonify(lookup(symbol))


# Rest method to get available stock
@app.route("/user/shares", methods=["GET"])
@login_required
def shares():
    shares_dict = db.execute("SELECT * FROM shares WHERE user_id = :user_id",
                            user_id=session["user_id"])
    print('Available user shares: {0}'.format(shares_dict))
    return jsonify(shares_dict)


# User registation
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        # Error - no username provided
        if not request.form.get("username"):
            return apology("Please provide a username.")

        # Error - username not unique
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        if len(rows) == 1:
            return apology("Username is already taken.")

        # Error - password not provided
        if not request.form.get("password"):
            return apology("Please provide a password.")

        # Error - confirmation password not provided
        if not request.form.get("confirmation"):
            return apology("Please confirm your password.")

        # Error - passwords don't match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords must match")

        # Store username and hased password into database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                   username=request.form.get("username"),
                   hash=generate_password_hash(request.form.get("password")))
        return redirect("/")


# Sell shares
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        return render_template("sell.html")
    else:
        # Error - no stock symbol provided
        if not request.form.get("symbol"):
            return apology("Please provide a stock symbol.")

        # Error - invalid stock symbol
        if not lookup(request.form.get("symbol")):
            return apology("Stock symbol not valid.")

        # Error - non-integer number of shares
        requested_shares = float(request.form.get("shares"))
        if not (requested_shares).is_integer():
            return apology("Number of shares must be an integer.")

        # Error - no shares of this type owned
        user_shares = db.execute("SELECT * FROM shares WHERE user_id = :user_id AND stock_symbol =:stock_symbol",
                                 user_id=session["user_id"], stock_symbol=request.form.get("symbol"))
        if len(user_shares) != 1:
            return apology("No such shares in portfolio")

        # Error - not enough shares of this type owned
        if requested_shares > user_shares[0]["shares"]:
            return apology("Not enough shares")

        # Register sale
        db.execute("INSERT INTO transactions (transaction_type, user_id, stock_symbol, stock_name, stock_price, shares) VALUES (:transaction_type, :user_id, :stock_symbol, :stock_name, :stock_price, :shares)",
                   transaction_type='Sold',
                   user_id=session["user_id"],
                   stock_symbol=request.form.get("symbol"),
                   stock_name=lookup(request.form.get("symbol"))['name'],
                   stock_price=lookup(request.form.get("symbol"))['price'],
                   shares=-requested_shares)

        # Update user shares portfolio
        current_shares = user_shares[0]['shares']
        updated_shares = current_shares - requested_shares
        if updated_shares == 0:
            db.execute("DELETE FROM shares WHERE user_id = :user_id AND stock_symbol = :stock_symbol",
                       user_id=session["user_id"],
                       stock_symbol=request.form.get("symbol"))
        else:
            db.execute("UPDATE shares SET shares = :shares, stock_price = :stock_price, shares_value = :shares_value WHERE user_id = :user_id AND stock_symbol = :stock_symbol",
                       shares=updated_shares,
                       stock_price=monetary(
                           lookup(request.form.get("symbol"))['price']),
                       shares_value=monetary(
                           updated_shares * lookup(request.form.get("symbol"))['price']),
                       user_id=session["user_id"],
                       stock_symbol=request.form.get("symbol"))

        # Update user balance
        user_cash = db.execute(
            "SELECT * FROM users WHERE id = :id", id=session["user_id"])[0]['cash']
        cost = requested_shares*lookup(request.form.get("symbol"))['price']
        db.execute("UPDATE users SET cash = :balance WHERE id = :id",
                   balance=user_cash+cost, id=session["user_id"])
        return redirect("/")


# Error handler
def errorhandler(e):
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)