from flask import Flask, Response, request
import json
import os
from os.path import join, dirname
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from fyers_api import fyersModel, accessToken
import psycopg2
from traceback import format_exc
from datetime import datetime, timezone


app = Flask(__name__)

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

client_id = os.environ['CLIENT_ID']
secret_key = os.environ.get('SECRET_KEY')
redirect_uri = os.environ.get('REDIRECT_URL')
app_id = client_id[:-4]

### DATABASE CONFIGS ###
db_host = os.environ['DB_HOSTNAME']
db_port = os.environ['DB_PORT']
db_user = os.environ['DB_USERNAME']
db_pass = os.environ['DB_PASSWORD']
db_database = os.environ['DB_DATABASE']

# class TokenNotFound(Exception):

#     def __init__(self, message="Token not found"):
#         self.message = message
#         print(self.message)
#         super().__init__(self.message)

# ALLOWED_API_NAMES = { 'get_profile': fyers.get_profile(),
#                       'funds': 'funds', 'holdings': 'holdings', 'history': 'history',
#                       'quotes': 'quotes' }


def read_file():
    with open("token_fyers.txt", "r") as f:
        token = f.read()
    return token


def write_file(token):
    with open('token_fyers.txt', 'w') as f:
        f.write(token)

def write_token_to_db(token):
    try:
        conn = psycopg2.connect(host=db_host, database=db_database, user=db_user, password=db_pass)
        cur = conn.cursor()
        cur.execute('INSERT INTO token (token, created_at) VALUES (%s, %s)', (token, datetime.now(timezone.utc)));
        conn.commit()
    except Exception as exc:
        print("Error occurred: %s. Traceback:: %s", str(exc), format_exc())
    finally:
        conn.close()

def read_token_from_db():
    try:
        conn = psycopg2.connect(host=db_host, database=db_database, user=db_user, password=db_pass)
        cur = conn.cursor()
        cur.execute("SELECT *  from token order by created_at asc")
        rows = cur.fetchall()
        token = None
        for row in rows:
            token = row[1]
            print("ID = ", row[0])
            print("Token = ", row[1])
        return token
    except Exception as exc:
        print("Error occurred: %s", str(exc))
    finally:
        conn.close()

session = accessToken.SessionModel(client_id=client_id, secret_key=secret_key,redirect_uri=redirect_uri, response_type='code', grant_type='authorization_code')

@app.route('/')
def index():  
    return 'Welcome. Get URL for auth code from get_authcode_url api'

@app.route('/get_authcode_url')
def get_auth_url(): 
    global session
    return session.generate_authcode() 

@app.route('/generate_token/<string:auth_code>')
def generate_access_token(auth_code):
    global session
    session.set_token(auth_code)
    response = session.generate_token()
    # print("generate_access_token: ", response["access_token"], type(response["access_token"]))
    return response["access_token"]


@app.route('/login')
def login():
    global session
    token = 'Could not login'
    if request.args.get('s') == 'ok':
        auth = request.args.get('auth_code')
        token = generate_access_token(auth_code=auth)
        # print("login: ", token, type(token))
        write_token_to_db(token)
    return Response(json.dumps({'access_token': token}), status=200, mimetype='application/json')


@app.route('/get_data')
def get_stock_data():
    stock = request.args.get('stock')
    print("Quotes API param", stock)
    try:
        data = {"symbols": stock}
        fyers = fyersModel.FyersModel(client_id=client_id, token=read_token_from_db(), log_path=os.getcwd())
        resp = fyers.quotes(data)
        print("Quotes response ::: ", resp)
        return Response(json.dumps({'data': resp.get('d')}), status=200, mimetype="application/json")
    except Exception as e:
        return Response({"data": str(e)}, status=500)


if __name__ == '__main__':
    app.run()
