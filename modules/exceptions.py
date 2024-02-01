from typing import Self


class PossibleAuthError(Exception):
    def __init__(self: Self) -> None:
        super().__init__(
            'possível erro na autenticação/cookies, no corpo da requisição ou a autenticação expirou e as respostas não retornam OK'
        )


class InvalidPlatformError(Exception):
    def __init__(self: Self) -> None:
        super().__init__('a plataforma inserida não está entre as suportadas')
