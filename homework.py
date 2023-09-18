from http import HTTPStatus
import logging
import os
import sys
import telegram
import time
import requests
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w'
)


class ErrorOnSendingMessage(Exception):
    """Ошибка при отправке сообщения в телеграмм."""

    pass


class ResponseIsNot200(Exception):
    """Статус ответа Api не равен 200."""

    pass


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
    return True


def get_api_answer(timestamp):
    """Получение ответа от api Яндекса."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if response.status_code != HTTPStatus.OK:
            raise ResponseIsNot200(logging.error('Статус код не равен 200'))
        else:
            response = response.json()
    except Exception as error:
        raise TypeError(logging.critical(f'Сбой в работе программы: {error}'))
    return response


def check_response(response):
    """Проверка объекта, полученного через get_api_answer()."""
    if isinstance(response, dict) is not True:
        raise TypeError(logging.error(
            'Возвращаемый тип данных имеет отличия от dict'))
    else:
        try:
            value = response['homeworks']
        except KeyError as error:
            logging.error(f'Отсутствует ключ {error}')

    if isinstance(value, list) is not True:
        raise TypeError(logging.error('Данные не приходят в виде list'))
    elif len(value) == 0:
        raise ValueError(logging.error('List домашнего задания пуст'))
    else:
        return value[0]


def parse_status(homework):
    """Получение нужных данных для отправки в телеграм."""
    if 'homework_name' in homework:
        homework_name = homework.get('homework_name')
        try:
            homework_status = homework.get('status')
            if homework_status in HOMEWORK_VERDICTS.keys():
                verdict = HOMEWORK_VERDICTS.get(homework_status)
        except Exception:
            raise KeyError(logging.error(
                'There is no such status in HOMEWORK_VERDICTS'))
    else:
        raise NameError(logging.error(
            'There is no homework_name in API answer'))

    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'

    return message


def send_message(bot, message):
    """Функция, отправляющая сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Message are sended')
    except Exception:
        raise ErrorOnSendingMessage(logging.error('Error on sending message'))


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time() - RETRY_PERIOD - 3000000)
    timestamp = {'from_date': timestamp}

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message:
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Error on programm running: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
