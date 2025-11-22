
import numpy as np
from llama_index.core.bridge.pydantic import (
    Field,
    ConfigDict,
    model_validator,
)
from abc import abstractmethod

from itertools import product
from enum import Enum
from typing import Any, Callable, Coroutine, List, Optional, Sequence, Tuple, cast
from typing_extensions import Self
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.instrumentation import DispatcherSpanMixin
from llama_index.core.schema import BaseNode, MetadataMode, TransformComponent
from llama_index.core.instrumentation import DispatcherSpanMixin
from llama_index.core.constants import (
    DEFAULT_EMBED_BATCH_SIZE,
)
from llama_index.core.callbacks.base import CallbackManager


from pydantic import ConfigDict

from llama_index.core.instrumentation.events.embedding import (
    EmbeddingEndEvent,
    EmbeddingStartEvent,
)
import llama_index.core.instrumentation as instrument

# TODO: change to numpy array 라고 함. 오잉 numpy말고 list로 쓰고있었구나??
Embedding = List[float]

dispatcher = instrument.get_dispatcher(__name__) # 관찰용

class SimilarityMode(str, Enum):
    """similarity/distance 를 위한 노드들"""
    DEFAULT = 'cosine' # 각도 기반
    DOT_PRODUCT = 'dot_product' # 각도 + 길이(크기) 기반
    EUCLIDEAN = 'euclidean' # 거리 기반

def mean_agg(embeddings: List[Embedding]) -> Embedding:
    """임베딩들 평균내서 하나로 만드는 함수. 즉, 임베딩 벡터 여러 개를 하나의 ‘대표 임베딩’으로 평균내서 만드는 함수"""
    """
    왜 하냐면,
        - "AI가 재밌다"는 
        - 토큰이 "AI", "가", "재밌다" 3개가 나와서
        - 임베딩도 3개가 나옴.

    근데 이 문서 전체를 대표하는 임베딩 하나만 있으면 좋겠다는 상황이 생김 (주로 document-level 인덱스 만들거나, 여러 쿼리 변형을 합칠 때 등등)
    이 때, 제일 단순하게 그냥 평균내서 벡터 하나 만들어버리는거임.
    """
    """
    embeddings = [
        [0.1, 0.2, 0.3],   # e1
        [0.2, 0.0, 0.4],   # e2
        [0.0, 0.4, 0.2],   # e3
    ]
    이렇게 있으면, 
    np.array(embeddings) 하면
    [[0.1, 0.2, 0.3],
    [0.2, 0.0, 0.4],
    [0.0, 0.4, 0.2]]


    """
    return np.array(embeddings).mean(axis=0).tolist()


def similarity(
    embedding1: Embedding,
    embedding2: Embedding,
    mode: SimilarityMode = SimilarityMode.DEFAULT,
) -> float:
    """ 임베딩 유사도 가져옴 """
    # linalg 은 linear algebra 즉 선형대수의 줄임말임. 선형대수학 관련 함수 모아둔건데, 그 안에 norm은 벡터/행렬의 norm을 계산해주는 함수임.
    if mode == SimilarityMode.EUCLIDEAN:
        # 원래 유클리디언 거리는 작을수록 유사도가 높은건디, 나머지가 다 크면 클수록 좋은거라서 일단 - 써서 크게 만들어~~
        return -float(np.linalg.norm(np.array(embedding1) - np.array(embedding2)))
    elif mode == SimilarityMode.DOT_PRODUCT:
        return np.dot(embedding1, embedding2)
    else:
        product = np.dot(embedding1, embedding2)
        norm = np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        return product / norm

"""
TransformComponent -> 노드들을 변환하는 컴포턴트 공통 인터페이스. 결국 임베딩도 노드를 받는다.
DispatcherSpanMixin -> 어디서 시간/비용/에러가 발생했는지 모니터링하는 것
"""

"""
Node 는?
문서를 쪼갠 chunk를 아래가 포함된 객체로 감싼 것.
- text : 실제내용
- metadata: 파일명, 페이지 번호, 섹션 제목, 태그 등
- embedding: 그 조각의 벡터 표현
"""
"""
span은?
- 분산 트레이싱에서 쓰는 로그 쓰려고 쓰는 단위
- 원래는 텍스트로 로그 쓰는데 span으로 하면 span안에 child span(부모 자식 관계)이 있어서 내용을 더 볼 수 있음
- HTML의 span같은 꼴인 듯!
"""
class BaseEmbedding(TransformComponent, DispatcherSpanMixin):
    """ 임베딩을 위한 베이스 클래스~~"""

    model_config = ConfigDict(
        protected_namespaces=("pydantic_model_",), arbitrary_types_allowed=True
    )
    model_name: str = Field(
        default="unknown", description="The name of the embedding model."
    )
    embed_batch_size: int = Field(
        default=DEFAULT_EMBED_BATCH_SIZE,
        description="The batch size for embedding calls.",
        gt=0,
        le=2048,
    )

    # LlamaIndex 내부에서 일어나는 이벤트들 추적용
    callback_manager: CallbackManager = Field(
        default_factory=lambda: CallbackManager([]), exclude=True
    )
    num_workers: Optional[int] = Field(
        default=None,
        description="The number of workers to use for async embedding calls.",
    )
    # Use Any to avoid import loops
    embeddings_cache: Optional[Any] = Field(
        default=None,
        description="Cache for the embeddings: if None, the embeddings are not cached",
    )

    @model_validator(mode="after")
    def check_base_mbeddings_class(self) -> Self:
        # BaseKVStore는 LlamaIndex에서 정의한 키-값 저장소 인터페이스임! 이건 나중에 Redis나 이런것들이 될 수 있겠지.
        from llama_index.core.storage.kvstore.types import BaseKVStore # 모듈 import 시점에는 아직 안 가져오고, 함수가 호출될 때 늦게 가져오니까 순환 참조를 피할 수 있음. 이래서 함수안에서 호출하는군.
        

        if self.callback_manager is None:
            self.callback_manager = CallbackManager([])
        if self.embeddings_cache is not None and not isinstance(
            self.embeddings_cache, BaseKVStore
        ):
            raise TypeError("embeddings_cache must be of type BaseKVStore")
        return self # 이렇게 self를 리턴하면 이 함수안에서 자기 자신을 수정하고, 수정된 나(self)를 다시 돌려주는 거임
    
    @abstractmethod
    def _get_query_embedding(self, query: str) -> Embedding:
        """쿼리 임베딩하는거~ 이거는 코어로직이 될거임"""

    @abstractmethod
    async def _aget_query_embedding(self, query: str) -> Embedding:
        """쿼리 임베딩하는거 비동기~~ 이거도 비동기 코어로직이 될거임."""

    @dispatcher.span # 이 데코레이터는 이거 wrapper로, 외부에 호출 될 때 관측용 span 하나 열어주는 데코레이터임.
    def get_query_embedding(self, query:str) -> Embedding:
        """
        _get_query_embedding 에서 코어 로직 만들고,
        실제로는 여기를 통해 호출하게 해서, 캐시, 로깅, 트레이싱 같은 모니터링 이벤트 쌓는거 모아놓는거임~ 올 괜찮은 구존데.
        캐싱된거 있으면 캐시된거 쓰고 그럼.
        """
        model_dict = self.to_dict()
        model_dict.pop("api_key", None)
        dispatcher.event(
            EmbeddingStartEvent(
                model_dict=model_dict,
            )
        )
        with self.callback_manager.event(
            CBEventType.EMBEDDING, payload={EventPayload.SERIALIZED: self.to_dict()}
        ) as event:
            if not self.embeddings_cache:
                query_embedding = self._get_query_embedding(query)
            elif self.embeddings_cache is not None:
                cached_emb = self.embeddings_cache.get(
                    key=query, collection="embeddings"
                )
                if cached_emb is not None:
                    cached_key = next(iter(cached_emb.keys()))
                    query_embedding = cached_emb[cached_key]
                else:
                    query_embedding = self._get_query_embedding(query)
                    self.embeddings_cache.put(
                        key=query,
                        val={str(uuid.uuid4()): query_embedding},
                        collection="embeddings",
                    )
            event.on_end(
                payload={
                    EventPayload.CHUNKS: [query],
                    EventPayload.EMBEDDINGS: [query_embedding],
                },
            )
        dispatcher.event(
            EmbeddingEndEvent(
                chunks=[query],
                embeddings=[query_embedding],
            )
        )
        return query_embedding
    
    @dispatcher.span
    async def aget_query_embedding(self, query: str) -> Embedding:
        # 대충 이것도 비슷한 구조 걍 await 써서 비동기인 것 뿐.
        return []
    
    def get_agg_embedding_from_queries(
        self,
        queries: List[str],
        agg_fn: Optional[Callable[..., Embedding]] = None,
    ) -> Embedding:
        """여러 쿼리들에서 aggregated된 임베딩 가져오깅"""
        # 오 여기서 디폴트인 mean_agg 말고 직접 agg할 수 있구낭
        query_embeddings = [self.get_query_embedding(query) for query in queries]
        agg_fn = agg_fn or mean_agg 
        return agg_fn(query_embeddings)
    

    @abstractmethod
    def _get_text_embedding(self, text: str) -> Embedding:
        """
        텍스트를 임베딩함~~
        """
    
    def _get_text_embeddings(self, texts: List[str]) -> List[Embedding]:
        """
        List[str] 형식의 시퀀스가 들어오면 요거 호출.
        """
        # Default implementation just loops over _get_text_embedding
        return [self._get_text_embedding(text) for text in texts]


    def _get_text_embeddings_cached(self, texts: List[str]) -> List[Embedding]:
        """
        캐시에서 텍스트 임베딩 꺼내오고 아니면 캐싱함
        """
        if self.embeddings_cache is None:
            raise ValueError("embeddings_cache must be defined")

        embeddings: List[Optional[Embedding]] = [None for i in range(len(texts))]
        # Tuples of (index, text) to be able to keep same order of embeddings
        non_cached_texts: List[Tuple[int, str]] = []
        for i, txt in enumerate(texts):
            cached_emb = self.embeddings_cache.get(key=txt, collection="embeddings")
            if cached_emb is not None:
                cached_key = next(iter(cached_emb.keys()))
                embeddings[i] = cached_emb[cached_key]
            else:
                non_cached_texts.append((i, txt))
        if len(non_cached_texts) > 0:
            text_embeddings = self._get_text_embeddings(
                [x[1] for x in non_cached_texts]
            )
            for j, text_embedding in enumerate(text_embeddings):
                orig_i = non_cached_texts[j][0]
                embeddings[orig_i] = text_embedding

                self.embeddings_cache.put(
                    key=texts[orig_i],
                    val={str(uuid.uuid4()): text_embedding},
                    collection="embeddings",
                )
        return cast(List[Embedding], embeddings)
    

    # 텍스트 임베딩하는 것도 위 구조처럼 @dispatcher.span 쓰고 호출 함수 안에서 이벤트 로깅같은거 처리함. 대충 텍스트 배치하는 것도 같은 형식으로 진행돼서 걍 넘어감

    def similarity(
        self,
        embedding1: Embedding,
        embedding2: Embedding,
        mode: SimilarityMode = SimilarityMode.DEFAULT,
    ) -> float:
        """유사성 찾기~~ 추상 클래스는 호출 함수를 이렇게 다 따로 두는 형식으로 하는군. 편하겄어.."""
        return similarity(embedding1=embedding1, embedding2=embedding2, mode=mode)

    def __call__(self, nodes: Sequence[BaseNode], **kwargs: Any) -> Sequence[BaseNode]:
        # 노드들에서 임베딩용 텍스트를 뽑고~
        # get_text_embedding_batch 로 한 번에 임베딩 계산하고~
        # 각 노드의 node.embedding에 벡터를 넣어주고
        # 그 노드 리스트를 반환
        embeddings = self.get_text_embedding_batch(
            [node.get_content(metadata_mode=MetadataMode.EMBED) for node in nodes],
            **kwargs,
        )

        for node, embedding in zip(nodes, embeddings):
            node.embedding = embedding

        return nodes