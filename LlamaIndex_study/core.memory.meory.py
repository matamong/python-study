# https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/memory/memory.py

from abc import abstractmethod
from enum import Enum
from typing import Any, Callable, Generic, List, Optional, TypeVar
import uuid
from pydantic import BaseModel, ConfigDict, Field

from llama_index.core.base.llms.types import (
    ChatMessage,
    ContentBlock,
    TextBlock,
    AudioBlock,
    ImageBlock,
    DocumentBlock,
)
from llama_index.core.memory.types import BaseMemory
from llama_index.core.prompts import RichPromptTemplate
from llama_index.core.storage.chat_store.sql import SQLAlchemyChatStore, MessageStatus
# from llama_index.core.storage.chat_store import SimpleChatStore <- 이걸로 대체 가능

from llama_index.core.utils import get_tokenizer


# Define type variable for memory block content
T = TypeVar("T", str, List[ContentBlock], List[ChatMessage])

DEFAULT_TOKEN_LIMIT = 30000
DEFAULT_FLUSH_SIZE = int(DEFAULT_TOKEN_LIMIT * 0.1)
DEFAULT_MEMORY_BLOCKS_TEMPLATE = RichPromptTemplate(
    """
<memory>
{% for (block_name, block_content) in memory_blocks %}
<{{ block_name }}>
  {% for block in block_content %}
    {% if block.block_type == "text" %}
{{ block.text }}
    {% elif block.block_type == "image" %}
      {% if block.url %}
        {{ (block.url | string) | image }}
      {% elif block.path %}
        {{ (block.path | string) | image }}
      {% endif %}
    {% elif block.block_type == "audio" %}
      {% if block.url %}
        {{ (block.url | string) | audio }}
      {% elif block.path %}
        {{ (block.path | string) | audio }}
      {% endif %}
    {% endif %}
  {% endfor %}
</{{ block_name }}>
{% endfor %}
</memory>
"""
)

class InsertMethod(Enum):
    SYSTEM = "system"
    USER = "user"


def generate_chat_store_key() -> str:
    """Generate a unique chat store key."""
    return str(uuid.uuid4())


# Q: 기본적으로 알아서 SQLAlchemy에서 뭘 해주나??
def get_default_chat_store() -> SQLAlchemyChatStore:
    """Get the default chat store."""
    return SQLAlchemyChatStore(table_name="llama_index_memory")


class BaseMemoryBlock(BaseModel, Generic[T]):
    """
    원문:
    A Base class for memory blocks.
    Subclasses must implement the 'aget' and 'aput' methods.
    Optionally, subclasses can implement the 'atruncate'method which is used to reduce the size of the memory block.
    
    메모:
    "메모리"블락 의 공통 구조와 동작을 정의한 추상 클래스.
    데이터필드와 공통 인터페이스 ('aget', 'aput', 'atruncate')도 함께 정의되어있음.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True) # 지금 이 BaseModel의 ConfigDict를 설정
    # Pydantic은 기본적으로 int, str, float, list, dict, datetime 등 표준 타입이나 Pydantic 모델만을 유효한 필드 타입으로 인정함.
    # 아래처럼 모르는 타입은 오류가 남.
    """
    class MyCustomClass:
        pass

    from pydantic import BaseModel

    class Demo(BaseModel):
        value: MyCustomClass  # X 기본적으로는 오류
    """
    # arbitrary_types_allowed=True로 하면 허용해줌.
    # DB 세션 객체, open file handler, socket, 커스텀 서비스 객체 등
    
    # 클래스 속성들 정의 (여기서는 Pydantic을 이용해서 정의 중)
    name: str = Field(description="The name/identifier of the memory block.") # Field는 메타데이터용.(문서 자동화에 주로 사용 됨)
    description: Optional[str] = Field(
        default=None, description="A description of the memory block."
    )
    priority: int = Field(
        default=0,
        description="Priority of this memory block (0 = never truncate, 1 = highest priority, etc.).",
    )
    accept_short_term_memory: bool = Field(
        default=True,
        description="Whether to accept puts from messages ejected from the short-term memory.",
    )


    @abstractmethod
    async def _aget(
        self, messages: Optional[List[ChatMessage]] = None, **block_kwargs: Any
    ) -> T:
        """
        Pull the memory block (async). 
        
        메모리 블록에서 데이터를 가져오는 함수
        - 하위 클래스에서 반드시 구현해야 하는 추상 함수. aget으로 구현해야함.
        - messages: 현재 대화 내용
        - **block_kwargs는 추가 옵션
        """

    async def aget(
            self, messages: Optional[List[ChatMessage]] = None, **block_kwargs: Any
    ) -> T:
        """
        외부에서 호출되는 실제 클래스
        (로깅이나 pre/post hook 등을 넣기 위해서 요렇게 감쌈!)
        """
        return await self._aget(messages, **block_kwargs)
    
    @abstractmethod
    async def _aput(self, messages: List[ChatMessage]) -> None:
        """
        Push to the memory block (async).
        """
    
    async def aput(
        self,
        messages: List[ChatMessage],
        from_short_term_memory: bool = False,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Push to the memory block (async).
        messages를 메모리 블록에 저장하는 역할
        """
        # 현재 블록이 받기를 원하지 않으면 → 리턴
        if from_short_term_memory and not self.accept_short_term_memory:
            return
        
        # session_id가 있으면, 각 메시지에 session_id를 추가로 붙여줌
        if session_id is not None:
            for message in messages:
                message.additional_kwargs["session_id"] = session_id
        
        await self._aput(messages)
    
    async def atruncate(self, content: T, tokens_to_truncate: int) -> Optional[T]:
        """
        메모리 블록 내용을 잘라내는 함수

        기본 동작은 "잘라내지 않고 전부 버리기" (None 리턴)
        선택적으로 하위 클래스에서 override 가능
        인자 설명:
            - content: 메모리 블록의 내용
            - tokens_to_truncate: 줄이고자 하는 토큰 수 (정확할 필요는 없고 힌트)
        """
        return None
    

class Memory(BaseMemory):
    """
    메시지 저장, 추론에 필요한 데이터 구성, 블록별 메모리 사용 조정.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    token_limit: int = Field(
        default=DEFAULT_TOKEN_LIMIT,
        description="The overall token limit of the memory.",
    )
    token_flush_size: int = Field(
        default=DEFAULT_FLUSH_SIZE,
        description="The token size to use for flushing the FIFO queue.",
    )
    chat_history_token_ratio: float = Field(
        default=0.7,
        description="Minimum percentage ratio of total token limit reserved for chat history.",
    )
    memory_blocks: List[BaseMemoryBlock] = Field(
        default_factory=list,
        description="The list of memory blocks to use.",
    )
    memory_blocks_template: RichPromptTemplate = Field(
        default=DEFAULT_MEMORY_BLOCKS_TEMPLATE,
        description="The template to use for formatting the memory blocks.",
    )
    insert_method: InsertMethod = Field(
        default=InsertMethod.SYSTEM,
        description="Whether to inject memory blocks into a system message or into the latest user message.",
    )
    image_token_size_estimate: int = Field(
        default=256,
        description="The token size estimate for images.",
    )
    audio_token_size_estimate: int = Field(
        default=256,
        description="The token size estimate for audio.",
    )
    tokenizer_fn: Callable[[str], List] = Field(
        default_factory=get_tokenizer,
        exclude=True,
        description="The tokenizer function to use for token counting.",
    )

    # 메시지를 저장할 백엔드 저장소
    sql_store: SQLAlchemyChatStore = Field(
        default_factory=get_default_chat_store,
        exclude=True,
        description="The chat store to use for storing messages.",
    )
    session_id: str = Field(
        default_factory=generate_chat_store_key,
        description="The key to use for storing messages in the chat store.",
    )
