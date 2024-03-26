import json
import signal
import sys
import threading
import time
from functools import reduce

import socketio
import chatlib
import helpers

###############
### GLOBALS ###
###############

is_connected = False
TIMEOUT = 18
PROTOCOL_TYPE = 'client'
USER_TYPE = '1'
sio = socketio.Client()
sio.connect('http://127.0.0.1:8080')
locker = threading.Event()


def signal_handler(sig, frame):
    """
    a handler to signals (INT, TERM) caught from user,
    disconnect from server, and do exit
    :param sig: the signal caught from user
    :param frame:
    """
    print('-^--^-')
    try:
        disconnect()
    finally:
        sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_input_and_validate(input_choices: list[str], menu_msg: str) -> str:
    """
    getting an input from user and validate that it's
    taken from {input_choices}.
    :param input_choices: a list of options which the input should be taken from
    :param menu_msg: a message to be shown for the user
    :return: the user's input
    """
    try:
        user_input = input(menu_msg)
        while user_input not in input_choices:
            print("Invalid choice")
            user_input = input(menu_msg)
        return user_input
    except EOFError or KeyboardInterrupt:
        pass
    except Exception as e:
        print('An exception occurred when trying to get an input from user.')
        print(e)
        disconnect()


###########################
### Socket-IO Callbacks ###
###########################

@sio.on('login_callback')
def login_callback(data: str) -> None:
    global is_connected
    data = json.loads(data)
    if data['result'] == 'ACK':
        is_connected = True
    else:
        print(data['msg'], 'Please try again.')
    locker.set()


@sio.on('play_question_callback')
def play_question_callback(data: str) -> None:
    question_data = json.loads(data)
    answer_pretty_print = reduce(lambda x, y: f'{x}\n{y[0]+ 1} - {y[1]}', enumerate(question_data['answers']), "")
    print(question_data['question'] + answer_pretty_print)

    user_ans = int(get_input_and_validate(['1', '2', '3', '4'], 'Your answer: '))
    send_answer_handler(question_data['qid'], question_data['answers'][user_ans-1])
    # locker.set()


@sio.on('answer_callback')
def get_answer_callback(data: str) -> None:
    data = json.loads(data)
    print(data['msg'])
    time.sleep(2)
    locker.set()


@sio.on('score_callback')
def get_score_callback(data: str) -> None:
    data = json.loads(data)
    print('Your score: ', data['msg'])
    time.sleep(3)
    locker.set()


@sio.on('highscore_callback')
def get_highscore_callback(data: str) -> None:
    data = json.loads(data)
    print(data['msg'])
    time.sleep(3)
    locker.set()


@sio.on('error_callback')
def error_callback(data: str) -> None:
    data = json.loads(data)
    print(data['result'])
    print(data['msg'])
    locker.set()


##########################
### Socket-IO Handlers ###
##########################

def disconnect() -> None:
    global is_connected
    try:
        sio.disconnect()
        print("Disconnected!")
        is_connected = False
    except Exception as e:
        print(e)


def login_handler() -> None:
    """
    get username and password from the user and login
    :return: None
    """
    username = input('Please enter username: ')
    password = input('Please enter password: ')
    fields = {'username': username, 'password': password, 'user_type': USER_TYPE}
    data = helpers.build_json_msg('login', PROTOCOL_TYPE, fields)
    print('Logging in...')
    sio.emit(event='login', data=data)


def logout_handler() -> None:
    try:
        sio.emit('logout_handler')
    finally:
        disconnect()
        exit()


def error_and_exit(error_msg: str) -> None:
    print(error_msg)
    try:
        disconnect()
    finally:
        exit()


def play_question_handler() -> None:
    sio.emit(event='play_question')


def send_answer_handler(qid: str, ans: str) -> None:
    """
    called after a question is shown to a user,
    sending back question id number and the user's answer
    :param qid: a question id number represented as a string
    :param ans: the user's answer
    """
    fields = {'question_id': qid, 'answer': ans}
    data = helpers.build_json_msg('ans', PROTOCOL_TYPE, fields)
    sio.emit(event='answer', data=data)


def get_score_handler() -> None:
    sio.emit(event='server_score')


def get_highscore_handler() -> None:
    sio.emit(event='server_highscore')


def get_logged_in_handler() -> None:
    sio.emit(event='logged_in_users')


######################
### Client Process ###
######################


def player_menu(cmd=None):
    """
    a menu for regular player
    :param cmd: for optional use case later (not used right now)
    """
    player_menu_msg = """
1 - Play a question
2 - Get score
3 - Get highscore
4 - Log out\n"""
    command = get_input_and_validate(['1', '2', '3', '4'], player_menu_msg)
    match command:
        case '1':
            play_question_handler()
        case '2':
            get_score_handler()
        case '3':
            get_highscore_handler()
        case '4':
            logout_handler()
            return True
        case _:
            return


def main() -> None:
    global is_connected

    # step 1: log in
    while not is_connected:
        login_handler()
        time.sleep(0.1)
        locker.wait()
        locker.clear()

    # step 2: main menu
    while True:
        if player_menu():
            break
        time.sleep(0.1)
        locker.wait()
        locker.clear()


if __name__ == '__main__':
    main()

