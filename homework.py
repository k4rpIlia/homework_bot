import logging

import os

import sys

import time

from dotenv import load_dotenv

import requests

import telegram

from http import HTTPStatus


load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_PRAKTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

error_handler = logging.StreamHandler(sys.stdout)
error_handler.setLevel(logging.DEBUG)
error_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger()
logger.addHandler(error_handler)


def check_tokens():
    """
    Проверяет доступность переменных окружения.
    которые необходимы для работы программы.
    """
    required_tokens = [
        'PRACTICUM_TOKEN',
        'TELEGRAM_TOKEN',
        'TELEGRAM_CHAT_ID']
    for token_name in required_tokens:
        if not globals().get(token_name):
            error_message = f'Отсутствует переменная окружения: {token_name}'
            logging.critical(error_message)
            return False
        else:
            return True


def send_message(bot, message):
    """Функция отправляет сообщение в чат."""
    try:
        bot.send_message(chat_id=23436567687654, text=message)
        logging.debug('Отправлено сообщение в Telegram')
    except telegram.error.TelegramError:
        logging.error('Ошибка отправки сообщения')


def get_api_answer(timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.
    В случае успешного запроса должна вернуть ответ API,
    приведенный к типу данных Python.
    """
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            error_message = (
                f'Ошибка в запросе! Gfhаметры запроса:{payload},'
                f'Код ответа: {response.status_code},'
                f'Контент ответа: {response.content}')
            raise Exception(error_message)
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к API: {error}')


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.
    На вход получает результат функции get_api_answer().
    """
    if not isinstance(response, dict):
        err_message = "Полученный ответ не является словарем"
        logging.error(err_message)
        raise TypeError(err_message)

    required_keys = {"homeworks", "current_date"}
    if not required_keys.issubset(response.keys()):
        err_message = ('В ответе API домашки нет ключей '
                       '`homeworks` или `current_date`')
        logging.error(err_message)
        raise Exception(err_message)

    if not isinstance(response["homeworks"], list):
        err_message = ('В ответе API домашки данные под ключом '
                       '"homeworks" приходят не в виде списка.')
        logging.error(err_message)
        raise TypeError(err_message)

    if not response["homeworks"]:
        err_message = ('В словаре нет ключа "homeworks"')
        logging.error(err_message)
        raise TypeError(err_message)

    if not all(isinstance(hw, dict) for hw in response['homeworks']):
        err_message = 'Тип данных в "homeworks" не является словарем'
        raise TypeError(err_message)

    return True


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе.
    статус этой работы. В случае успеха, функция возвращает
    подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS.
    """
    if 'homework_name' in homework:
        homework_name = homework.get('homework_name')
    else:
        raise ValueError('В ответе API домашки нет ключа `homework_name`.')
    if 'status' in homework:
        status = homework.get('status')
        if status in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS[status]
            message = (f'Изменился статус проверки работы'
                       f' "{homework_name}". {verdict}')
            return message
        else:
            raise ValueError('Статус не соответствует ожидаемому')
    else:
        raise ValueError('Ошибка при получении статуса')


last_sent_message = None


def main():
    """Основная логика приложения."""
    global last_sent_message
    logging.info('Бот запущен')

    if not check_tokens():
        logging.critical()
        SystemExit

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                if response['homeworks'] == []:
                    logging.debug('Пустая домашка')
                status = parse_status(response.get('homeworks')[0])
                if status != last_sent_message:
                    if send_message(bot, status):
                        last_sent_message = status
                        timestamp = response.get('current_date', timestamp)
                    else:
                        logging.error('Ошибка отправки сообщения')
                else:
                    logging.debug('Статус работы  не изменился.')
        except Exception as error:
            message = error
            logging.exception('Сбой в работе программы: {error}')
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
