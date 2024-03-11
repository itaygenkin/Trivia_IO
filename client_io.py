import signal
import sys
import threading
import time
import socketio
import chatlib


###############
### GLOBALS ###
###############

sio = socketio.Client()
sio.connect('http://127.0.0.1:8080')
locker = threading.Event()
is_connected = False
TIMEOUT = 18


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
def login_callback(data) -> None:
    global is_connected
    cmd, msg = chatlib.parse_message(data)
    if cmd == 'ERROR':
        print('Login failed:', msg)
    else:
        is_connected = True
    locker.set()


@sio.on('play_question_callback')
def play_question_callback(data) -> None:
    cmd, question_data = chatlib.parse_message(data)
    print(question_data)  # TODO: check expected fields
    q_data = chatlib.split_data(question_data, 6)

    question_pretty_print = [f'\n{x-1} - {q_data[x]}' for x in range(1, len(q_data))]
    print(''.join(question_pretty_print)[5:])
    user_ans = int(get_input_and_validate(['1', '2', '3', '4'], 'Your answer: '))

    send_answer_handler(q_data[0], q_data[user_ans+1])
    locker.set()


@sio.on('answer_callback')
def get_answer_callback(data) -> None:
    cmd, data = chatlib.parse_message(data)
    print(cmd, data)
    time.sleep(2.5)
    locker.set()


@sio.on('score_callback')
def get_score_callback(data) -> None:
    cmd, score = chatlib.parse_message(data)
    print('Your score:', score)
    time.sleep(3)
    locker.set()


@sio.on('highscore_callback')
def get_highscore_callback(data) -> None:
    cmd, highscore = chatlib.parse_message(data)
    print(highscore)
    time.sleep(3)
    locker.set()


@sio.on('error_callback')
def error_callback(data: str) -> None:
    cmd, msg = chatlib.parse_message(data)
    print(cmd)
    print(msg)
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
    user_mode = '1'
    data = [username, password, user_mode]
    print('Logging in...')
    sio.emit(event='login', data='#'.join(data))


def logout_handler() -> None:
    try:
        sio.emit('logout_handler', data='')
    finally:
        disconnect()
        exit()


def error_and_exit(error_msg) -> None:
    print(error_msg)
    try:
        disconnect()
    finally:
        exit()


def play_question_handler() -> None:
    sio.emit(event='play_question')


def send_answer_handler(qid, ans) -> None:
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_CLIENT['send_ans'], qid + '#' + ans)
    sio.emit(event='answer', data=data_to_send)


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

