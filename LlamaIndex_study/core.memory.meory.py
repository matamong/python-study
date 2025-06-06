# https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/memory/memory.py

from abc import abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, Union, cast
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

    아래처럼 구현될 것 임.:
        class SummaryMemoryBlock(BaseMemoryBlock[str]):
            async def _aget(self, messages: List[ChatMessage], **kwargs) -> str:
                return summarize_messages(messages)  # 문자열 요약

            async def _aput(self, messages: List[ChatMessage]) -> None:
                store_in_summary_vector_db(messages)

            async def atruncate(self, content: str, tokens_to_truncate: int) -> Optional[str]:
                return truncate_text(content, tokens_to_truncate)
        
        class LongTermMemoryBlock(BaseMemoryBlock[List[ChatMessage]]):
            async def _aget(self, messages: List[ChatMessage], **kwargs) -> List[ChatMessage]:
                return self.retrieve_relevant_past_turns(messages)

            async def _aput(self, messages: List[ChatMessage]) -> None:
                self.store(messages)

    즉,
    BaseMemoryBlock은 다음과 같은 확장 지점을 열어둔 추상 클래스.
        aput(messages: List[ChatMessage]):
        → 이 메시지를 어디다 저장할지? 어떻게 기억할지?
        → 내가 정함! (벡터 DB든, Redis든, JSON 파일이든 OK)

        aget(...) -> T:
        → 저장한 기억을 어떤 방식으로 꺼낼지?
        → 검색/필터링/리트리벌 등 자유롭게 구현 가능

        atruncate(...):
        → 길면 어떻게 줄일지? 버릴지? 잘라낼지?
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
    
    # 클래스 메서드로 기본 설정값을 기반으로 Memory 객체를 생성 (사용자 정의 클래스로 만드는 느낌)
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
            
            if all(isinstance(item, ChatMessage) for item in message_or_blocks):
                messages = cast(List[ChatMessage], message_or_blocks) 
                """
                cast: message_or_blocks가 실제로는 List[ChatMessage]라고 타입검사에게 말해주는거임 (IDE를 위해서)                 
                """

                blocks = []
                for msg in messages:
                    blocks.extend(msg.blocks)
                
                # Estimate the token count for the additional kwargs
                token_count += sum(
                    len(self.tokenizer_fn(str(msg.additional_kwargs)))
                    for msg in messages
                    if msg.additional_kwargs
                )
            elif all(
                isinstance(item, (TextBlock, ImageBlock, AudioBlock, DocumentBlock))
                for item in message_or_blocks
            ):
                content_blocks = cast(
                    List[Union[TextBlock, ImageBlock, AudioBlock, DocumentBlock]],
                    message_or_blocks,
                )
                blocks = content_blocks
            else:
                raise ValueError(f"Invalid message type: {type(message_or_blocks)}")
        elif isinstance(message_or_blocks, str):
            blocks = [TextBlock(text=message_or_blocks)]
        else:
            raise ValueError(f"Invalid message type: {type(message_or_blocks)}")

        # block 유형별로 토큰 수를 추정해서 합산함.
        # 텍스트는 tokenizer로 실제 길이 계산
        # 이미지나 오디오는 설정된 추정값을 사용
        for block in blocks:
            if isinstance(block, TextBlock):
                token_count += len(self.tokenizer_fn(block.text))
            elif isinstance(block, ImageBlock):
                token_count += self.image_token_size_estimate
            elif isinstance(block, AudioBlock):
                token_count += self.audio_token_size_estimate
        
        return token_count

    async def _get_memory_blocks_content(
        self, chat_history: List[ChatMessage], **block_kwargs: Any
    ) -> Dict[str, Any]:
        """
        Get content from memory blocks in priority order

        self.memory_blocks 리스트에 있는 모든 memory block에 대해 aget()을 호출해서,
        그 결과(기억된 내용)를 모아서 Dict[str, Any] 형태로 리턴
        """
        content_per_memory_block: Dict[str, Any] = {}

        # Process memory blocks in priority order
        for memory_block in sorted(self.memory_blocks, key=lambda x: -x.priority):
            content = await memory_block.aget(
                chat_history, session_id=self.session_id, **block_kwargs
            )

            # Handle different return types from memory blocks
            if content and isinstance(content, list):
                # Memory block returned content blocks
                content_per_memory_block[memory_block.name] = content
            elif content and isinstance(content, str):
                # Memory block returned a string
                content_per_memory_block[memory_block.name] = content
            elif not content:
                continue
            else:
                raise ValueError(
                    f"Invalid content type received from memory block {memory_block.name}: {type(content)}"
                )
        return content_per_memory_block

    async def _truncate_memory_blocks(
        self,
        content_per_memory_block: Dict[str, Any],
        memory_blocks_tokens: int,
        chat_history_tokens: int,
    ) -> Dict[str, Any]:
        """Truncate memory blocks if total token count exceeds limit."""
        if memory_blocks_tokens + chat_history_tokens <= self.token_limit:
            return content_per_memory_block
        
        tokens_to_truncate = (
            memory_blocks_tokens + chat_history_tokens - self.token_limit
        )
        truncated_content = content_per_memory_block.copy()

        # Truncate memory blocks based on priority
        for memory_block in sorted(
            self.memory_blocks, key=lambda x: x.priority
        ):  # Lower priority first
            # Skip memory blocks with priority 0, they should never be truncated
            if memory_block.priority == 0:
                continue
            
            if tokens_to_truncate <= 0:
                break

            # Truncate content and measure tokens saved
            content = truncated_content.get(memory_block.name, [])

            truncated_block_content = await memory_block.atruncate(
                content, tokens_to_truncate
            )

            # Calculate tokens saved
            original_tokens = self._estimate_token_count(content)

            if truncated_block_content is None:
                new_tokens = 0
            else:
                new_tokens = self._estimate_token_count(truncated_block_content)
            
            tokens_saved = original_tokens - new_tokens
            tokens_to_truncate -= tokens_saved

            if truncated_block_content is None:
                truncated_content[memory_block.name] = []
            else:
                truncated_content[memory_block.name] = truncated_block_content
            
        # handle case whre we still have tokens to truncate
        # just remove the blocks starting from the least priority
        for memory_block in sorted(self.memory_blocks, key=lambda x: x.priority):
            if memory_block.priority == 0:
                continue

            if tokens_to_truncate <= 0:
                break

            # Truncate content and measure tokens saved
            content = truncated_content.pop(memory_block.name)
            tokens_to_truncate -= self._estimate_token_count(content)
        
        return truncated_content
    
    async def _format_memory_blocks(
        self, content_per_memory_block: Dict[str, Any]
    ) -> Tuple[List[Tuple[str, List[ContentBlock]]], List[ChatMessage]]:
        """
            Format memory blocks content into template data and chat messages.
            
            content_per_memory_block 는 아래처럼 생겼을 것.
            {
                "summary": "요약된 내용",
                "retrieval": [ChatMessage(...), ChatMessage(...)],
                "file_memory": [TextBlock(...), ImageBlock(...)]
            }
        """
        memory_blocks_data: List[Tuple[str, List[ContentBlock]]] = [] # 템플릿
        chat_message_data: List[ChatMessage] = [] # 그대로 채팅 히스토리에 들어갈 리스트

        for block in self.memory_blocks:
            if block.name in content_per_memory_block:
                content = content_per_memory_block[block.name]

                # Skip empty memory blocks
                if not content:
                    continue

                if (
                    isinstance(content, list)
                    and content
                    and isinstance(content[0], ChatMessage)
                ):
                    # 이건 이미 메시지 형태로 만들어진 것 → 직접 붙이기만 하면 됨
                    chat_message_data.extend(content)
                elif isinstance(content, str):
                    # 요약 문자열 등 → TextBlock으로 감싸고, 템플릿용으로 넘김
                    memory_blocks_data.append((block.name, [TextBlock(text=content)]))
                else:
                    # 이미지/문서 블록 등, 이미 ContentBlock 형태로 구성된 데이터
                    # 이것도 템플릿으로 넘김
                    memory_blocks_data.append((block.name, content))

        return memory_blocks_data, chat_message_data

    def _insert_memory_content(
        self,
        chat_history: List[ChatMessage], # 기존 대화 내용
        memory_content: List[ContentBlock], # 템플릿 기반 memory block이 생성한 요약/지식
        chat_message_data: List[ChatMessage], # memory block이 직접 생성한 메시지들
    ) -> List[ChatMessage]:
        """
        Insert memory content into chat history based on insert method.
        메모리 블록에서 나온 기억들(memory blocks) 을
        기존 대화(chat history)에 적절하게 삽입해서
        최종 채팅 히스토리 결과 리스트를 만들어줌.
        
        아래처럼 들어오면:
            chat_history = [
                ChatMessage(role="user", content="안녕"),
                ChatMessage(role="assistant", content="반가워요!"),
            ]
            memory_content = [
                TextBlock(text="이전 대화 요약: ..."),
            ]
            chat_message_data = [
                ChatMessage(role="assistant", content="이전 대화를 기반으로 이런 걸 기억하고 있어요."),
            ]

        이렇게 바꿈:
            [
                ChatMessage(role="system", blocks=[TextBlock(...) memory_content]),
                ChatMessage(role="assistant", content="이전 대화를 기반으로 이런 걸 기억하고 있어요."),
                ChatMessage(role="user", content="안녕"),
                ChatMessage(role="assistant", content="반가워요!"),
            ]
        """
        result = chat_history.copy()

        # Process chat messages
        if chat_message_data:
            result = [*chat_message_data, *result]
            """
            result = [
                ChatMessage(role="user", content="안녕"),
                ChatMessage(role="assistant", content="안녕하세요!"),
                ChatMessage(role="system", blocks=[...]),
            ]
            """
        
        # Process template-based memory blocks
        if memory_content:
            if self.insert_method == InsertMethod.SYSTEM:
                """
                기억(memory block 내용)을 채팅 기록(chat history)에 삽입하려고 하는데,
                그걸 삽입할 "system 메시지"가 이미 있는지 먼저 확인
                """
                # Find system message or create a new one
                system_idx = next(
                    (i for i, msg in enumerate(result) if msg.role == "system"), None
                )

                if system_idx is not None:
                    # Update existing system message
                    result[system_idx].blocks = [
                        *memory_content,
                        *result[system_idx].blocks
                    ]
                else:
                    # Create new system message at the beginning
                    result.insert(0, ChatMessage(role="system", blocks=memory_content))
            elif self.insert_method == InsertMethod.USER:
                # Find the latest user message
                session_idx = next(
                    (i for i, msg in enumerate(reversed(result)) if msg.role == "user"),
                    None,
                ) 
                # reversed 해서 마지막 result에 삽입할거임.

                if session_idx is not None:
                    # Get actual index (since we enumerated in reversed)
                    actual_idx = len(result) - 1 - session_idx
                    # Updated existing user message
                    result[actual_idx].blocks = [
                        *memory_content,
                        *result[actual_idx].blocks,
                    ]
                else:
                    result.append(ChatMessage(role="user", blocks=memory_content))
        
        return result

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
        content_per_memory_block = await self._get_memory_blocks_content(
            chat_history, **block_kwargs
        )
        # 4. 메모리 블록 토큰 계산 (토큰 제한 땜에)
        memory_blocks_tokens = sum(
            self._estimate_token_count(content) 
            for content in content_per_memory_block.values()
        )
        # 5. 필요하면 truncate
        truncated_content = await self._truncate_memory_blocks(
            content_per_memory_block, memory_blocks_tokens, chat_history_tokens
        )
        # 6. 메모리 블락에서 꺼낸걸 "어떤 건 템플릿(요약, 지시)에 넣고", "어떤 건 바로 메시지(채팅)로 쓸 수 있는지" 분리
        memory_blocks_data, chat_message_data = await self._format_memory_blocks(
            truncated_content
        )

        # 7. 템플릿이 있으면 템플릿 내용을 채팅 매세지로 만들어야함.
        memory_content = []
        if memory_blocks_data:
            memory_block_messages = self.memory_blocks_template.format_messages(
                memory_blocks=memory_blocks_data
            )
            memory_content = (
                memory_block_messages[0].blocks if memory_block_messages else []
            )
            # memory_block_messages의 첫번째를 쓴 memory_content라는 이 리스트는 최종적으로 system 메시지나 user 메시지에 삽입

        return self._insert_memory_content(
            chat_history, memory_content, chat_message_data
        )
    
    async def aput(self, message: ChatMessage) -> None:
        # TODO: 여기서부터
        pass
        