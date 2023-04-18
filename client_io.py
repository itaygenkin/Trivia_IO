import time
import socketio
import chatlib


### Globals ###
sio = socketio.Client()
sio.connect('http://127.0.0.1:8080')
is_connected = False
TIMEOUT = 6


### Socket-IO Callbacks ###

@sio.on('login_callback')
def login_callback(data):
    global is_connected
    cmd, msg = chatlib.parse_message(data)
    if cmd == 'ERROR':
        print('Login failed: ', msg)
        next_operation = chatlib.get_input_and_validate(['e', 'l'], 'e - exit\nl - log in\n')
        if next_operation == 'e':
            error_and_exit('quiting...')
        elif next_operation == 'l':
            login_handler()
    else:
        is_connected = True
        player_game_menu(cmd)


@sio.on('play_question_callback')
def play_question_callback(data):
    cmd, question_data = chatlib.parse_message(data)
    q_data = chatlib.split_data(question_data, 5)

    question_pretty_print = [f'\n{x-1} - {q_data[x]}' for x in range(1, len(q_data))]
    print(''.join(question_pretty_print)[5:])
    user_ans = int(chatlib.get_input_and_validate(['1', '2', '3', '4'], 'Your answer: '))

    send_answer_handler(q_data[0], q_data[user_ans+1])


@sio.on('answer_callback')
def get_answer_callback(data):
    cmd, data = chatlib.parse_message(data)
    print(cmd, data)
    time.sleep(2)
    player_game_menu(cmd)


@sio.on('score_callback')
def get_score_callback(data):
    cmd, score = chatlib.parse_message(data)
    print('Your score:', score)
    time.sleep(3)
    player_game_menu(cmd)


@sio.on('highscore_callback')
def get_highscore_callback(data):
    cmd, highscore = chatlib.parse_message(data)
    print(highscore)
    time.sleep(3)
    player_game_menu(cmd)


@sio.on('error')
def error_callback(data):
    # TODO: check if necessary and implement if so
    pass


### Socket-IO Handlers ###

def disconnect():
    global is_connected
    try:
        sio.disconnect()
        print("Disconnected!")
        is_connected = False
        exit()
    except Exception as e:
        print(e)


def login_handler():
    """
    get username and password from the user and login
    :return: None
    """
    username = input('Please enter username: ')
    password = input('Please enter password: ')
    user_mode_msg = 'Choose Player(1) or Creator(2): '
    user_mode = chatlib.get_input_and_validate(['1', '2'], user_mode_msg)
    data = [username, password, user_mode]
    print('Logging in...')
    sio.emit(event='login', data='#'.join(data))


def logout_handler():
    try:
        sio.emit('logout_handler', data='')
    finally:
        disconnect()
        exit()


def error_and_exit(error_msg):
    print(error_msg)
    try:
        disconnect()
    finally:
        exit()


def play_question_handler():
    sio.emit(event='play_question')


def send_answer_handler(qid, ans):
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_CLIENT['send_ans'], qid + '#' + ans)
    sio.emit(event='answer', data=data_to_send)


def get_score_handler():
    sio.emit(event='server_score')


def get_highscore_handler():
    sio.emit(event='server_highscore')


def add_question_handler():
    # TODO: implement
    pass


def update_question_bank():
    # TODO: implement
    pass


### Client Process ###

def player_game_menu(cmd=None):
    player_menu_msg = """
1 - Play a question
2 - Get score
3 - Get highscore
4 - Log out\n"""
    command = chatlib.get_input_and_validate(['1', '2', '3', '4'], player_menu_msg)
    match command:
        case '1':
            play_question_handler()
        case '2':
            get_score_handler()
        case '3':
            get_highscore_handler()
        case '4':
            logout_handler()
            return
        case _:
            return


def creator_menu():
    # TODO: implement
    print('function hasn\'t implemented yet')
    disconnect()
    exit()


if __name__ == '__main__':
    login_handler()
    time.sleep(TIMEOUT)
    if not is_connected:
        print('Shut down')
        exit()
