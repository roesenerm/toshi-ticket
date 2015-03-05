from flask import Flask, render_template, redirect, url_for, request, jsonify, make_response, session, flash
from flask.ext.pymongo import PyMongo
import pymongo
from pymongo import Connection
from functools import *
import json
import requests
from urllib2 import Request, urlopen
from time import gmtime, strftime


app = Flask(__name__)
app.secret_key = "temp secret"
mongo = PyMongo(app)

conn = Connection()
db = conn.dbZero

tokens = db.tokens
posts = db.posts


CLIENT_ID = '40335456568a0fd8a01e934b18b83df11a58b0cf1bb7adfaa4dfeb57e247652e'
CLIENT_SECRET = '591828d95d35aa6179316409b9e016f3a1dd78af14bfe142efff2a3aa9bd40ef'
YOUR_CALLBACK_URL = 'http://127.0.0.1:5000/consumer_auth'

def login_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('You need to login first.')
			return redirect(url_for('login'))
	return wrap

@app.route('/oauthlogin')
def register_me():

	auth_url = 'https://www.coinbase.com/oauth/authorize?response_type=code&client_id='+ CLIENT_ID +'&redirect_uri='+ YOUR_CALLBACK_URL

	return render_template('register.jinja2', auth_url=auth_url)

@app.route('/consumer_auth')
def recieve_token():

	oauth_code = request.args['code']

	url = 'https://www.coinbase.com/oauth/token?grant_type=authorization_code&code='+oauth_code+'&redirect_uri='+YOUR_CALLBACK_URL+'&client_id='+CLIENT_ID+'&client_secret='+CLIENT_SECRET

	r = requests.post(url)

	data = r.json()

	access_token = data['access_token']

	print access_token

	refresh_token = data['refresh_token']

	if access_token == None:
		print "False"
		return redirect(url_for('/'))
	else:
		print "True"
		session['logged_in'] = True

		t = strftime("%Y-%m-%d %H:%M:%S", gmtime())
		print t
		db.tokens.insert({'created_at':t,'token': access_token})

		lastToken = tokens.find().sort([("created_at", pymongo.DESCENDING)])
		print lastToken.next()['token']

		return redirect(url_for('explore'))

#Cover Page
@app.route('/')
def home():
	auth_url = 'https://www.coinbase.com/oauth/authorize?response_type=code&client_id='+ CLIENT_ID +'&redirect_uri='+ YOUR_CALLBACK_URL

	return render_template("cover2.html", auth_url=auth_url)

#Welcome Page
@app.route('/welcome')
@login_required
def welcome():
	return render_template("welcome.html")

@app.route('/explore', methods=['GET', 'POST'])
#@login_required
def explore():

	posts = db.posts.find()

	lastToken = tokens.find().sort([("created_at", pymongo.DESCENDING)])
	token = lastToken.next()['token']

	error = None
	if request.method == 'POST':

		uri = 'https://api.coinbase.com/v1/addresses?access_token=' + token

		j = requests.get(uri)

		addresses = j.json()

		to_public_address = str(addresses['addresses'][-1]['address']['address'])

		from_public_address = str(request.form['from_public_address'])

		issuing_public_address = str(request.form['issuing_public_address'])

		from_private_key = db.posts.find({"issuing_public_address":issuing_public_address})

		from_private_key = from_private_key.next()['issuing_private_key']

		transfer_amount = int(request.form['transfer_amount'])

		fee_each = 0.00005

		headers = {'Content-Type':'application/json'}
		payload = {'from_public_address': from_public_address, 'from_private_key': from_private_key, 'transfer_amount': transfer_amount, 'to_public_address': to_public_address, 'issuing_address': issuing_public_address, 'fee_each': fee_each}

		print "json"
		print json.dumps(payload)

		r = requests.post('https://coins.assembly.com/v1/transactions/transfer', data=json.dumps(payload), headers=headers)

		print r.status_code


		return jsonify(r.json())

	return render_template("explore.html", posts=posts)


#Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	auth_url = 'https://www.coinbase.com/oauth/authorize?response_type=code&client_id='+ CLIENT_ID +'&redirect_uri='+ YOUR_CALLBACK_URL

	return render_template('login.html', error=error, auth_url=auth_url)

#Logout
@app.route('/logout')
@login_required
def logout():
	session.pop('logged_in', None)
	flash('You were just logged out!')
	return redirect(url_for('login'))

#Profile Page
@app.route('/profile', methods=['GET', 'POST'])
#@login_required
def profile():

	lastToken = tokens.find().sort([("created_at", pymongo.DESCENDING)])
	token = lastToken.next()['token']

	uri = 'https://api.coinbase.com/v1/addresses?access_token=' + token

	r = requests.get(uri)

	print r.status_code

	addresses = r.json()

	my_address = addresses['addresses'][-1]['address']['address']

	print my_address

	r = requests.get('https://coins.assembly.com/v1/addresses/' + my_address)

	response = r.json()
	my_assets = response['assets']

	print my_assets

	return render_template("profile.html", my_address=my_address, my_assets=my_assets)

# Create unique coin
@app.route('/issuecoin', methods=['GET', 'POST'])
#@login_required
def issueCoin():
	error = None
	if request.method == 'POST':
		headers = {'Content-Type':'application/json'}
		payload = {'issued_amount': request.form['issuedamount'], 'description': request.form['description'], 'coin_name': request.form['coin_name'], 'email': request.form['email']}

		print payload

		r = requests.post('https://coins.assembly.com/v1/colors/prepare', data=json.dumps(payload), headers=headers)

		print r.status_code

		issuance = r.json()

		issuing_private_key = issuance['issuing_private_key']
		name = issuance['name']
		minting_fee = 0.002
		issuing_public_address = issuance['issuing_public_address']

		# message payload
		'''
		message_payload = {'public_address':issuing_public_address, 'fee_each':minting_fee, 'private_key':issuing_private_key, 'message': request.form['ticketprice']}
		message = requests.post('https://coins.assembly.com/v1/messages', data=json.dumps(message_payload),headers=headers)

		print message.status_code
		'''
		#message payload

		qrcode = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=" + issuing_public_address

		image = request.form['image']

		lastToken = tokens.find().sort([("created_at", pymongo.DESCENDING)])
		token = lastToken.next()['token']

		sendBitcoin(issuing_public_address, minting_fee, token)

		posts.insert({'issuing_public_address': issuing_public_address, 'issuing_private_key': issuing_private_key, 'name': name, 'qrcode': qrcode, 'image': image})

		return render_template("issuance.html", issuing_private_key=issuing_private_key, name=name, minting_fee=minting_fee, issuing_public_address=issuing_public_address, qrcode=qrcode, image=image)

	return render_template("issuecoin.html")

# Transfer coins to different account
@app.route('/transfercoin', methods=['GET', 'POST'])
@login_required
def transferCoin():
	error = None
	if request.method == 'POST':
		headers = {'Content-Type':'application/json'}
		payload = {'from_public_address': request.form['from_public_address'], 'from_private_key': request.form['from_private_key'], 'transfer_amount': request.form['transfer_amount'], 'to_public_address': request.form['to_public_address'], 'issuing_address': request.form['issuing_address'], 'fee_each': 5e-05}

		r = requests.post('https://coins.assembly.com/v1/transactions/transfer', data=json.dumps(payload), headers=headers)

		return jsonify(r.json())

	return render_template("transfercoin.html")

def buyTicket(from_public_address, from_private_key, issuing_public_address):
	error = None

	#tokens = TokenPosts.query.all()
	#token = str(tokens[-1])

	uri = 'https://api.coinbase.com/v1/addresses?access_token=' + token

	r = requests.get(uri)

	addresses = r.json()

	to_public_address = addresses[0]

	if request.method == 'POST':
		headers = {'Content-Type':'application/json'}
		payload = {'from_public_address': from_public_address, 'from_private_key': from_private_key, 'transfer_amount': request.form['transfer_amount'], 'to_public_address': to_public_address, 'issuing_address': issuing_address, 'fee_each': 5e-05}

		r = requests.post('https://coins.assembly.com/v1/transactions/transfer', data=json.dumps(payload), headers=headers)

		return jsonify(r.json())
		#return render_template("buyconfirmation.html")

def sellTicket():
	pass

def sendBitcoin(issuing_public_address, minting_fee, token):

	error = None
	if request.method == 'POST':
		headers = {'Content-Type':'application/json'}
		payload = {'transaction': {'to': issuing_public_address,
			'amount': minting_fee,
			'notes': 'Official ticket issuance with minting fee',
			'user_fee': 0.0002
		}}

	r = requests.post('https://api.coinbase.com/v1/transactions/send_money?access_token='+ token, data=json.dumps(payload), headers=headers)

	print r.json()

	print "sent"

# Check coin balance
@app.route('/checkcoin', methods=['GET', 'POST'])
#@login_required
def checkCoin():
	error = None
	if request.method == 'POST':
		headers = {'Content-Type':'application/json'}
		public_address = request.form['from_public_address']

		print public_address

		r = requests.get('https://coins.assembly.com/v1/addresses/' + public_address)

		response = r.json()

		print response
		assets = response['assets']

		print assets

		#qrcode = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=" + color_address

		return render_template("balance.html", assets=assets)


	return render_template("checkCoin.html")

@app.route('/artist')
@login_required
def artist():

	posts = db.posts.find()

	return render_template('artist.html', posts=posts)


# Graph example
@app.route('/graph')
@login_required
def graph(chartID = 'chart_ID', chart_type = 'line', chart_height = 500):
    chart = {"renderTo": chartID, "type": chart_type, "height": chart_height,}
    series = [{"name": 'Coin1', "data": [1,2,3]}, {"name": 'Coin2', "data": [4, 5, 6]}]
    pageType = 'graph'
    title = {"text": 'Coin Price'}
    xAxis = {"categories": ['xAxis Data1', 'xAxis Data2', 'xAxis Data3']}
    yAxis = {"title": {"text": 'Price'}}
    return render_template('graph.html', pageType=pageType, chartID=chartID, chart=chart, series=series, title=title, xAxis=xAxis, yAxis=yAxis)

@app.route('/graph2')
def graph2():
	return render_template('graph2.html')


if __name__ == '__main__':
	app.run(debug=True)