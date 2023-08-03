import string

# Protocol Constants

CMD_FIELD_LENGTH = 16  # Exact length of cmd field (in bytes)
LENGTH_FIELD_LENGTH = 4   # Exact length of length field (in bytes)
MAX_DATA_LENGTH = 10 ** LENGTH_FIELD_LENGTH - 1  # Max size of data field according to protocol
MSG_HEADER_LENGTH = CMD_FIELD_LENGTH + 1 + LENGTH_FIELD_LENGTH + 1  # Exact size of header (CMD+LENGTH fields)

# Protocol Messages 
# In this dictionary we will have all the client and server command names

PROTOCOL_CLIENT = {
	"login_msg": "LOGIN",
	"logout_msg": "LOGOUT",
	"logged_msg": "LOGGED",
	"get_ques": "GET_QUESTION",
	"send_ans": "SEND_ANSWER",
	"score": "MY_SCORE",
	"high": "HIGHSCORE",
	"add": "ADD_QUESTION",
	"logged_in": "LOGGED_IN_USERS"
}

SEMI_PROTOCOL_CLIENT = {
	'1': "GET_QUESTION",
	'2': "MY_SCORE",
	'3': "HIGHSCORE",
	'4': "LOGGED",
	'5': "LOGOUT"
}

PROTOCOL_SERVER = {
	"login_ok_msg": "LOGIN_OK",
	"login_failed_msg": "ERROR",
	"logged_msg": "LOGGED_ANSWER",
	"question": "YOUR_QUESTION",
	"correct": "CORRECT_ANSWER",
	"wrong": "WRONG_ANSWER",
	"score": "YOUR_SCORE",
	"all_score": "ALL_SCORE",
	"error": "ERROR",
	"no_ques": "NO_QUESTION",
	"add_succ": "ADD_QUESTION_SUCCESSFULLY"
}


def build_message(cmd, data):
	"""
	Gets command name (str) and data field (str) and creates a valid protocol message
	Returns: str, or None if error occurred
	"""
	if (cmd not in PROTOCOL_CLIENT.values() and cmd not in PROTOCOL_SERVER.values()) or (len(data) > MAX_DATA_LENGTH):
		return None
	full_msg = cmd
	while len(full_msg) < 16:  # padding part one of the message
		full_msg += ' '
	n = str(len(data))
	while len(n) < 4:  # padding part two of the message
		n = '0' + n
	return full_msg + '|' + n + '|' + data


def parse_message(data):
	"""
	Parses protocol message and returns command name and data field
	Returns: cmd (str), data (str). If some error occured, returns None, None
	"""
	try:
		lst = data.split('|')
		if len(lst) != 3:
			raise IndexError
	except IndexError:
		return None, None
	cmd = lst[0].strip()
	num = lst[1]
	msg = lst[2]
	if (cmd not in PROTOCOL_CLIENT.values() and cmd not in PROTOCOL_SERVER.values()) or not is_number(num) or len(msg) != int(num):
		return None, None
	# The function should return 2 values
	return cmd, msg


def is_number(num):
	"""
	Check whether num is a 4-digit-number (or padded by 0 to 4 digits)
	:param num: str
	:rtype: boolean
	"""
	if len(num) != 4 or num == '    ':
		return False
	for i in num:
		if i not in string.digits and i != ' ':
			return False
	return True


def split_data(msg, expected_fields):
	"""
	Helper method. gets a string and number of expected fields in it. Splits the string
	using protocol's data field delimiter (|#) and validates that there are correct number of fields.
	Returns: list of fields if all ok. If some error occurred, returns None
	"""
	if '|' in msg:
		list_of_fields = msg.split('|')
		if len(list_of_fields) == expected_fields + 1:
			return list_of_fields
	elif '#' in msg:
		list_of_fields = msg.split('#')
		if len(list_of_fields) == expected_fields + 1:
			return list_of_fields
	return None


def join_data(msg_fields):
	"""
	Helper method. Gets a list, joins all of its fields to one string divided by the data delimiter.
	Returns: string that looks like cell1#cell2#cell3
	"""
	msg = ""
	for x in msg_fields:
		msg += str(x) + '#'
	return msg[:-1]


def parse_notation(sentence):
	sentence = sentence.replace('&#039;', "\'")
	sentence = sentence.replace('&#034;', '\"')
	sentence = sentence.replace('&quot;', '\"')
	return sentence


def convert_user_mode(mode):
	if mode == '2':
		return True
	elif mode == '1':
		return False
	return None
