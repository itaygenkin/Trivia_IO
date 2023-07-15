import asyncio
import logging
import signal
import sys
import atexit
import time
import socketio
import chatlib


###############
### GLOBALS ###
###############

sio = socketio.AsyncClient(logger=True)
# await sio.connect('http://127.0.0.1:8080')
is_connected = False
lock = asyncio.Condition()
# lock = threading.Lock()
TIMEOUT = 6
user_mode = None


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
        cleanup()
    finally:
        sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@atexit.register
async def cleanup():
    # TODO: implement the function so that the client will gracefully exit
    await asyncio.get_event_loop().shutdown_asyncgens()


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
async def login_callback(data) -> None:
    global is_connected
    cmd, msg = chatlib.parse_message(data)
    if cmd == 'ERROR':
        print('Login failed: ', msg)
        next_operation = get_input_and_validate(['e', 'l'], 'e - exit\nl - log in\n')
        if next_operation == 'e':
            error_and_exit('quiting...')
        elif next_operation == 'l':
            await login_handler()
    else:
        is_connected = True
        lock.release()
        print("Lock releases in the callback")


@sio.on('play_question_callback')
async def play_question_callback(data: str) -> None:
    try:
        cmd, question_data = chatlib.parse_message(data)
        q_data = chatlib.split_data(question_data, 5)

        question_pretty_print = [f'\n{x-1} - {q_data[x]}' for x in range(1, len(q_data))]
        print(''.join(question_pretty_print)[5:])
        user_ans = int(get_input_and_validate(['1', '2', '3', '4'], 'Your answer: '))

        send_answer_handler(q_data[0], q_data[user_ans+1])
    except Exception as e:
        logging.info(msg=f'Catched an error while trying to play question\n>> {e}')
        print('An error occurred')
        time.sleep(1.5)
        menu()


@sio.on('answer_callback')
def get_answer_callback(data: str) -> None:
    cmd, data = chatlib.parse_message(data)
    print(cmd, data)
    time.sleep(2)  # TODO: async/await
    player_game_menu(cmd)


@sio.on('score_callback')
def get_score_callback(data: str) -> None:
    cmd, score = chatlib.parse_message(data)
    print('Your score:', score)
    time.sleep(3)  # TODO: async/await
    player_game_menu(cmd)


@sio.on('highscore_callback')
def get_highscore_callback(data: str) -> None:
    cmd, highscore = chatlib.parse_message(data)
    print(highscore)
    time.sleep(3)  # TODO: async/await
    menu(cmd)
    return


@sio.on('add_question_callback')
def add_question_callback(data: str) -> None:
    cmd, msg = chatlib.parse_message(data)
    print(cmd)
    creator_menu(cmd)
    return


@sio.on('error')
def error_callback(data: str):
    # TODO: check if necessary and implement if so
    pass


##########################
### Socket-IO Handlers ###
##########################

def disconnect():
    global is_connected
    try:
        sio.disconnect()
        print("Disconnected!")
        is_connected = False
        exit()
    except Exception as e:
        print(e)
    finally:
        return


async def login_handler() -> None:
    """
    get username and password from the user and login
    :return: None
    """
    global user_mode
    username = input('Please enter username: ')
    password = input('Please enter password: ')
    user_mode_msg = 'Choose Player(1) or Creator(2): '
    user_mode = get_input_and_validate(['1', '2'], user_mode_msg)
    data = [username, password, user_mode]
    print('Logging in...')
    await sio.emit(event='login', data='#'.join(data))
    await lock.acquire()
    print("Lock acquired in login_handler")


def logout_handler():
    try:
        sio.emit('logout_handler', data='')
    finally:
        disconnect()
        exit()


def error_and_exit(error_msg: str):
    print(error_msg)
    try:
        disconnect()
    finally:
        exit()


def play_question_handler() -> None:
    sio.emit(event='play_question')


def send_answer_handler(qid: str, ans: str) -> None:
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_CLIENT['send_ans'], qid + '#' + ans)
    sio.emit(event='answer', data=data_to_send)


def get_score_handler() -> None:
    sio.emit(event='server_score')


def get_highscore_handler() -> None:
    sio.emit(event='server_highscore')


def add_question_handler() -> None:
    question = input('Write the question: ')
    if not question.endswith('?'):
        question += '?'
    answers = [input(f'Write answer number {i}: ') for i in range(1, 5)]
    correct_answer = input('Write the correct answer: ')
    question_data = [question, *answers, correct_answer]
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_CLIENT['add'], '#'.join(question_data))
    sio.emit(event='server_add_question', data=data_to_send)


######################
### Client Process ###
######################

def menu(cmd: str = None) -> None:
    """
    a small menu pipe to call the relevant menu
    :param cmd: a command to be sent for the next menu
    """
    if user_mode == '1':
        player_game_menu(cmd)
    elif user_mode == '2':
        creator_menu(cmd)
    return


def player_game_menu(cmd: str = None) -> None:
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
            return
        case _:
            return
    return


async def creator_menu(cmd: str = None) -> None:
    """
    a menu for creator
    :param cmd: for optional use case later (not used right now)
    """
    creator_menu_msg = """
1 - Add question
2 - Get highscore
3 - Logged users
4 - Log out\n"""
    command = get_input_and_validate(['1', '2', '3'], creator_menu_msg)
    match command:
        case '1':
            add_question_handler()
        case '2':
            get_highscore_handler()
        case '3':
            # TODO: write a function that gets the logged in users
            pass
        case '4':
            logout_handler()
            return
        case _:
            return
    return


async def start():
    try:
        await sio.connect('http://127.0.0.1:8080')
        asyncio.create_task(login_handler())
        print('waiting...')
        await asyncio.wait_for(lock.acquire(), timeout=TIMEOUT)
        print('released')
    except asyncio.TimeoutError:
        print("Timed out waiting for the lock")
    else:
        menu()


if __name__ == '__main__':
    print("WELCOME")
    asyncio.run(start())
    print(299)

    # after TIMEOUT is done and nothing happened, the program gracefully exit
    time.sleep(TIMEOUT)
    if not is_connected:
        print('Shut down')
        exit(1)
