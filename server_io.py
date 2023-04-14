import time

import socketio
import eventlet
import requests
import chatlib
import random
import pandas as pd


### GLOBALS ###
questions_bank = pd.DataFrame({'question': ['Which Basketball team has completed two threepeats?'],
                               'answers': [['Chicago Bulls', 'LA Lakers', 'Golden state Warriors', 'Boston Celtics']],
                               'correct_answer': ['Chicago Bulls'],
                               'id': 1})
players = pd.DataFrame({'username': ['itay', 'oscar', 'test'],
                        'password': ['a123', 'oscar', 'test'],
                        'score': [0, 10, 0],
                        'is_creator': [False, True, False],
                        'id': [0, 1, 2]})
logged_players = {}  # dict of pairs : {sid: (username, is_creator)}
host = '127.0.0.1'
port = 8080

### DATA LOADERS ###


def gather_answers(correct_answer, incorrect_answers):
    answers = []
    correct_question_index = random.randint(1, 4)
    for i in range(1, 5):
        if i == correct_question_index:
            answers.append(correct_answer)
        else:
            answers.append(incorrect_answers.pop(0))
    return answers


def update_questions_bank_from_web():  
    global questions_bank
    response = requests.get(url="https://opentdb.com/api.php?amount=50&type=multiple")
    payload = response.json()['results']
    for q in payload:
        question = chatlib.parse_notation(q['question'])
        if question in questions_bank['question'].values:
            continue
        correct_answer = q['correct_answer']
        incorrect_answers = q['incorrect_answers']
        # create a list of all answers
        answers = gather_answers(correct_answer, incorrect_answers)
        question_to_add = pd.DataFrame({'question': question, 'answers': [answers], 'correct_answer': correct_answer})
        # add the question to the questions bank
        questions_bank = questions_bank._append(question_to_add, ignore_index=True)


def update_questions_bank_from_json():
    global questions_bank
    # TODO: implement
    pass


### SOCKET METHODS ###

sio = socketio.Server()
app = socketio.WSGIApp(sio, static_files={'/': './content/'})


@sio.event
def connect(sid, environ):
    print(sid, 'connected...')


@sio.event
def disconnect(sid):
    global logged_players
    sio.disconnect(sid=sid)
    if sid in logged_players.keys():
        logged_players.pop(sid)
    print(sid, 'disconnected...')


# TODO: implement
def send_error(sid, error_msg):
    """
    sends an error with a message
    :param sid: the session id of the client to be sent to
    :param error_msg: an error message to be sent
    :type error_msg: str
    """
    print('error:', error_msg)
    sio.emit(event='error', data=error_msg, to=sid)


@sio.event
def client_msg_handler(sid, data):
    # TODO: complete
    pass


### Handlers ###

@sio.on('login')
def login_handler(sid, data):
    global players, logged_players
    msg_back = ""
    try:
        [user, password, mode] = chatlib.split_data(data, 2)
        user_mode = chatlib.convert_user_mode(mode)

        # check username and password correctness
        if user not in players['username'].values or \
                players.loc[players['username'] == user]['password'].values[0] != password:
            err_msg = "Incorrect username or password"
            msg_back = chatlib.build_message(chatlib.PROTOCOL_SERVER['login_failed_msg'], err_msg)

        # check if user has already logged in
        elif user in players.iloc[list(logged_players.values())]['username'].values:
            err_msg = f'{user} has already logged in'
            msg_back = chatlib.build_message(chatlib.PROTOCOL_SERVER['login_failed_msg'], err_msg)

        # check if user tried to log in without the right permission
        elif user_mode and not players.loc[(players['username'] == user) &
                                           (players['password'] == password)]['is_creator'].values[0]:
            err_msg = f"{user} is not permitted to log in as a creator"
            msg_back = chatlib.build_message(chatlib.PROTOCOL_SERVER['login_failed_msg'], err_msg)

        # the user has successfully logged in
        else:
            logged_players[sid] = players.loc[(players['username'] == user)
                                              & (players['password'] == password)].index[0]
            print(f'User \'{user}\' successfully logged in')
            msg_back = chatlib.build_message(chatlib.PROTOCOL_SERVER['login_ok_msg'], 'Successfully logged in')

    except AttributeError as e:
        msg_back = 'Failed to log in. Try again.'
        send_error(sid, "Incorrect username or password")
    except Exception as e:
        msg_back = 'Failed to log in. Try again.'
        print(f'Something wrong happened when a user tried to log in.\nsid: {sid}')
        print(e)
    finally:
        sio.emit(event='login_callback', to=sid, data=msg_back)


@sio.on('logout')
def logout_handler(sid):
    global logged_players
    sio.disconnect(sid)


def play_question_handler(sid):
    # TODO: implement
    pass


def answer_handler(sid, user, data):
    # TODO: implement
    pass


@sio.on('server_score')
def get_score_handler(sid):
    global logged_players
    score = players.iloc[int(logged_players[sid])]['score']
    data = chatlib.build_message(chatlib.PROTOCOL_SERVER['score'], str(score))
    sio.emit(event='score_callback', data=data, to=sid)


def get_highscore_handler(sid):
    # TODO: implement
    pass


def add_question_handler(sid, data):
    # TODO: implement
    pass


def update_question_bank(sid):
    # TODO: implement
    pass


### APP PROCESS ###
def main():
    # sio.on(event='event', handler=login_handler)
     eventlet.wsgi.server(eventlet.listen((host, port)), app)
    # TODO: complete main()


if __name__ == '__main__':
    main()


