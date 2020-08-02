#API For Polyglot Parrot

#Import statements
from flask import Flask, jsonify, request, redirect, url_for, abort
from flask_restful import Resource
from werkzeug.utils import secure_filename
from feed_element import feed_element
import os
import bson
import pymongo
import sqlite3
import re
from datetime import datetime
from markovModel import markovModel
import bcrypt
from random import shuffle
from pymongo import MongoClient
import json
from bson.objectid import ObjectId

#App Set Up
app = Flask(__name__)

#Encryption Salt setup
salt = bcrypt.gensalt()

#Database Setup
#polyglot_db
client = MongoClient()
polyglot_db = client.polyglot_db
#analytics_db
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), 'ad.sqlite3')
analytics_db = sqlite3.connect(DEFAULT_PATH)

#Controller

#User Data
#Get: Returns a JSON File containing the user's information
#Post: Posts a new user to the SI Database
#Formating
# userName -> user's chosen username
# firstName -> user's given name
# lastName -> user's surname
# profilePic -> user's profile picture in a string base64
# languages -> list of user's languages
# friends -> list of id's of user's friends
#TODO: add Token to ensure only authenticated sources are posting
@app.route('/api/user/<username>/<password>', methods = ['GET'])
@app.route('/api/user', methods = ['POST'])
@app.route('/api/user', methods = ['PUT'])
def user(username = None, password = None):
	if request.method == 'GET':
		credentials = polyglot_db.users.find({"username": username})
		if (not credentials.count() == 1):
			return 'bad request: single username "' + username + '" not found', 400
		encrypted = credentials[0]['password']
		print(credentials)
		if (encrypted == bcrypt.hashpw(password.encode(), encrypted)):
			#TODO: Record user logged into app in the Analytics Database
			user = jsonify(str(credentials[0]))
			return user
		else:
			return 'bad request: authentication failed', 400
	elif request.method == 'POST':
		username = request.json['username']
		password = request.json['password']
		credentials = polyglot_db.users.find({"username": username})
		if credentials.count() == 0:
			encrypted = bcrypt.hashpw(password.encode(), salt)
			request.json['password'] = encrypted
			polyglot_db.users.insert(request.json)
			return jsonify(str(polyglot_db.users.find({"username": username})[0]))
		else:
			return 'bad request: username taken', 400
	elif request.method == 'PUT':
		user_id = ObjectId(request.json['_id'])
		credentials = polyglot_db.users.find({"_id": user_id})
		if credentials.count() == 1:
			#updates only fields allowed to be updated
			polyglot_db.users.update({'_id':user_id},{"$set":{ "firstName": request.json['firstName'], "lastName": request.json['lastName'], "profilePic": request.json['profilePic'], "weeklyProgress": request.json['weeklyProgress'] } },upsert=False)#({ "_id": user_id },{$set: { "firstName": request.json['firstName'], "lastName": request.json['lastName'], "profilePic": request.json['profilePic'], "weeklyProgress": request.json['weeklyProgress'] }})
			return jsonify(str(polyglot_db.users.find({"_id": user_id})[0]))
		else:
			return 'bad request: user not found', 400



#Feed Element Data
#Get: Obtains all feed elements for a user's feed
#Post: Posts a new feed to the Post Database (returns list of elements)
#Formatting
#feedElements
# ->username: userName of each friend
# ->posts
# ->->userName: userName of the post
# ->->text: the text displayed by the post
# ->->likes: the likes a post has
# ->->dislikes: the dislikes a post has
# ->->idNum: the id number of a post
#photos
#->photo: returns the photo of the specified user
@app.route('/api/feedElements/<username>/<getFriends>', methods = ['GET'])
@app.route('/api/feedElements/<username>/<text>', methods = ['POST'])
@app.route('/api/feedElements/<_id>', methods = ['PUT'])
def feed_elements(username = None, getFriends = False, text = None, _id = None):
	if request.method == 'POST':
		text = text.replace("+", " ")
		language = markovModel().get_likeliest(text)
		new_feed_element = {"username": username,  "text": text, "likes": 0, "dislikes": 0, "language": language, "likers": []}
		polyglot_db.feed_elements.insert(new_feed_element)
		result = dict()
		result['feedElements'] = list(polyglot_db.feed_elements.find({'username': username}))
		return str(result), 200
	elif request.method == 'GET':
		result = dict()
		result['feedElements'] = {}
		result['feedElements'][username] = list(polyglot_db.feed_elements.find({'username': username}))
		friends = polyglot_db.users.find({'username': username})[0]['friends']
		if getFriends:
			for friend in friends:
				result['feedElements'][friend] = list(polyglot_db.feed_elements.find({'username': friend}))
		return str(result), 200
	elif request.method == 'PUT':
		#requires a feed_element body
		new_feed_element = {'username': request.json['username'], 'text': request.json['text'], 'likes': request.json['likes'], 'dislikes': request.json['dislikes'], 'language': request.json['language'],'likers': request.json['likers'] }
		polyglot_db.users.update({"_id": ObjectId(_id)},{"$set":new_feed_element},upsert=False)
		return jsonify(new_feed_element), 200

#Friend Request Data
#Get: Obtains all friend Request Datas for a specific user
#Post: Sends a Friend Request, uploading it to the SID
#Delete: Accepts or Rejects a Friend Request, deleting it from the SID
#Formatting
#requests
#->userName: requester's userName
#->firstName: requester's given name
#->lastName: requester's surname
#->profilePic: requester's profile picture in a string base64
#->languages: an array of languages the requester is interested in/knows/learning
#->friends: an array of the requester's friends
@app.route('/api/friendrequest/<accepter>/<requester>/<accepted>', methods = ['DELETE'])
@app.route('/api/friendrequest/<accepter>/<requester>', methods = ['POST'])
@app.route('/api/friendrequest/<accepter>', methods = ['GET'])
def friendrequest(accepter, requester = '', accepted = 'False'):
	if request.method == 'POST':
		friend_request = {'requester': requester, 'accepter': accepter}
		polyglot_db.friendRequests.insert(friend_request)
		#notifications(accepter, requester, "@" + requester + " has sent you a friend request!")
		return jsonify(str(friend_request)), 200
	elif request.method == 'DELETE':
		friend_request = {'requester': requester, 'accepter': accepter}
		if accepted == False:
			polyglot_db.friendRequests.remove(friend_request)
			return []
		elif accepted == True:
			requester = polyglot_db.users.find({"username": requester})[0]
			accepter = polyglot_db.users.find({"username": accepter})[0]
			requester_friends = requester['friends']
			accepter_friends = accepter['friends']
			requester_friends.append(accepter)
			accepter_friends.append(requester)
			polyglot_db.users.update({'_id': requester['_id']},{'$set': {'friends': requester_friends}}, upsert=False)
			polyglot_db.users.update({'_id': accepter['_id']},{'$set': {'friends': accepter_friends}}, upsert=False)
			polyglot_db.friendRequests.remove(friend_request)
			results = dict()
			results["friends"] = accepter_friends
			#notifications(requester, accepter, "You are now friends with" + accepter + "!")
			#notifications(accepter, requester, "You are now friends with" + requester + "!")
			return jsonify(results), 200
	elif request.method == 'GET':
		friend_requests = polyglot_db.friendRequests
		request_list = friend_requests.find({'accepter': accepter})
		data = {}
		data['requests'] = []
		for x in range(request_list.count()):
			requester = polyglot_db.users.find({"userName": requestList[x]['requester']})
			data['requests'].append({
				'username': requester[0]['username'],
				'firstname': requester[0]['firstname'],
				'lastname': requester[0]['lastname'],
				'profilePic': requester[0]['profilePic'],
				'languages': requester[0]['languages'],
				'friends': requester[0]['friends']
				})
		return jsonify(data)

#Friends Data
#Get: obtains data for all friends to be displayed
#TODO: Use ML to get recommended in the future
#Simple return for right now
#Formatting:
#recommended
# userName -> a user's chosen username
# firstName -> a user's given name
# lastName -> a user's surname
# profilePic -> a user's profile picture in a string base64
#languages -> an array of languages a user is interested in/knows/learning
#friends -> an array of that user's friends
@app.route('/api/friends/<userName>', methods = ['GET'])
def friends(userName):
	user = polyglot_db.users.find({"username": username})[0]
	result = {}
	result['recommended'] = []
	result['friends'] = []
	similarData = polyglot_db.users.find().limit(10)
	for x in range(similarData.count()):
		if similarData[x]['username'] == username:
			continue
		else:
			data['recommended'].append({
				'username': similarData[x]['username'],
				'firstName': similarData[x]['firstName'],
				'profilePic': similarData[x]['profilePic'],
				'languages': similarData[x]['languages'],
				'friends': similarData[x]['friends']
				})
	for friend in user['friends']:
		friend_data = SID.userList.find({"userName": friend})[0]
		data['friends'].append({
			'username': friend_data['username'],
			'profilePic': friend_data['profilePic'],
			'weeklyProgress': friend_data['weeklyProgress']
			})
	return jsonify(data)
"""
#Notifications Data
#Get: Obtains all notifications to a user
#Post: Sends a Notification to the SID
#Formatting
#notifications
# -> sender: who the notification comes from
# -> to: the user's name, reiterated
# -> message: content of the notification
@app.route('/api/notifications/<to>', methods = ['GET'])
@app.route('/api/notifications/<to>/<sender>/<message>', methods = ['POST'])
def notifications(to, sender = '', message = ''):
	if request.method == 'POST':
		SID.notifications.insert_one({'sender': sender, 'to': to, 'message': message})
	elif request.method == 'GET':
		data = {}
		data['notifications'] = []
		notificationPile = SID.notifications.find({'to': to})
		for x in range(notificationPile.count()):
			data['notifications'].append({
				'sender': notificationPile[x]['sender'],
				'to': notificationPile[x]['to'],
				'message': notificationPile[x]['message']
				})
		return jsonify(data)
"""

"""

Note: Every Endpoint below this line is commented out. This is because it is all part of a language progression feature, which used bad practices w/ databases. 




#TODO: Rename to follow convention
#LanguageProgress
#Obtains User's Data
#If there is no record of the language, one is added
#PUT updates status of a user
@app.route('/languageProgress/<userName>/<language>/<checkP>', methods = ['PUT'])
@app.route('/languageProgress/<userName>/<language>', methods = ['GET'])
def languageProgress(userName, language, checkP = ""):
	if request.method == 'GET':
		data = {}
		data['checkPoints'] = []
		schema = SID.langProg.find({"userName": "schema", "language": language})[0]
		cps = schema['cpCount']
		stack = SID.langProg.find({"userName": userName, "language": language})
		if stack.count() == 0:
			SID.langProg.insert_one({"userName": userName, "language": language})
			idNum = SID.langProg.find({"userName": userName, "language": language})[0]['_id']
			for x in range(cps):
				line = "cp" + str(x + 1)
				SID.langProg.update_one({"_id": idNum}, {"$set": {line: False}})
			stack = SID.langProg.find({"userName": userName, "language": language})[0]
			credentials = SID.userList.find({"userName": userName})[0]
			languages = credentials['Languages']
			languages.append(language)
			toUpdateID = credentials['_id']
			SID.userList.update_one({'_id': toUpdateID},{'$set': {'Languages': languages}}, upsert=False)
		else:
			stack = stack[0]
		for x in range(cps):
			line = "cp" + str(x + 1)
			status = stack[line]
			data['checkPoints'].append({
				"status": status,
				"cp" : line,
				line: schema[line]
				})
		return jsonify(data)
	elif request.method == 'PUT':
		stack = SID.langProg.find({"userName": userName, "language": language})[0]
		toUpdateID = stack['_id']
		schema = SID.langProg.find({"userName": "schema", "language": language})[0]
		cps = schema['cpCount']
		for x in range(cps):
			line = 'cp' + str(x + 1)
			if schema[line] == checkP:
				checkP = line
				break
		SID.langProg.update_one({'_id': toUpdateID},{'$set': {checkP: True}}, upsert=False)
		return "HTML 200"

#Internal Update of Language Progress
def languageProgressUpdate(userName, language, checkP = ""):
	stack = SID.langProg.find({"userName": userName, "language": language})[0]
	toUpdateID = stack['_id']
	schema = SID.langProg.find({"userName": "schema", "language": language})[0]
	cps = schema['cpCount']
	for x in range(cps):
		line = 'cp' + str(x + 1)
		if schema[line] == checkP:
			checkP = line
			break
	SID.langProg.update_one({'_id': toUpdateID},{'$set': {checkP: True}}, upsert=False)
	updateWeeklyProgress(userName, 100)
	return "HTML 200"

#Exam Portion of the API
@app.route('/api/exam/<userName>/<language>/<topic>/<idNum>/<answer>', methods = ['PUT'])
@app.route('/api/exam/<userName>/<language>/<topic>', methods = ['GET'])
def exam(userName, language, topic, idNum = "", answer = ""):
	if request.method == 'GET':
		#Return ten questions, with their answers randomized
		cur2 = examAnswers.cursor()
		cur2.execute("DELETE FROM answersDB WHERE userName = ?", (userName,))
		category = "" + language + topic
		cur = questions.cursor()
		cur.execute("SELECT * FROM questionDB WHERE topic =?", (category,))
		rows = cur.fetchall()
		data = {}
		data['questions'] = []
		for row in rows:
			rA = row[3]
			answers = []
			answers.append(rA)
			answers.append(row[4])
			answers.append(row[5])
			answers.append(row[6])
			shuffle(answers)
			data['questions'].append({
				'qText': row[2],
				'a': answers[0],
				'b': answers[1],
				'c': answers[2],
				'd': answers[3],
				'id': row[0]
				})
			cur2.execute("INSERT INTO answersDB (questionID, userName, rA) VALUES (?, ?, ?)", (row[0] , userName, rA))
		cur2.execute("INSERT INTO answersDB (questionID, userName, rA) VALUES (?, ?, ?)", ('record' , userName, '0'))
		examAnswers.commit()
		return jsonify(data)
	elif request.method == 'PUT':
		data = {}
		data['result'] = []
		data['updated'] = False
		answer.replace('+', ' ')
		cur = examAnswers.cursor()
		cur.execute('SELECT rA FROM answersDB WHERE questionID=? AND userName=?', (idNum, userName))
		rows = cur.fetchall()
		for row in rows:
			if answer == row[0]:
				data['result'].append(True)
				updateWeeklyProgress(userName, 10)
				cur.execute("SELECT rA FROM answersDB WHERE questionID = 'record' AND userName = ?", (userName,))
				rows2 = cur.fetchall()
				x = int(rows2[0][0]) + 1
				if x == 7:
					languageProgressUpdate(userName, language, topic)
					data['updated'] = True
				cur.execute("UPDATE answersDB SET rA = ? WHERE questionID = 'record' AND userName = ?", (x,userName))
				cur.execute("DELETE FROM answersDB WHERE userName = ? AND questionID = ?", (userName,idNum))
				examAnswers.commit()
			else:
				data['result'].append(False)
				cur.execute("DELETE FROM answersDB WHERE userName = ? AND questionID = ?", (userName,idNum))
				examAnswers.commit()
		return jsonify(data)

"""




if __name__ == '__main__':
	app.debug = True
	app.run(host='0.0.0.0', port=3000)



