
class feed_element:
	def __init__(self, username, text, likes, dislikes, language, likers):
		self.username = username
		self.text = text
		self.likes = likes
		self.dislikes = dislikes
		self.language = language
		self.likers = likers
	def addLike(self):
		self.likes = self.likes + 1
	def subtractLike(self):
		self.likes = self.likes - 1
	def addDislike(self):
		self.dislikes = self.dislikes + 1
	def subtractDislike(self):
		self.dislikes = self.dislikes - 1

#def addFeed(collection, text, userName = 'anonymous', idNum = 0,likes = 0, dislikes = 0):
	#toAdd = feedElement(text, userName, idNum, likes, dislikes)
	#encodedPost = bson.BSON.encode(toAdd.__dict__)
	#collection.insert_one({'userName': userName, 'post': encodedPost})
	#toUpdate = collection.find_one({'userName': userName, 'post': encodedPost})
