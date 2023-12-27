class MaxRetriesException(Exception):
    def __init__(self):
        super().__init__('MaxRetriesException: possible error in authentication/cookies or request body and requests don\'t return OK')
