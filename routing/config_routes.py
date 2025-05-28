from fastapi import APIRouter, Depends
from pydantic import BaseModel
from client_settings.ClientSettingsProvider import ClientSettingsProvider

router = APIRouter()

class GetConfigRequest(BaseModel):
    """
    Модель запроса на получение конфигурации.

    Атрибуты:
        ui_lang: Язык интерфейса (по умолчанию "ru")
        version: Версия приложения (по умолчанию "1")
    """
    ui_lang: str = "ru"
    version: str = "1"

class GetConfigResponse(BaseModel):
    """
    Модель ответа на запрос конфигурации.

    Атрибуты:
        config: Словарь с конфигурацией
    """
    config: dict

@router.get("/api/v1/get_config")
async def get_config(params: GetConfigRequest = Depends()):
    settings_provider = ClientSettingsProvider(
        params={
            "ui_lang": params.ui_lang,
            "version": params.version
        }
    )
    
    return settings_provider.execute()
