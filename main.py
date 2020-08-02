#API For Polyglot Parrot Server Side

#Acronyms
#SID = user_db now -> Implemented w/ MongoDB
#AD = Analytics Database -> Implemented w/ SQLite3

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
			#updates all fields allowed to be updated without extra steps
			polyglot_db.users.update({'_id':user_id},{"$set":{ "firstName": request.json['firstName'], "lastName": request.json['lastName'], "profilePic": request.json['profilePic'], "weeklyProgress": request.json['weeklyProgress'] } },upsert=False)#({ "_id": user_id },{$set: { "firstName": request.json['firstName'], "lastName": request.json['lastName'], "profilePic": request.json['profilePic'], "weeklyProgress": request.json['weeklyProgress'] }})
			return jsonify(str(polyglot_db.users.find({"_id": user_id})[0]))
		else:
			return 'bad request: user not found', 400



#Feed Element Data
#Get: Obtains all feed elements for a user's feed
#Post: Posts a new feed to the Post Database (returns list of elements)
#Formatting
#feedElements
# ->userName: userName of each friend
# ->posts
# ->->userName: userName of the post
# ->->text: the text displayed by the post
# ->->likes: the likes a post has
# ->->dislikes: the dislikes a post has
# ->->idNum: the id number of a post
#photos
#->photo: returns the photo of the specified user
@app.route('/api/feedElements/<username>', methods = ['GET'])
@app.route('/api/feedElements/<username>/<text>', methods = ['POST'])
def feed_elements(username, text = None):
	if request.method == 'POST':
		text = text.replace("+", " ")
		language = markovModel().get_likeliest(text)
		new_feed_element = feed_element(username, text, 0, 0, language, [])
		encoded_element = bson.BSON.encode(new_feed_element.__dict__)
		polyglot_db.feed_elements.insert({'username': username,  'post': encoded_element})
		result = dict()
		result['feedElements'] = list(polyglot_db.feed_elements.find({'username': username}))
		return str(result), 200
	elif request.method == 'GET':
		result = dict()
		result['feedElements'] = list(polyglot_db.feed_elements.find({'username': username}))
		return str(result), 200
	"""
		credentials = SID.userList.find({"userName": userName})
		posters = []
		data = {}
		data['feedElements'] = []
		friendsList = credentials[0]['friends']
		friendsList.append(userName)
		i = 0
		for friend in friendsList:
			pile = SID.postList.find({"userName": friend})
			data['feedElements'].append({  
				'userName': friend,
				'posts': []
				})
			if not friend in posters:
				posters.append(friend)
				credentials = SID.userList.find({"userName": friend})
				data[friend] = credentials[0]["ProfilePic"]
			for feedElemen in pile:
				decoded = feedElemen['post']
				decoded = bson.BSON.decode(decoded)
				data['feedElements'][i]['posts'].append(decoded)
			i += 1
		return jsonify(data)
	"""
"""

#TODO: Combine this with method above it
#Like a Feed Element
#Simple interaction with the Database Method
#Adds or Removes a like from the specified post.
#Updates it in the Database
@app.route('/api/feedElement/<userName>/<postID>', methods = ['PUT'])
def feedElement(userName, postID):
	postStack = SID.postList.find({'idNum': int(postID)})
	decoded = postStack[0]['post']
	decoded = bson.BSON.decode(decoded)
	if not userName in decoded['likers']:
		print(int(decoded['likes']) + 1)
		decoded['likers'].append(userName)
		newPost = feedElement(decoded['userName'], decoded['text'], int(decoded['likes']) + 1, decoded['dislikes'], postID, decoded['language'], decoded['likers'])
	else:
		decoded['likers'].remove(userName)
		newPost = feedElement(decoded['userName'], decoded['text'], int(decoded['likes']) - 1, decoded['dislikes'], postID, decoded['language'], decoded['likers'])
	toUpdateID = postStack[0]['_id']
	newPost = bson.BSON.encode(newPost.__dict__)
	SID.postList.update_one({'_id':toUpdateID}, {'$set': {'post': newPost}}, upsert=False )
	return 'HTML 200'

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
@app.route('/api/friendRequest/<accepter>/<requester>/<accepted>', methods = ['DELETE'])
@app.route('/api/friendRequest/<accepter>/<requester>', methods = ['POST'])
@app.route('/api/friendRequest/<accepter>', methods = ['GET'])
def friendRequests(accepter, requester = '', accepted = 'False'):
	if request.method == 'POST':
		friendRequests = SID.friendRequests
		friendRequests.insert_one({'requester': requester, 'accepter': accepter})
		notifications(accepter, requester, "@" + requester + " has sent you a friend request!")
		return 'HTML 200'
	elif request.method == 'DELETE':
		if accepted == 'False':
			friendRequests = SID.friendRequests
			friendRequests.delete_one({'requester': requester, 'accepter': accepter})
			return 'HTML 200'
		elif accepted == 'True':
			requesterData = SID.userList.find({"userName": requester})
			accepterData = SID.userList.find({"userName": accepter})
			requesterFriends = requesterData[0]['friends']
			accepterFriends = accepterData[0]['friends']
			requesterFriends.append(accepter)
			accepterFriends.append(requester)
			requesterID = requesterData[0]['_id']
			accepterID = accepterData[0]['_id']
			SID.userList.update_one({'_id': requesterID},{'$set': {'friends': requesterFriends}}, upsert=False)
			SID.userList.update_one({'_id':accepterID}, {'$set': {'friends': accepterFriends}}, upsert=False )
			friendRequests = SID.friendRequests
			friendRequests.delete_one({'requester': requester, 'accepter': accepter})
			notifications(requester, accepter, "You are now friends with" + accepter + "!")
			notifications(accepter, requester, "You are now friends with" + requester + "!")
			return 'HTML 200'
	elif request.method == 'GET':
		friendRequests = SID.friendRequests
		requestList = friendRequests.find({'accepter': accepter})
		data = {}
		data['requests'] = []
		for x in range(requestList.count()):
			requester = SID.userList.find({"userName": requestList[x]['requester']})
			data['requests'].append({
				'userName': requester[0]['userName'],
				'firstName': requester[0]['firstName'],
				'lastName': requester[0]['lastName'],
				'profilePic': requester[0]['ProfilePic'],
				'languages': requester[0]['Languages'],
				'friends': requester[0]['friends']
				})
		return jsonify(data)

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

#Friends Data
#Get: obtains data for all friends to be displayed
#Implement Machine Learning Recommendation later
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
	userData = SID.userList.find({"userName": userName})[0]
	data = {}
	data['recommended'] = []
	data['friends'] = []
	similarData = SID.userList.find().limit(10)
	for x in range(similarData.count()):
		if similarData[x]['userName'] == userName:
			continue
		else:
			data['recommended'].append({
				'userName': similarData[x]['userName'],
				'firstName': similarData[x]['firstName'],
				'ProfilePic': similarData[x]['ProfilePic'],
				'languages': similarData[x]['Languages'],
				'friends': similarData[x]['friends']
				})
	for friend in userData['friends']:
		friendData = SID.userList.find({"userName": friend})[0]
		data['friends'].append({
			'userName': friendData['userName'],
			'ProfilePic': friendData['ProfilePic']
			})
	return jsonify(data)

#Competition
@app.route('/api/competition/<userName>')
def competition(userName):
	userData = SID.userList.find({"userName": userName})[0]
	friends = userData['friends']
	progressCount = {}
	for friend in friends:
		friendData = SID.userList.find({"userName": friend})[0]
		progressCount[friend] = friendData['weeklyProgress']
	statistics = {}
	statistics['winners'] = []
	x = 5
	while x > 0 and len(progressCount) > 0:
		toAdd = max(progressCount, key=(lambda key: progressCount[key]))
		toAddAmount = progressCount.pop(toAdd)
		statistics['winners'].append({
			'userName': toAdd,
			'amount': toAddAmount
			})
	return jsonify(statistics)

#update weekly progress of a user
def updateWeeklyProgress(userName, amount):
	userData = SID.userList.find({"userName": userName})[0]
	toUpdateID = userData['_id']
	weeklyProgress = userData['weeklyProgress']
	newWeeklyProgress = weeklyProgress + amount
	SID.userList.update_one({'_id': toUpdateID},{'$set': {'weeklyProgress': newWeeklyProgress}}, upsert=False)
	return 0

"""



if __name__ == '__main__':
	app.debug = True
	app.run(host='0.0.0.0', port=3000)



