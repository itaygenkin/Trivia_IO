import time
import socketio
import chatlib


### Globals ###
sio = socketio.Client()
sio.connect('http://127.0.0.1:8080')
is_connected = False


### Socket-IO Callbacks ###

@sio.on('login_callback')
def login_callback(data):
    global is_connected
    cmd, msg = chatlib.parse_message(data)
    print(msg)  # TODO: delete
    print(cmd)  # TODO: delete
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


@sio.on('score_callback')
def get_score_callback(data):
    cmd, score = chatlib.parse_message(data)
    print('Your score:', score)
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
    # TODO: implement
    pass


def get_score_handler():
    sio.emit(event='server_score')


def get_highscore_handler():
    # TODO: implement
    pass


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
    print('function not implemented yet')
    disconnect()
    exit()


if __name__ == '__main__':
    login_handler()
    if not is_connected:
        exit()
