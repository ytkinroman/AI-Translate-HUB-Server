import logging
from jsonrpcserver import Success, Error
from JSON_RPC.commands.base_command import BaseCommand
from services.transcribe.transcriber import Transcriber


class CmdTranscribe(BaseCommand):
    def Execute(self, params: dict):
        payload = params.get('payload')
        pipeline = params.get("pipeline")
        caption = payload.get('caption')
        result = dict()

        if not pipeline:
            logging.error("[CMD_Transcribe] ASR pipeline not found or not initialized in context")
            return Error(code=500, message="ASR pipeline not found")

        transcriber = Transcriber(pipeline)

        file_path = payload.get("file_path")

        result['data'] = transcriber.transcribe(file_path)

        if caption:
            result['caption'] = caption

        logging.info(f"[CMD_Transcribe] Result: {params}")

        return Success(result)
