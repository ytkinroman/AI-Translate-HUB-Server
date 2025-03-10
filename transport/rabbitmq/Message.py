class Message:
    def __init__(self, data: dict, queue: str):
        self.data = data
        self.queue = queue

    def get_queue(self):
        return self.queue

    def get_data(self):
        return self.data

    def set_data(self, data: dict):
        self.data = data

    def set_queue(self, queue: str):
        self.queue = queue
