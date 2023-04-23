class Error:
    message: str

    def __init__(self, message: str) -> None:
        self.message = message


def error(message: str) -> Error:
    return Error(message)
