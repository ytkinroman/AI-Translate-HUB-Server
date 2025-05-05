import sys
import json
import logging
import time
from pathlib import Path

import pika
import torch
from jsonrpcserver import dispatch
from transformers import (
    pipeline,
    WhisperForConditionalGeneration,
    WhisperProcessor,
    BlipProcessor,
    BlipForConditionalGeneration
)

from RabbitMQ.send_message import MessageSender
from config import (
    RABBIT_HOST,
    RABBIT_PORT,
    RABBIT_USER,
    RABBIT_PASSWORD,
    MODELS_PATH,
    MODEL_FOR_IMAGE,
    MODEL_FOR_TRANSCRIBE
)


WORK_QUEUE = 'requests'
RESULT_QUEUE = 'results'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class ResultHandler:
    def __init__(self):
        pass
    
    def _on_message(self, ch, method, properties, body):
        try:
            logging.info(f"[Handler] Received message: {body}")
            params = json.loads(body)
            service = params.get('service')
            chat_id = params.get('chat_id')
            if not service or chat_id is None:
                logging.error("[Handler] Missing 'service' or 'chat_id'")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            rpc = json.dumps({
                "jsonrpc": "2.0",
                "method": service,
                "params": [params.get('payload')],
                "id": params.get('message_id', '1')
            })
            
            logging.info(f"[Handler] Dispatching RPC: {rpc}")
            
            response = dispatch(rpc, context={'pipelines': self.pipelines})
            resp_str = str(response)

            if resp_str:
                resp = json.loads(resp_str)
                if 'result' in resp:
                    result = {
                        'chat_id': chat_id,
                        'message': resp['result'],
                        'message_id': params.get('message_id')
                    }
                    logging.info(f"[Handler] Result: {resp['result']}")
                    if result['message'] and service != 'telegram':
                        with MessageSender() as sender:
                            sender.send_message(RESULT_QUEUE, result)
                else:
                    logging.error(f"[Handler] Error from service: {resp.get('error')}")
            else:
                logging.info("[Handler] Notification (no response expected)")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logging.exception(f"[Handler] Exception: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _connect_and_consume(self):
        params = pika.ConnectionParameters(
            host=RABBIT_HOST,
            port=RABBIT_PORT,
            credentials=pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD),
            heartbeat=30,
            socket_timeout=300
        )
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=WORK_QUEUE, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=WORK_QUEUE,
            on_message_callback=self._on_message
        )
        logging.info("[Consumer] Waiting for messages. To exit press CTRL+C")
        channel.start_consuming()

    def start(self):
        while True:
            connection = None
            try:
                self._connect_and_consume()
            except KeyboardInterrupt:
                logging.info("[Consumer] Interrupted by user, shutting down...")
                break
            except Exception as e:
                logging.exception(f"[Consumer] Error, retry in 5s: {e}")
                time.sleep(5)

if __name__ == '__main__':
    worker = ResultHandler()
    worker.start()