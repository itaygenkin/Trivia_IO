import socketio
import eventlet
import requests
import random
import pandas as pd
import logging
import atexit
import sys
import json

import chatlib
import helpers

###############
### GLOBALS ###
###############

HOST = '127.0.0.1'
PORT = 8080

questions_bank = pd.DataFrame({'question': ['Which Basketball team has completed two threepeats?'],
                               'answers': [['Chicago Bulls', 'LA Lakers', 'Golden state Warriors', 'Boston Celtics']],
                               'correct_answer': ['Chicago Bulls'],
                               'id': 1})

players = pd.DataFrame({'username': [],
                        'password': [],
                        'score': [],
                        'is_manager': [],
                        'id': [],
                        'sid': [],
                        'games_played': [],
                        'wins_in_row': []})
players['is_manager'] = players['is_manager'].astype(bool)


###########################
### BASIC CONFIGURATION ###
###########################

@atexit.register
def cleanup() -> None:
    print('-^--^-\n--ww--')
    logging.info(msg='an error occurred, server cleans up and shuts down')
    for sid in players['sid'].values:
        if sid is None:
            continue
        sio.disconnect(sid=sid)
        logging.info(msg=f'{sid} disconnected')
    write_to_csv()
    print('exiting...')


logging.basicConfig(filename='trivia_logger.log', level=logging.INFO, filemode='a',
                    format="%(asctime)s>> %(levelname)s>> %(msg)s;", datefmt='%d/%m/%y-%H:%M')

####################
### DATA LOADERS ###
####################


def update_questions_bank_from_web() -> None:
    global questions_bank
    response = requests.get(url="https://opentdb.com/api.php?amount=50&type=multiple")
    if not response.ok:
        logging.info(msg=f'GET request failed. Status code: {response.status_code}')
        exit()
    payload = response.json()['results']

    questions = []
    answers = []
    correct_answers = []

    for q in payload:
        question = helpers.parse_notation(q['question'])
        if question in questions_bank['question'].values:
            continue
        questions.append(question)

        correct_answer = q['correct_answer']
        incorrect_answers = q['incorrect_answers']

        # create a list of all answers and add the list to {answers} list
        answers.append(helpers.gather_answers(correct_answer, incorrect_answers))
        correct_answers.append(correct_answer)

    max_id = questions_bank.id.max()
    # add the questions to the questions bank
    questions_to_add = pd.DataFrame({'question': questions, 'answers': answers, 'correct_answer': correct_answers,
                                     'id': range(max_id + 1, len(questions) + max_id + 1)})
    questions_bank = questions_bank._append(questions_to_add, ignore_index=True)
    logging.info(msg='successfully updated questions from web')


def write_to_csv() -> None:
    players.to_csv(sys.argv[1], index=False, mode='w')


def read_and_append_csv() -> None:
    """
    reading a csv file and append the data to players data frame
    """
    global players
    temp_csv = pd.read_csv(sys.argv[1])
    max_id = players.id.max()
    for index, row in temp_csv.iterrows():
        if row.id <= max_id:
            continue
        next_row = row
        next_row['sid'] = None
        players = players._append(row)


######################
### SOCKET METHODS ###
######################

sio = socketio.Server()
app = socketio.WSGIApp(sio, static_files={'/': './content/'})


@sio.event
def connect(sid, environ) -> None:
    print(sid, 'connected...')
    logging.info(msg=f'{sid} connected')


@sio.event
def disconnect(sid) -> None:
    sio.disconnect(sid=sid)
    sid_index = players.loc[players['sid'] == sid]['sid'].index
    if len(sid_index) > 0 and sid in players.iloc[sid_index[0]].values:
        players.at[sid_index[0], 'sid'] = None
    print(sid, 'disconnected...')
    logging.info(msg=f'{sid} disconnected')


def send_error(sid, error_msg: str) -> None:
    """
    sends an error with a message
    :param sid: the session id of the client to be sent to
    :param error_msg: an error message to be sent
    :type error_msg: str
    """
    data = {'result': 'ERROR', 'msg': error_msg}
    sio.emit(event='error_callback', data=json.dumps(data), to=sid)
    print('[SERVER] ', error_msg)


################
### Handlers ###
################

def check_correct_username_n_password(username: str, password: str) -> bool:
    """
    checks if the username and password are correct,
    login_handler helper function
    """
    if username not in players['username'].values:
        return False
    elif players.loc[players['username'] == username]['password'].values[0] != password:
        return False
    else:
        return True


def check_user_logged_in(user: str, password: str) -> bool:
    """
    check if the user has already logged in,
    login_handler helper function
    :return: True if the user has already logged in, o/w False
    """
    return players.loc[(players['username'] == user) & (players['password'] == password)]['sid'].values[0]


def check_user_permission(user: str, password: str, user_type: bool) -> bool:
    """
    check if the user tried to access the back office without having permission,
    login_handler helper function
    :return: True if the user tried to access the back office without permission
    """
    return user_type != players.loc[(players['username'] == user) &
                                    (players['password'] == password)]['is_manager'].values[0]


@sio.on('login')
def login_handler(sid, data: str) -> None:
    data = json.loads(data)
    if data['command'] != helpers.PROTOCOL_CLIENT['login']:
        send_error(sid, 'Wrong direction')
        return

    data_to_send = {'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['login']}
    try:
        user, password = data['username'], data['password']
        user_type = helpers.PROTOCOL_USER_TYPE[data['user_type']]

        # check username and password correctness
        if not check_correct_username_n_password(user, password):
            data_to_send['msg'] = "Incorrect username or password"
            data_to_send['result'] = 'FAILURE'

        # check if user has already logged in
        elif check_user_logged_in(user, password):
            data_to_send['msg'] = f'{user} has already logged in.'
            data_to_send['result'] = 'FAILURE'

        # check if user tried to log in without the right permission
        elif check_user_permission(user, password, user_type):
            data_to_send['msg'] = "Access Denied."
            data_to_send['result'] = 'FAILURE'

        # the user has successfully logged in
        else:
            index = players.loc[(players['username'] == user) & (players['password'] == password)].index[0]
            players.at[index, 'sid'] = sid  # update the session id of the user
            data_to_send['msg'] = 'Successfully logged in'
            data_to_send['result'] = 'ACK'
            logging.info(msg=f'{user} successfully logged in')

    except AttributeError as e:
        msg_back = 'Failed to log in. Try again.'
        send_error(sid, msg_back)
        print('[SERVER] ', msg_back)
    except Exception as ex:
        msg_back = 'Failed to log in. Try again.'
        logging.info(msg=f'Exception>> login_handler>> {ex}')
        logging.info(msg=f'Something wrong happened when a user tried to log in.\nsid: {sid}')
        send_error(sid, msg_back)
        print('[SERVER] ', msg_back)
    else:
        sio.emit(event='login_callback', to=sid, data=json.dumps(data_to_send))
        print('[SERVER] ', data_to_send['msg'])


@sio.on('logout')
def logout_handler(sid):
    sio.disconnect(sid)


def create_random_question() -> dict:
    qid = random.choice([x for x in range(1, questions_bank['id'].max())])
    rand_question = questions_bank.iloc[qid]
    return {'qid': qid, 'question': rand_question['question'], 'answers': rand_question['answers']}


@sio.on('play_question')
def play_question_handler(sid) -> None:
    question_data = create_random_question()
    question_data['command'] = helpers.PROTOCOL_SERVER['question']
    sio.emit(event='play_question_callback', data=json.dumps(question_data), to=sid)
    print('[SERVER] ', question_data)


@sio.on('answer')
def answer_handler(sid, data: str) -> None:
    data = json.loads(data)
    # check for the right direction
    if data['command'] != helpers.PROTOCOL_CLIENT['ans']:
        send_error(sid, 'Wrong direction')
    qid, ans = data['question_id'], data['answer']

    user_index = players.loc[players['sid'] == sid].index[0]
    data_to_send = {'result': 'FAILED', 'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['ans'], 'msg': ''}

    # check if the user is correct
    if questions_bank.iloc[int(qid)]['correct_answer'] == ans:
        players.at[user_index, 'score'] += 5
        players.at[user_index, 'wins_in_row'] += 1

        data_to_send['msg'] = 'Correct answer.\nYOU GOT 5 POINTS.'
        data_to_send['result'] = 'ACK'
    else:
        players.at[user_index, 'wins_in_row'] = 0
        data_to_send['result'] = 'ACK'
        data_to_send['msg'] = 'WRONG ANSWER.'
    players.at[user_index, 'games_played'] += 1
    sio.emit(event='answer_callback', data=json.dumps(data_to_send), to=sid)


@sio.on('server_score')
def get_score_handler(sid) -> None:
    score = players.loc[players['sid'] == sid]['score'].values[0]
    data_to_send = {'result': 'ACK', 'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['score'],
                    'msg': str(score)}
    sio.emit(event='score_callback', data=json.dumps(data_to_send), to=sid)
    print('[SERVER] ', data_to_send)


@sio.on('server_highscore')
def get_highscore_handler(sid) -> None:
    highscore = players.sort_values(by=['score'], ascending=False)[['username', 'score']].head(10)
    data_to_send = {'result': 'ACK', 'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['highscore'],
                    'msg': highscore.to_string(index=False)}
    sio.emit(event='highscore_callback', data=json.dumps(data_to_send), to=sid)
    print('[SERVER] ', data_to_send)


@sio.on('server_add_question')
def add_question_handler(sid, data: str) -> None:
    try:
        q_data = json.loads(data)
        max_id = questions_bank.id.max()
        question_to_add = pd.DataFrame({'question': q_data['question'], 'answers': q_data['answers'],
                                        'correct_answer': q_data['correct_answer'], 'id': max_id})
        questions_bank._append(question_to_add)
        data_to_send = {'result': 'ACK', 'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['add_succ']}
    except Exception as e:
        logging.info(msg='Failed to add question')
        logging.info(msg=f'Exception>> add_question_handler>> {e}')
        send_error(sid, 'Failed to add the question.')
    else:
        logging.info(msg='successfully added question')
        sio.emit(event='add_question_callback', data=json.dumps(data_to_send), to=sid)


@sio.on('logged_in_users')
def get_logged_in_users_handler(sid):
    logged_in_users = players.loc[players['sid'].notnull()][['username', 'id']]
    data_to_send = {'result': 'ACK', 'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['logged_in'],
                    'msg': logged_in_users.to_string()}
    sio.emit(event='get_logged_in_callback', data=json.dumps(data_to_send), to=sid)
    print('[SERVER] ', data_to_send)


@sio.on('register_player')
def register_player_handler(sid, data: str) -> None:
    try:
        data = json.loads(data)
        username, password = data['username'], data['password']
    except TypeError as te:
        logging.info(msg=f'Error>> register_player_handler>> {te}')
        logging.info(msg='can\'t parse data')
        send_error(sid, 'can\'t parse data')
    else:
        # username must be unique
        # check if username has already registered
        if username in players['username'].values:
            logging.info(msg=f'tried to register an existing player, username: {username}')
            data_to_send = {'result': 'Failure', 'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['reg_fail'],
                            'msg': f"Username \'{username}\' has already registered"}
            sio.emit(event='register_player_callback', data=json.dumps(data_to_send), to=sid)
            return

        try:
            players.loc[len(players.index)] = [username, password, 0, False, players.id.max() + 1, None, 0, 0]
            ack_msg = f'Successfully registered {username}'
            print(f'[SERVER] ', ack_msg)
        except Exception as e:
            logging.info(msg=f'Exception>> register_player_handler>> {e}')
            send_error(sid, 'Failed to register player')
        else:
            logging.info(msg=ack_msg)
            data_to_send = {'result': 'ACK', 'protocol': 'server', 'command': helpers.PROTOCOL_SERVER['reg_succ'],
                            'msg': ack_msg}
            sio.emit(event='register_player_callback', data=json.dumps(data_to_send), to=sid)


###################
### APP PROCESS ###
###################

if __name__ == '__main__':
    update_questions_bank_from_web()
    read_and_append_csv()
    eventlet.wsgi.server(eventlet.listen((HOST, PORT)), app)
