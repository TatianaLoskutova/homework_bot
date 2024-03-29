import http
import json
import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    APIRequestsError,
    APIResponseError,
    MissingHomeworksKeyError,
    UnknownHomeworkNameError,
    UnknownHomeworkStatusError,
    TelegramError,
)

load_dotenv()

logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
}

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': int(time.time())}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for value in tokens.values():
        if not value:
            return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправлено в Telegram')
    except telegram.error.TelegramError as error:
        logger.error(error)
        raise TelegramError('Ошибка при отправке сообщения в Телеграм')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=PAYLOAD,
        )
        if homework_statuses.status_code != http.HTTPStatus.OK:
            logger.error('Ошибка при запросе к API')
            raise APIRequestsError(
                homework_statuses.status_code,
                'Ошибка при запросе к API',
            )
        return homework_statuses.json()
    except requests.RequestException as request_error:
        logger.error(f'Ошибка при запросе к API: {request_error}')
        raise APIRequestsError(f'Ошибка при запросе к API: {request_error}')
    except json.JSONDecodeError as json_error:
        logger.error(f'Ошибка при разборе JSON: {json_error}')
        raise APIResponseError('Ошибка при разборе JSON')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logger.error('Полученная структура данных не словарь.')
        raise TypeError('Полученная структура данных не словарь.')
    if 'homeworks' not in response:
        raise MissingHomeworksKeyError(
            'Отсутствует ключ "homeworks" в ответе API.'
        )
    if not isinstance(response['homeworks'], list):
        logger.error('Полученная структура данных не список.')
        raise TypeError('Полученная структура данных не список.')
    return response['homeworks'][0]


def parse_status(homework):
    """Извлечение информации о статусе конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise UnknownHomeworkStatusError(status)
    if not homework_name:
        raise UnknownHomeworkNameError(homework_name)
    verdict = HOMEWORK_VERDICTS.get(status, 'Статус неизвестен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if not check_tokens():
        logging.critical(
            'Отсутствуют необходимые переменные окружения'
        )
        raise EnvironmentError(
            'Отсутствуют необходимые переменные окружения'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    initial_timestamp = timestamp - 2000
    errors_dict = {'error': None}

    while True:
        try:
            api_response = get_api_answer(initial_timestamp)
            check_response(api_response)
            homework = api_response['homeworks']
            if not homework:
                message = 'Нет ДЗ для проверки'
                logger.debug(message)
            else:
                message = parse_status(homework[0])
                if errors_dict.get(homework[0]['homework_name']) != message:
                    send_message(bot, message)
                    timestamp = api_response.get('current_date', timestamp)
                    errors_dict[homework[0]['homework_name']] = message
                else:
                    message = 'Статус домашки не изменился.'
                    logger.debug(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors_dict['error'] != message:
                logger.error(message)
                send_message(bot, message)
            errors_dict['error'] = message
        except TelegramError as telegram_error:
            logger.error(
                f'Ошибка в отправке сообщения в Телеграм: {telegram_error}'
            )
            pass
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
