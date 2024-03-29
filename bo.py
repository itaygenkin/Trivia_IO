import json
import signal
import threading

import socketio
import chatlib
import time
import sys

import helpers

###############
### GLOBALS ###
###############

sio = socketio.Client()
sio.connect('http://127.0.0.1:8080')
locker = threading.Event()
is_connected = False
TIMEOUT = 8
PROTOCOL_TYPE = 'manager'
USER_TYPE = '2'


def signal_handler(sig, frame):
    """
    a handler to signals (INT, TERM) caught from user,
    disconnect from server, and do exit
    :param sig: the signal caught from user
    """
    print('--^-YY-^--')
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
    :param menu_msg: a message to be shown for the manager
    :return: the manager's input
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


@sio.on('add_question_callback')
def add_question_callback(data: str) -> None:
    data = json.loads(data)
    print(data['result'])
    locker.set()


@sio.on('get_logged_in_callback')
def get_logged_in_users_callback(data: str) -> None:
    data = json.loads(data)
    print(data['msg'])
    locker.set()


@sio.on('register_player_callback')
def register_player_callback(data: str) -> None:
    data = json.loads(data)
    print(data['msg'])
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
    get m_name and password from the manager and login
    :return: None
    """
    print("Hey Manager,")
    username = input('Please enter your name: ')
    password = input('Please enter password: ')
    fields = {'username': username, 'password': password, 'user_type': USER_TYPE}
    data_to_send = helpers.build_json_msg('login', 'manager', fields)
    print('Logging in...')
    sio.emit(event='login', data=data_to_send)


def logout_handler() -> None:
    try:
        sio.emit('logout_handler', data='')
    finally:
        disconnect()
        exit()


def error_and_exit(error_msg: str) -> None:
    print(error_msg)
    try:
        disconnect()
    finally:
        exit()


def add_question_handler() -> None:
    question = input('Write the question: ')
    if not question.endswith('?'):
        question += '?'

    answers = [input(f'Write answer number {i}: ') for i in range(1, 5)]
    correct_answer_msg = 'Write the correct answer number: '
    correct_answer_num = int(get_input_and_validate(['1', '2', '3', '4'], correct_answer_msg)) - 1

    fields = {'question': question, 'correct_answer': answers[correct_answer_num], 'answers': answers}
    data_to_send = helpers.build_json_msg('add', PROTOCOL_TYPE, fields)

    sio.emit(event='server_add_question', data=data_to_send)


def get_logged_in_handler() -> None:
    sio.emit(event='logged_in_users')


def register_player_handler() -> None:
    username = input('Enter username: ')
    password = input('Enter password: ')
    fields = {'username': username, 'password': password}
    new_player_data = helpers.build_json_msg('register', PROTOCOL_TYPE, fields)
    sio.emit(event='register_player', data=new_player_data)


def manager_menu(cmd=None) -> bool | None:
    """
    a menu for manager
    :param cmd: for optional use case later (not used right now)
    """
    creator_menu_msg = """
1 - Add question
2 - Get logged in users
3 - Register new player
4 - Log out\n"""
    command = get_input_and_validate(['1', '2', '3', '4'], creator_menu_msg)
    match command:
        case '1':
            add_question_handler()
        case '2':
            get_logged_in_handler()
        case '3':
            register_player_handler()
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
        if manager_menu():
            break
        time.sleep(0.1)
        locker.wait()
        locker.clear()


if __name__ == '__main__':
    main()

