import re
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.base import RunnableSerializable

from src.constants.prompts import EXTRACT_ENTITIES
from src.schemas.entity import Entity
from src.services.generator import Generator
from src.settings import SETTINGS
from src.utils.logger import logger


class EntityProcessor(Generator):
    def __init__(self):
        self._mode = SETTINGS.ENTITY_EXTRACTOR_MODE.lower()
        self._fast_field = SETTINGS.FAST_ENTITY_FIELD
        self._hybrid_length_threshold = SETTINGS.HYBRID_LENGTH_THRESHOLD

        if self._mode != "fast":
            super().__init__()
            self._chain = self._create_rag_chain(
                prompt=ChatPromptTemplate.from_messages(
                    [
                        ("system", EXTRACT_ENTITIES),
                        MessagesPlaceholder(variable_name="input"),
                    ]
                ),
            )
        else:
            self._chain = None

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
        text = (message or "").strip()
        if not text:
            return {}

        if self._mode == "fast":
            return self._fast_extract(text)

        if self._mode == "hybrid":
            # Try heuristic first for short/simple queries; fallback to LLM if not confident.
            if len(text) <= self._hybrid_length_threshold and "," not in text:
                fast_entities = self._fast_extract(text, allow_partial=True)
                if fast_entities:
                    logger.debug(
                        "Hybrid extractor used fast path",
                        extra={"entities": fast_entities, "message": text},
                    )
                    return fast_entities

        # LLM path
        entities: Entity = self._chain.invoke({"input": [message]})
        logger.debug(
            "LLM entity extraction result",
            extra={"message": message, "entities": entities.dict()},
        )
        return entities.dict()

    def _fast_extract(self, text: str, allow_partial: bool = False) -> dict:
        """Heuristic extraction for simple cases without LLM."""
        lowered = text.lower()

        # Remove leading helper phrases.
        leading_patterns = [
            r"^giới thiệu về",
            r"^thông tin về",
            r"^cho tôi biết về",
            r"^tìm kiếm",
            r"^tìm",
        ]
        cleaned = lowered
        for pat in leading_patterns:
            cleaned = re.sub(pat, "", cleaned).strip()

        # If text mentions products explicitly.
        if "sản phẩm" in cleaned:
            prod_part = cleaned.split("sản phẩm", 1)[1].strip(",. :- ")
            if prod_part:
                return {"product_names": prod_part}
            if allow_partial:
                return {}

        # Heuristic company name: strip common prefixes and filler words.
        company_prefixes = [
            "công ty",
            "doanh nghiệp",
            "tập đoàn",
            "cty",
            "ctcp",
            "tnhh",
            "jsc",
        ]
        tokens = [tok for tok in re.split(r"[\\s,.;:-]+", cleaned) if tok]
        filtered = []
        for tok in tokens:
            if tok in company_prefixes:
                continue
            filtered.append(tok)
        company_candidate = " ".join(filtered).strip(" ,.;:-")
        company_candidate = re.sub(
            r"\\b(ở|o|tai|tại)\\b.*", "", company_candidate, flags=re.IGNORECASE
        ).strip(" ,.;:-")

        if company_candidate:
            return {self._fast_field: company_candidate}

        return {} if allow_partial else {self._fast_field: text}

    def get_entities(self, user_input: str) -> Dict[str, Any]:
        """Get full entities

        Args:
            entities (_type_): entities object

        Returns:
            _type_: full entities object
        """
        entities_dict = self.generate(user_input)
        return entities_dict
