import os
import requests
import urllib.parse
from flask_paginate import Pagination, get_page_parameter
from flask import redirect, render_template, request, session
from functools import wraps

symbols = {}

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


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None

def search(text):
    #Check cache first
    print('Searching for {0}'.format(text))
    result = []
    if len(symbols) != 0:
        print('Cached symbols: {0}'.format(len(symbols)))
        for key,value in symbols.items():
            if text is not None and text.lower() in key.lower() or text.lower() in value['name'].lower():
                result.append(symbols.get(key))
    else:
        # Contact API
        try:
            api_key = os.environ.get("API_KEY")
            response = requests.get(f"https://cloud.iexapis.com/stable/ref-data/exchange/nas/symbols?token={api_key}&filter=symbol,name")
            response.raise_for_status()
        except requests.RequestException:
            return None
        
        # Parse response
        #try:
        fetched = response.json()
        print(len(fetched))
        for r in fetched:
            symbols[str(r['symbol'])] = {"symbol": str(r['symbol']), "name": str(r['name'])}
            if text is not None and (text.lower() in r['symbol'].lower() or text.lower() in r['name'].lower()):
                result.append(symbols[str(r['symbol'])])
           
        #except Exception as e:
            #print('Caught exception: {0}'.format(e))
           # return None
    if len(result) > 0:
        stuffs = result[0: 0 + 10]
        print('res: {0}'.format(stuffs))
        return stuffs
    else:
        return {}

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def monetary(value):
    """Format value as USD."""
    return round(value,2)