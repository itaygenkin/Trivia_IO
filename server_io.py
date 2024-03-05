import socketio
import eventlet
import requests
import chatlib
import random
import pandas as pd
import logging
import atexit
import sys

###############
### GLOBALS ###
###############

host = '127.0.0.1'
port = 8080
questions_bank = pd.DataFrame({'question': ['Which Basketball team has completed two threepeats?'],
                               'answers': [['Chicago Bulls', 'LA Lakers', 'Golden state Warriors', 'Boston Celtics']],
                               'correct_answer': ['Chicago Bulls'],
                               'id': 1})

players = pd.DataFrame({'username': [],
                        'password': [],
                        'score': [],
                        'is_creator': [],
                        'id': [],
                        'sid': []})


###########################
### BASIC CONFIGURATION ###
###########################

@atexit.register
def cleanup():
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
    if not response.ok:
        logging.info(msg=f'GET request failed. Status code: {response.status_code}')
        exit()
    payload = response.json()['results']

    questions = []
    answers = []
    correct_answers = []

    for q in payload:
        question = chatlib.parse_notation(q['question'])
        if question in questions_bank['question'].values:
            continue
        questions.append(question)

        correct_answer = q['correct_answer']
        incorrect_answers = q['incorrect_answers']

        # create a list of all answers and add the list to {answers} list
        answers.append(gather_answers(correct_answer, incorrect_answers))
        correct_answers.append(correct_answer)

    max_id = questions_bank.id.max()
    # add the questions to the questions bank
    questions_to_add = pd.DataFrame({'question': questions, 'answers': answers, 'correct_answer': correct_answers,
                                     'id': range(max_id + 1, len(questions) + max_id + 1)})
    questions_bank = questions_bank._append(questions_to_add, ignore_index=True)
    logging.info(msg='successfully updated questions from web')


def write_to_csv():
    players.to_csv(sys.argv[1], index=False, mode='w')


def read_and_append_csv():
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
def connect(sid, environ):
    print(sid, 'connected...')
    logging.info(msg=f'{sid} connected')


@sio.event
def disconnect(sid):
    sio.disconnect(sid=sid)
    sid_index = players.loc[players['sid'] == sid]['sid'].index
    if len(sid_index) > 0 and sid in players.iloc[sid_index[0]].values:
        players.at[sid_index[0], 'sid'] = None
    print(sid, 'disconnected...')
    logging.info(msg=f'{sid} disconnected')


def send_error(sid, error_msg):
    """
    sends an error with a message
    :param sid: the session id of the client to be sent to
    :param error_msg: an error message to be sent
    :type error_msg: str
    """
    sio.emit(event='error', data=error_msg, to=sid)
    print('[SERVER]: ', error_msg)


################
### Handlers ###
################

@sio.on('login')
def login_handler(sid, data):
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
        elif players.loc[(players['username'] == user) & (players['password'] == password)]['sid'].values[0]:
            err_msg = f'{user} has already logged in'
            msg_back = chatlib.build_message(chatlib.PROTOCOL_SERVER['login_failed_msg'], err_msg)

        # check if user tried to log in without the right permission
        elif user_mode != players.loc[(players['username'] == user) &
                                      (players['password'] == password)]['is_creator'].values[0]:
            print(user_mode)
            print(players.loc[(players['username'] == user) &
                                      (players['password'] == password)]['is_creator'].values[0])
            err_msg = f"{user} does not have manager permission"
            msg_back = chatlib.build_message(chatlib.PROTOCOL_SERVER['login_failed_msg'], err_msg)

        # the user has successfully logged in
        else:
            index = players.loc[(players['username'] == user) & (players['password'] == password)].index[0]
            players.at[index, 'sid'] = sid
            msg_back = chatlib.build_message(chatlib.PROTOCOL_SERVER['login_ok_msg'], 'Successfully logged in')
            logging.info(msg=f'{user} successfully logged in')

    except AttributeError as e:
        msg_back = 'Failed to log in. Try again.'
        send_error(sid, "Incorrect username or password")
    except Exception as e:
        msg_back = 'Failed to log in. Try again.'
        logging.info(msg=f'Exception>> login_handler>> {e}')
        logging.info(msg=f'Something wrong happened when a user tried to log in.\nsid: {sid}')
    finally:
        sio.emit(event='login_callback', to=sid, data=msg_back)
        print('[SERVER] ', msg_back)


@sio.on('logout')
def logout_handler(sid):
    sio.disconnect(sid)


def create_random_question(sid):
    # q_asked = players.loc[players['sid'] == sid]['questions_asked'].values
    qid = random.choice([x for x in range(1, questions_bank['id'].max())])
    question = questions_bank.iloc[qid]
    return str(qid) + '#' + question['question'] + '#' + '#'.join(question['answers'])


@sio.on('play_question')
def play_question_handler(sid):
    question_data = create_random_question(sid)
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_SERVER['question'], question_data)
    sio.emit(event='play_question_callback', data=data_to_send, to=sid)
    print('[SERVER] ', data_to_send)


@sio.on('answer')
def answer_handler(sid, data):
    cmd, msg = chatlib.parse_message(data)
    qid, ans = chatlib.split_data(msg, 1)

    # check if the user is correct
    if questions_bank.iloc[int(qid)]['correct_answer'] == ans:
        data_to_send = chatlib.build_message(chatlib.PROTOCOL_SERVER['correct'], 'YOU GOT 5 POINTS.')
        user_index = players.loc[players['sid'] == sid].index[0]
        # players.at[user_index, 'questions_asked'].append(qid)
        players.at[user_index, 'score'] += 5
    else:
        data_to_send = chatlib.build_message(chatlib.PROTOCOL_SERVER['wrong'], '')
    sio.emit(event='answer_callback', data=data_to_send, to=sid)


@sio.on('server_score')
def get_score_handler(sid):
    score = players.loc[players['sid'] == sid]['score'].values[0]
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_SERVER['score'], str(score))
    sio.emit(event='score_callback', data=data_to_send, to=sid)
    print('[SERVER] ', data_to_send)


@sio.on('server_highscore')
def get_highscore_handler(sid):
    highscore = players.sort_values(by=['score'], ascending=False)[['username', 'score']].head(10)
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_CLIENT['high'], highscore.to_string(index=False))
    sio.emit(event='highscore_callback', data=data_to_send, to=sid)
    print('[SERVER] ', data_to_send)


@sio.on('server_add_question')
def add_question_handler(sid, data):
    data_to_send = ''
    try:
        q_data = chatlib.parse_message(data)
        max_id = questions_bank.id.max()
        question_to_add = pd.DataFrame({'question': q_data[0], 'answers': [q_data[1], q_data[2], q_data[3], q_data[4]],
                                        'correct_answer': q_data[5], 'id': max_id})
        questions_bank._append(question_to_add)
        data_to_send = chatlib.build_message(chatlib.PROTOCOL_SERVER['add_succ'], "")
        logging.info(msg='successfully added question')
    except Exception as e:
        data_to_send = chatlib.build_message(chatlib.PROTOCOL_SERVER['error'], 'Failed to add the question.')
        logging.info(msg='Failed to add question')
        logging.info(msg=f'Exception>> add_question_handler>> {e}')
    finally:
        sio.emit(event='add_question_callback', data=data_to_send, to=sid)


@sio.on('logged_in_users')
def get_logged_in_users(sid):
    logged_in_users = players.loc[players['sid'].notnull()][['username', 'id']]
    data_to_send = chatlib.build_message(chatlib.PROTOCOL_CLIENT['logged_in'], logged_in_users.to_string())
    sio.emit(event='get_logged_in_callback', data=data_to_send, to=sid)
    print('[SERVER] ', data_to_send)


###################
### APP PROCESS ###
###################

if __name__ == '__main__':
    update_questions_bank_from_web()
    read_and_append_csv()
    eventlet.wsgi.server(eventlet.listen((host, port)), app)
