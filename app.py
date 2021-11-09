from flask import Flask, Response
import json
import os
import sys
from urllib.parse import urlparse, parse_qs
from fyers_api import fyersModel, accessToken
import requests

app = Flask(__name__)

username = os.environ['USERNAME']
password = str(os.environ.get('PASSWORD'))
pan = os.environ.get('PAN')
client_id = os.environ['CLIENT_ID']
secret_key = os.environ.get('SECRET_KEY')
redirect_uri = os.environ.get('REDIRECT_URL')
app_id = client_id[:-4]

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


def setup():
    session = accessToken.SessionModel(client_id=client_id, secret_key=secret_key, redirect_uri=redirect_uri,
                                       response_type='code', grant_type='authorization_code')

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                       Chrome/94.0.4606.81 Safari/537.36',
        'content-type': 'application/json; charset=UTF-8',
        'accept-language': 'en-US,en;q=0.9'}

    data = f'{{"fyers_id":"{username}","password":"{password}","pan_dob":"{pan}","app_id":"{app_id}","redirect_uri":"{redirect_uri}","appType":"100","code_challenge":"","state":"abcdefg","scope":"","nonce":"","response_type":"code","create_cookie":true}}'
    resp = requests.post('https://api.fyers.in/api/v2/token', headers=headers, data=data)

    parsed = urlparse(resp.json()['Url'])
    auth_code = parse_qs(parsed.query)['auth_code'][0]
    session.set_token(auth_code)
    response = session.generate_token()
    token = response["access_token"]
    write_file(token)
    print('Got the access token!!!')
    fyers = fyersModel.FyersModel(client_id=client_id, token=token, log_path=os.getcwd())
    print(fyers.get_profile())


def check():
    try:
        token = read_file()
    except FileNotFoundError:
        print('Getting the access token!')
        setup()
        sys.exit()
    else:
        fyers = fyersModel.FyersModel(client_id=client_id, token=token, log_path=os.getcwd())
        response = fyers.get_profile()
        if 'error' in response['s'] or 'error' in response['message'] or 'expired' in response['message']:
            print('Getting a access token!')
            setup()
        else:
            print('You already have a access token!')
            print(response)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


@app.route('/login')
def login():
    check()
    resp = {'app_token': read_file()}
    return Response(json.dumps(resp), status=200, mimetype='application/json')


@app.route('/get_data/<string:stock>')
def get_stock_data(stock):
    try:
        data = {"symbols": stock}
        fyers = fyersModel.FyersModel(client_id=client_id, token=read_file(), log_path=os.getcwd())
        resp = fyers.quotes(data)
        return Response(json.dumps({'data': resp.get('d')}), status=200, mimetype="application/json")
    except Exception as e:
        return Response({"data": str(e)}, status=500)


if __name__ == '__main__':
    app.run()
