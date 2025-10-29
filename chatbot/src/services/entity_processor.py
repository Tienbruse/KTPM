from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.base import RunnableSerializable
from src.constants.prompts import EXTRACT_ENTITIES
from src.schemas.entity import Entity
from src.services.generator import Generator


class EntityProcessor(Generator):
    def __init__(self):
        super().__init__()

        self._chain = self._create_rag_chain(
            prompt=ChatPromptTemplate.from_messages(
                [
                    ("system", EXTRACT_ENTITIES),
                    MessagesPlaceholder(variable_name="input"),
                ]
            ),
        )

    def _create_rag_chain(
        self,
        prompt: ChatPromptTemplate,
    ) -> RunnableSerializable:
        """Create a RAG chain

        Args:
            prompt (ChatPromptTemplate): prompt

        Raises:
            ValueError: LLM generator is not available

        Returns:
            RunnableSerializable: RAG chain
        """
        runnable = prompt | self.generator.with_structured_output(schema=Entity)

        return runnable

    def generate(self, message: str) -> dict:
        """Extract entities from the user's message

        Args:
            message (str): User's message

        Returns:
            dict: Extracted entities
        """
        print("message: ", message)
        entities: Entity = self._chain.invoke({"input": [message]})
        print("entities: ", entities)
        return entities.dict()

    def get_entities(self, user_input: str) -> Dict[str, Any]:
        """Get full entities

        Args:
            entities (_type_): entities object

        Returns:
            _type_: full entities object
        """
        entities_dict = self.generate(user_input)
        return entities_dict
