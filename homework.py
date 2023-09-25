from http import HTTPStatus
import logging
import pathlib
import os
import sys
import telegram
import time
import requests
from dotenv import load_dotenv
from exceptions import ErrorOnSendingMessage, ResponseIsNot200


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов."""
    list_of_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

    if not all(list_of_tokens):
        logging.critical('Отсутствует переменная окрудения')
        sys.exit()


def get_api_answer(timestamp):
    """Получение ответа от api Яндекса."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if response.status_code != HTTPStatus.OK:
            raise ResponseIsNot200(
                f"Response status code {response.status_code}")
        else:
            response = response.json()
    except Exception as error:
        raise TypeError(f'Error on programm running: {error}')
    return response


def check_response(response):
    """Проверка объекта, полученного через get_api_answer()."""
    if not isinstance(response, dict):
        raise TypeError(f'Response type {type(response)} is not dict')
    if 'current_date' not in response:
        raise ValueError('Thre is no current date in response')
    try:
        value = response['homeworks']
    except KeyError as error:
        raise KeyError(f'There is no such key {error}')

    if not isinstance(value, list):
        raise TypeError(f'Response value type {type(value)} is no list')

    return value


def parse_status(homework):
    """Получение нужных данных для отправки в телеграм."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        if homework_status in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS.get(homework_status)
        else:
            raise KeyError('There is no such status in HOMEWORK VERDICTS')
    except Exception:
        raise TypeError('There is no such homework')

    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'

    return message


def send_message(bot, message):
    """Функция, отправляющая сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Message are sended')
    except Exception:
        raise ErrorOnSendingMessage


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time() - RETRY_PERIOD - 500000)
    timestamp = {'from_date': timestamp}

    previous_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            value = check_response(response)

            if value:
                value = value[0]
                message = parse_status(value)

            if previous_message != message:
                send_message(bot, message)
            else:
                logging.debug('Message the same as previous')
            timestamp = response.get('current_date')
        except ErrorOnSendingMessage as error:
            logging.error(error)
        except Exception as error:
            message = f'Error on programm running: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s',
        level=logging.DEBUG,
        filename=f'{pathlib.Path(__file__)}.log',
        filemode='w'
    )

    main()
