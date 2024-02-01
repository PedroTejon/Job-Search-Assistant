from typing import Self


class MaxRetriesError(Exception):
    def __init__(self: Self) -> None:
        super().__init__(
            'MaxRetriesError: possível erro na autenticação/cookies ou no corpo da requisição e as respostas não retornam OK'
        )


class InvalidPlatformError(Exception):
    def __init__(self: Self) -> None:
        super().__init__('InvalidPlatformError: a plataforma inserida não está entre as suportadas')
