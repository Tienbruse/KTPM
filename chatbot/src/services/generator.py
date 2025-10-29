from abc import ABC, abstractmethod
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.base import RunnableSerializable
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from src.constants.enum import ModelSource
from src.settings import SETTINGS
from src.utils.logger import logger


class Generator(ABC):
    def __init__(self):
        logger.info(f"MODEL SOURCE: {SETTINGS.MODEL_SOURCE}")
        if SETTINGS.MODEL_SOURCE == ModelSource.OpenAI.value:
            self.__generator = ChatOpenAI(
                api_key=SecretStr(SETTINGS.OPENAI_API_KEY),
                temperature=SETTINGS.MODEL_TEMPERATURE,
                cache=False,
                model=SETTINGS.MODEL_NAME,
            )
        elif SETTINGS.MODEL_SOURCE == ModelSource.DeepSeek.value:
            self.__generator = ChatDeepSeek(
                api_key=SecretStr(SETTINGS.DEEPSEEK_API_KEY),
                temperature=SETTINGS.DEEPSEEK_MODEL_TEMPERATURE,
                cache=False,
                model=SETTINGS.DEEPSEEK_MODEL_NAME,
            )
        else:
            raise ValueError("Model source is not supported")

    @property
    def generator(self):
        return self.__generator

    @abstractmethod
    def _create_rag_chain(
        self,
        prompt: ChatPromptTemplate,
    ) -> RunnableSerializable:
        raise NotImplementedError

    @abstractmethod
    def generate(self, **kwargs) -> Any:
        raise NotImplementedError
