class APIRequestsError(Exception):
    """Исключение, вызываемое при некорректном ответе от API."""
    pass


class UnknownHomeworkStatusError(Exception):
    """Исключение, вызываемое при получении недокументированного статуса домашней работы."""
    pass


class UnknownHomeworkNameError(Exception):
    """Исключение, вызываемое при отсутствии ключа названия домашней работы."""
    pass


class MissingHomeworksKeyError(Exception):
    """Исключение, вызываемое при отсутствии ключа 'homeworks' в ответе API"""
    pass


class CustomTelegramError(Exception):
    """Исключение при ошибке при отправке сообщения в Телеграм"""
    pass


class APIResponseError(Exception):
    """Ошибка при разборе JSON"""
    pass
