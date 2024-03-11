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
	"logged_in": "LOGGED_IN_USERS",
	"register": "REGISTER_PLAYER"
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
	"add_succ": "ADD_QUESTION_SUCCESSFULLY",
	"reg_succ": "REGISTER_SUCCESSFULLY",
	"reg_fail": "REGISTER_FAILED"
}

PROTOCOL_USER_MODE = {'1': False, '2': True}  # 1 is user (NOT manager) - False, 2 is manager - True


def in_protocol(cmd: str) -> bool:
	return cmd in PROTOCOL_CLIENT or cmd in PROTOCOL_SERVER


def build_message(cmd: str, data: str) -> str | None:
	"""
	Gets command name and data field and creates a valid protocol message
	Returns: str, or None if error occurred
	"""
	if in_protocol(cmd):
		return None
	if len(data) > MAX_DATA_LENGTH:
		return None
	full_msg = cmd.ljust(CMD_FIELD_LENGTH, ' ')
	n = str(len(data)).rjust(LENGTH_FIELD_LENGTH, '0')
	return full_msg + '|' + n + '|' + data


def parse_message(data: str) -> tuple[str, str] | tuple[None, None]:
	"""
	Parses protocol message and returns command name and data field
	Returns: cmd (str), data (str). If some error occurred, returns None, None
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
	if in_protocol(cmd) or not is_number(num) or len(msg) != int(num):
		return None, None
	return cmd, msg


def is_number(num):
	"""
	Check whether num is a 4-digit-number (or padded by 0 to 4 digits)
	:param num: str
	:rtype: bool
	"""
	if len(num) != 4 or num == '    ':
		return False
	for i in num:
		if i not in string.digits and i != ' ':
			return False
	return True


def split_data(msg: str, expected_fields: int) -> list[str] | None:
	"""
	Helper method. gets a string and number of expected fields in it. Splits the string
	using protocol's data field delimiter (|#) and validates that there are correct number of fields.
	Returns: list of fields if all ok. If some error occurred, returns None
	"""
	if '|' in msg:
		list_of_fields = msg.split('|')
		if len(list_of_fields) == expected_fields:
			return list_of_fields
	elif '#' in msg:
		list_of_fields = msg.split('#')
		if len(list_of_fields) == expected_fields:
			return list_of_fields
	return None


def parse_notation(sentence: str) -> str:
	sentence = sentence.replace('&#039;', "\'")
	sentence = sentence.replace('&#034;', '\"')
	sentence = sentence.replace('&quot;', '\"')
	return sentence

