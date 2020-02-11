class polyglot:
	def __init__(self, userName, firstName, lastName, profilePic = None, languages = [], friends = []):
		self.userName = userName
		self.firstName = firstName
		self.lastName = lastName
		self.profilePic = profilePic
		self.languages = languages
		self.friends = friends

	def to_dict(obj):
		output ={}
		for key, item in obj.__dict__.items():
			if isinstance(item, list):
				l = []
				for item in item:
					d = to_dict(item)
					l.append(d)
					output[key] = l
				else:
					output[key] = item
		return output