import uuid
from typing import List

from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.base import RunnableSerializable
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.constants.prompts import AGENT_COMPANY
from src.services.generator import Generator


class Agent(Generator):
    def __init__(self, tools: List[BaseTool] = []):
        super().__init__()

        self._memory = MemorySaver()
        self._tools = tools
        self._agent = create_react_agent(
            self.generator,
            self._tools,
            prompt=AGENT_COMPANY,
            checkpointer=self._memory,
        )

    def _create_rag_chain(
        self,
        prompt: ChatPromptTemplate,
    ) -> RunnableSerializable:
        raise NotImplementedError

    async def generate(self, message: str, thread_id: str | None = None):
        """Extract entities from the user's message

        Args:
            message (str): User's message

        Returns:
            dict: Extracted entities
        """
        effective_thread = thread_id or str(uuid.uuid4())
        response = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": effective_thread}},
        )
        return response["messages"][-1].content

    async def get_reponse(self, user_input: str, thread_id: str | None = None):
        response = await self.generate(user_input, thread_id=thread_id)
        return response

    def clear_memory(self):
        self._memory = MemorySaver()
        self._agent = create_react_agent(
            self.generator,
            self._tools,
            prompt=AGENT_COMPANY,
            checkpointer=self._memory,
        )
