class ErrorOnSendingMessage(Exception):
    """ERROR on sending message"""


class ResponseIsNot200(Exception):
    """Status code of response is not equal 200"""
