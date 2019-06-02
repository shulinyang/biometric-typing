#'########::'##::::'##::::'###::::'########:::   '########:'########::::'###::::'########:'##::::'##:'########::'########:
# ##.... ##: ##:::: ##:::'## ##:::... ##..::::    ##.....:: ##.....::::'## ##:::... ##..:: ##:::: ##: ##.... ##: ##.....::
# ##:::: ##: ##:::: ##::'##:. ##::::: ##::::::    ##::::::: ##::::::::'##:. ##::::: ##:::: ##:::: ##: ##:::: ##: ##:::::::
# ########:: #########:'##:::. ##:::: ##::::::    ######::: ######:::'##:::. ##:::: ##:::: ##:::: ##: ########:: ######:::
# ##.....::: ##.... ##: #########:::: ##::::::    ##...:::: ##...:::: #########:::: ##:::: ##:::: ##: ##.. ##::: ##...::::
# ##:::::::: ##:::: ##: ##.... ##:::: ##::::::    ##::::::: ##::::::: ##.... ##:::: ##:::: ##:::: ##: ##::. ##:: ##:::::::
# ##:::::::: ##:::: ##: ##:::: ##:::: ##::::::    ##::::::: ########: ##:::: ##:::: ##::::. #######:: ##:::. ##: ########:
#..:::::::::..:::::..::..:::::..:::::..:::::::.   .::::::::........::..:::::..:::::..::::::.......:::..:::::..::........::
#
#      '########:'##::::'##:'########:'########:::::'###:::::'######::'########::'#######::'########::
#       ##.....::. ##::'##::... ##..:: ##.... ##:::'## ##:::'##... ##:... ##..::'##.... ##: ##.... ##:
#       ##::::::::. ##'##:::::: ##:::: ##:::: ##::'##:. ##:: ##:::..::::: ##:::: ##:::: ##: ##:::: ##:
#       ######:::::. ###::::::: ##:::: ########::'##:::. ##: ##:::::::::: ##:::: ##:::: ##: ########::
#       ##...:::::: ## ##:::::: ##:::: ##.. ##::: #########: ##:::::::::: ##:::: ##:::: ##: ##.. ##:::
#       ##:::::::: ##:. ##::::: ##:::: ##::. ##:: ##.... ##: ##::: ##:::: ##:::: ##:::: ##: ##::. ##::
#       ########: ##:::. ##:::: ##:::: ##:::. ##: ##:::: ##:. ######::::: ##::::. #######:: ##:::. ##:
#........::..:::::..:::::..:::::..:::::..::..:::::..:::......::::::..::::::.......:::..:::::..::

import re
import csv
from collections import defaultdict
import userInterface

# globally stores the titles of each data entry from csv
labels = []

# returns list of all features dicts drawn from the csv
def getCSVFeatures():
	allFeatures = []
	with open('data/password-data.csv') as file:
		data = csv.reader(file, delimiter = ',')
		for row in data:
			# at header: populate labels
			if row[0] == 'subject':
				labels = row
			else:
				keyList = getListFromCSVEntry(row, labels)
				features = getFeaturesFromList(keyList)
				allFeatures.append(features)
	return allFeatures

# given list of attempts, return list of features normalized by phi
def getNormalizedFeatureSet(attemptList, phi):
	normalized = []
	for attempt in attemptList:
		normalizedAttempt = {}
		for feature in attempt:
			keystroke = (feature[0], feature[1], feature[2])
			difference = abs(attempt[feature] - phi[keystroke])
			normalizedAttempt[feature] = difference
			if feature[1] != None:
				normalizedAttempt[(feature[0], feature[1], feature[2], 'squared')] = difference**2
		normalized.append(normalizedAttempt)
	return normalized

# attemptList is a list of defaultdict(int)s, each representing one password
# attempt for a given user
# @return phi: a dict from keystroke tuples to average times
def getPhiFromAttemptList(attemptList):
	# generate list of (prevKey, currKey, event) keystroke tuples, agnostic to time values
	phi = {}
	for f in attemptList[0]:
		keystroke = (f[0], f[1], f[2])
		phi[keystroke] = 0.0
	# populate phi with total times for all attempts
	for attempt in attemptList:
		for f in attempt:
			keystroke = (f[0], f[1], f[2])
			phi[keystroke] += attempt[f]
	# normalize phi to get average times
	for k in phi:
		phi[k] /= float(len(attemptList))

	return phi

# given list of (keystroke, UP/DOWN, time) events, generate features for password attempt
# each feature represented by (pastKey, currKey, event) tuple
def getFeaturesFromList(keyList):
	features = defaultdict(int)
	# add 1-feature
	features[(None, None, None)] = 1

	prevKey = None
	prevDownTime, prevUpTime = 0.0, 0.0
	while keyList != []:
		# take 0-th index entry
		downEvent = keyList[0]
		key, event, time = downEvent
		# if key down event:
		if event == "DOWN":
			# search for corresponding key up event w/ matching keystroke
			upEvent = (None, None, None)
			index = 0
			while upEvent[0] != key or upEvent[1] != 'UP':
				# temp fix for index out of range bug
				if index > len(keyList): break
				upEvent = keyList[index]
				index += 1
			# compute H, UD, DD times
			holdTime = upEvent[2] - downEvent[2]
			upDownTime = downEvent[2] - prevUpTime
			downDownTime = downEvent[2] - prevDownTime
			# add features based on previous keystroke and previous times
			features[(None, key, 'H', 'linear')] = max(holdTime, 0)
			# features[(None, key, 'H', 'squared')] = holdTime**2
			features[(prevKey, key, 'UD', 'linear')] = max(upDownTime, 0)
			# features[(prevKey, key, 'UD', 'squared')] = upDownTime**2
			features[(prevKey, key, 'DD', 'linear')] = max(downDownTime, 0)
			# features[(prevKey, key, 'DD', 'squared')] = downDownTime**2
			# update latest key up and key down times, and prev key
			prevDownTime = downEvent[2]
			prevUpTime = upEvent[2]
			prevKey = key
			# remove both key up and key down event from list
			keyList.remove(downEvent)
			keyList.remove(upEvent)
	return features

# returns a list of (keyChar, pressed/released, timeIndex) tuples
def getListFromCSVEntry(row, labels):
	# list to fill with data
	attempt = []
	time = 0.0
	for index in range(3, len(labels)): # 3-offset avoids metadata at beginning
		label = labels[index]
		labelList = label.split(".")
		# time between key press & release held in Hold
		if labelList[0] == "H":
			currKey = labelList[1]
			if currKey == "Return": continue
			# special case for shift key
			if labelList[1] == "Shift":
				currKey = "R"
			# special cases for 'period' and 'five'
			if currKey == "period":
				currKey = "."
			if currKey == "five":
				currKey = "5"
			keyPress = (currKey, "DOWN", time)
			holdTime = float(row[index])
			keyRelease = (currKey, "UP", time+holdTime)
			attempt.append(keyPress)
			attempt.append(keyRelease)
		# time between key-presses held in Down-Down
		elif labelList[0] == "DD":
			time += float(row[index])
	return attempt

################################################################################
# @function: userFeatureSetsFromInterface
# calls userInterface to request password attempts from user
# 
# @return normalizedFeatures: a list of features, normalized by
# 	their distance from the average time
# @return phi: a vector representing the average times for each keystroke event
# 	for a user
################################################################################
def userFeatureSetsFromInterface():
	userData = userInterface.welcomeUserAndCollectUserPasswordData(2, 0)
	features = []
	for datum in userData:
		features.append(getFeaturesFromList(datum))
	phi = getPhiFromAttemptList(features)
	normalizedFeatures = getNormalizedFeatureSet(features, phi)
	return normalizedFeatures, phi

################################################################################
# @function: generateAllFeatureSets
# generates all normalized features for a user and for CSV entries
# 
# @return userFeatureSets: a list of dict() objects representing the features
# 	for password attempts from the genuine user
# @return CSVFeatureSets: a list of dict() objects representing the features
# 	for password attempts from imposters, generated from the CSV
################################################################################
def generateAllFeatureSets():
	# get user data
	userFeatureSets, phi = userFeatureSetsFromInterface()
	# get data from csv
	CSVFeatures = getCSVFeatures()
	CSVFeatureSets = getNormalizedFeatureSet(CSVFeatures, phi)
	return userFeatureSets, CSVFeatureSets
