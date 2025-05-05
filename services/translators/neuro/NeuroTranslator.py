from neuro import neuro
from config import RMQ_QUEUE_4_ANSWERS
from transport.rabbitmq.Message import Message
from transport.rabbitmq.MessageSender import MessageSender
from services.translators.BaseTranslator import BaseTranslator


class NeuroTranslator(BaseTranslator):
    def __init__(self):
        self.name = 'neuro'
        self.description = 'Наше кастомное решение для перевода'

    def __str__(self):
        return f"Neuro(name={self.name}, description={self.description})"

    def __repr__(self):
        return self.__str__()

    def execute(self, params: list):
        if params['text'] and params['lang'] and params['connection_id']:
            translator = neuro()
            data = translator.translate(params['text'], params['lang'])
            data['connection_id'] = params['connection_id']

            message = Message(data, RMQ_QUEUE_4_ANSWERS)

            sender = MessageSender()
            sender.send(message)

            return True
        return False
