import logging
from jsonrpcserver import Success, Error
from services.doc_parser.parser import Parser
from JSON_RPC.commands.base_command import BaseCommand


class CmdParseDoc(BaseCommand):
    def Execute(self, params: dict):
        try:
            payload = params.get('payload')
            pipeline = params.get("pipeline")
            caption = payload.get('caption')
            result = dict()

            if not pipeline:
                logging.error("[CMD_Transcribe] ASR pipeline not found or not initialized in context")
                return Error(code=500, message="ASR pipeline not found")

            file_path = payload.get("file_path")
            file_type = payload.get("file_type")

            parser = Parser(file_type, file_path, pipeline)

            result['data'] = parser.parse()

            if caption:
                result['caption'] = caption

            return Success(result)
        except Exception as e:

            logging.error(f"[CmdParseDoc] Error: {e}")
            return Error(code=500, message=str(e))
