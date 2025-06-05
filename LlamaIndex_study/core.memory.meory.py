# https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/memory/memory.py

from abc import abstractmethod
from enum import Enum
from typing import Any, Callable, Generic, List, Optional, TypeVar, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator

from sqlalchemy.ext.asyncio import AsyncEngine
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
from llama_index.core.async_utils import asyncio_run


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
    넘치는 메시지는 전부 메모리블락으로 취급한다.
    데이터필드와 공통 인터페이스 ('aget', 'aput', 'atruncate')도 함께 정의되어있음.
    즉, Memory Block은 저장된 대화 기록 또는 기타 정보들을 특정 방식으로 기억하거나, 가공하거나, 저장하거나, 꺼내오는 단위 모듈이다.
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
    아래의 역할을 하는거임:
        - 대화가 쌓이면 토큰이 넘침
        - 넘치는 메시지는 "기억 블록(memory block)"으로 넘어감
        - 나중에 aget() 호출되면, 각 memory block에 저장된 걸 꺼냄
        - 꺼낸 결과들은 chat history에 재삽입되거나 시스템 메시지로 들어감
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

    @classmethod
    def class_name(cls) -> str:
        return "Memory"
    
    @model_validator(mode="before") # 객체 생성 전에 필드들을 검증/보완 오 이런 방식으로도 함 와오
    @classmethod
    def validate_memory(cls, values: dict) -> dict:
        # Validate token limit
        token_limit = values.get("token_limit", -1)
        if token_limit < 1:
            raise ValueError("Token limit must be set and grater than 0.")
        
        tokenizer_fn = values.get("tokenizer_fn")
        if tokenizer_fn is None:
            values["tokenizer_fn"] = get_tokenizer()
        
        if values.get("token_flush_size", -1) < 1:
            values["token_flush_size"] = int(token_limit * 0.1)
        elif values.get("token_flush_size", -1) > token_limit:
            values["token_flush_size"] = int(token_limit * 0.1)
        
        # validate all blocks have unique names
        block_names = [block.name for block in values.get("memory_blocks", [])]
        if len(block_names) != len(set(block_names)):
            raise ValueError("All memory blocks must have unique names.")
    
        return values
    
    # 클래스 메서드로 기본 설정값을 기반으로 Memory 객체를 생성 (이것도 validation 역할인 듯)
    @classmethod
    def from_defaults(  # type: ignore[override]
        cls,
        session_id: Optional[str] = None,
        chat_history: Optional[List[ChatMessage]] = None,
        token_limit: int = DEFAULT_TOKEN_LIMIT,
        memory_blocks: Optional[List[BaseMemoryBlock[Any]]] = None,
        tokenizer_fn: Optional[Callable[[str], List]] = None,
        chat_history_token_ratio: float = 0.7,
        token_flush_size: int = DEFAULT_FLUSH_SIZE,
        memory_blocks_template: RichPromptTemplate = DEFAULT_MEMORY_BLOCKS_TEMPLATE,
        insert_method: InsertMethod = InsertMethod.SYSTEM,
        image_token_size_estimate: int = 256,
        audio_token_size_estimate: int = 256,
        # SQLAlchemyChatStore parameters
        table_name: str = "llama_index_memory",
        async_database_uri: Optional[str] = None,
        async_engine: Optional[AsyncEngine] = None,
    ) -> "Memory": # 문자열로 리턴타입을 정하는걸 "Forward Reference" 이라고함
        """Initialize Memory"""
        session_id = session_id or generate_chat_store_key()

        # If not using the SQLAlchemyChatStore, provide an error
        sql_store = SQLAlchemyChatStore(
            table_name=table_name,
            async_database_uri=async_database_uri,
            async_engine=async_engine,
        )

        if chat_history is not None:
            asyncio_run(sql_store.set_messages(session_id, chat_history))
        
        if token_flush_size > token_limit:
            token_flush_size = int(token_limit * 0.7)
        
        """
        Forward Reference:
            - 타입 힌트를 사용할 때, 해당 타입이 아직 정의되지 않았거나, 자기 자신을 가리켜야 하는 경우, "클래스 이름"처럼 문자열로 타입을 감쌀 수 있도록 허용
            - 예시 : 
                class Node:
                    def __init__(self, next_node: "Node"):
                        self.next = next_node
        
            - 이 메서드는 클래스 메서드이고, cls를 통해 Memory 클래스를 생성하려고 하고있음.
            - 이 시점에서 Memory 클래스 전체 정의가 아직 끝나지 않았기 때문에, Memory를 타입 힌트로 바로 쓰면 에러가 남.
            - 그래서 "Memory"라는 **문자열로 감싸서 “얘는 나중에 해석해줘”**라고 Python에 말하는거임.
            - *참고로 3.7부터는 "from __future__ import annotations" 을 import하면 문자열로 안 쓰고 걍 써도 됨
                - 예시:
                    from __future__ import annotations

                    class Node:
                        def __init__(self, next: Node):  # <- 문자열로 안 감싸도 됨!
                            self.next = next
        """
        return cls(
            token_limit=token_limit,
            tokenizer_fn=tokenizer_fn or get_tokenizer(),
            sql_store=sql_store,
            session_id=session_id,
            memory_blocks=memory_blocks or [],
            chat_history_token_ratio=chat_history_token_ratio,
            token_flush_size=token_flush_size,
            memory_blocks_template=memory_blocks_template,
            insert_method=insert_method,
            image_token_size_estimate=image_token_size_estimate,
            audio_token_size_estimate=audio_token_size_estimate,
        )
    
    def _estimate_token_count(
            self,
            message_or_blocks: Union[
                str, ChatMessage, List[ChatMessage], List[ContentBlock]
            ],
    ) -> int:
        """Estimate token count for a message."""
        token_count = 0

        # Normalize the input to a list of ContentBlocks
        if isinstance(message_or_blocks, ChatMessage):
            blocks = message_or_blocks.blocks

            # Estimate the token count for the additional kwargs
            if message_or_blocks.additional_kwargs:
                token_count += len(
                    self.tokenizer_fn(str(message_or_blocks.additional_kwargs))
                )
        elif isinstance(message_or_blocks, List):
            # Type narrow the list (타입 좁히기...실제 타입을 확인!)
            messages: List[ChatMessage] = []
            content_blocks: List[
                Union[TextBlock, ImageBlock, AudioBlock, DocumentBlock]
            ] = []
            # TODO: 여기서부터
        return 0



    async def aget(self, **block_kwargs: Any) -> List[ChatMessage]: # type: ignore[override]
        """
        Get messages with memory blocks included (async).
            - Memory 객체는 내부에 여러 memory_blocks를 갖고 있음
            - 각 블록은 자신만의 방식으로 기억을 저장하고 있음 (.aput()으로 과거에 저장했음)
            - 지금은 aget()이므로, 각 블록에게 “기억 꺼내줘” 요청을 보냄
        """
        # 1. 챗 히스토리 가져오고
        chat_history = await self.sql_store.get_messages(
            self.session_id, status=MessageStatus.ACTIVE
        )
        # 2. 챗 히스토리 토큰 계산하고 (토큰 제한 떔에)
        chat_history_tokens = sum(
            self._estimate_token_count(message) for message in chat_history
        )
        # 3. 메모리 블록 별로 얻은 콘텐츠를 꺼냄.
        # 4. 메모리 블록 토큰 계산 (토큰 제한 땜에)
        # 5. 필요하면 truncate
        # 6. 메모리 블락에서 꺼낸걸 "어떤 건 템플릿(요약, 지시)에 넣고", "어떤 건 바로 메시지(채팅)로 쓸 수 있는지" 분리
        # 7. 템플릿이 있으면 템플릿 내용을 채팅 매세지로 만들어야함.
        return None
    
        