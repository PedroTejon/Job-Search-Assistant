from threading import Thread


class ExtractionThread(Thread):
    def __init__(self, execution_id: str, target: callable, name: str) -> None:
        super().__init__(target=target, name=name, args=[execution_id])
        self.execution_id = execution_id
        self.target = target
        self.name = name
