import time

from flask import Flask, Response, request, send_from_directory
import json
import os
from os.path import join, dirname
from dotenv import load_dotenv
from fyers_api import fyersModel, accessToken
import psycopg2
from traceback import format_exc
from datetime import datetime, timezone
from fyers_api.Websocket import ws

app = Flask(__name__)
if os.environ.get('ENVIRONMENT', 'development') != 'PRODUCTION':
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
db_url = os.environ['DATABASE_URL']


# class TokenNotFound(Exception):

#     def __init__(self, message="Token not found"):
#         self.message = message
#         print(self.message)
#         super().__init__(self.message)

# ALLOWED_API_NAMES = { 'get_profile': fyers.get_profile(),
#                       'funds': 'funds', 'holdings': 'holdings', 'history': 'history',
#                       'quotes': 'quotes' }


def write_token_to_db(token):
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute('INSERT INTO token (token, created_at) VALUES (%s, %s)', (token, datetime.now(timezone.utc)))
        conn.commit()
    except Exception as exc:
        print("Error occurred: %s. Traceback:: %s", str(exc), format_exc())
    finally:
        conn.close()


def read_token_from_db():
    try:
        conn = psycopg2.connect(db_url)
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


session = accessToken.SessionModel(client_id=client_id, secret_key=secret_key, redirect_uri=redirect_uri,
                                   response_type='code', grant_type='authorization_code')


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
        fyers = fyersModel.FyersModel(client_id=client_id, token=read_token_from_db(),
                                      log_path=join(dirname(__file__), 'log'))
        resp = fyers.quotes(data)
        print("Quotes response ::: ", resp)
        return Response(json.dumps({'data': resp.get('d')}), status=200, mimetype="application/json")
    except Exception as e:
        return Response({"data": str(e)}, status=500)


@app.route('/get_live_data')
def get_live_stock_data():
    stock = request.args.get('stock')
    print("Live data API param", stock)
    access_token = read_token_from_db()
    try:
        feed_token = client_id + ":" + access_token
        data_type = 'symbolData'
        symbol = [stock]
        ws.websocket_data = custom_message
        fyers_socket = ws.FyersSocket(access_token=feed_token, run_background=False,
                                      log_path=join(dirname(__file__), 'log'))
        fyers_socket.subscribe(symbol=symbol, data_type=data_type)
        time.sleep(5)
    except Exception as e:
        return Response({"data": str(e)}, status=500)


def custom_message(self):
    print("Custom " + str(self.response))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


if __name__ == '__main__':
    app.run()
