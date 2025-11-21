
from typing import List
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.instrumentation import DispatcherSpanMixin
from llama_index.core.schema import BaseNode, MetadataMode, TransformComponent

# TODO: change to numpy array 라고 함. 오잉 numpy말고 list로 쓰고있었구나??
Embedding = List[float]

dispatcher = instrument.get_dispatcher(__name__) # 관찰용

class SimilarityMode(str, Enum):
    """similarity/distance 를 위한 노드들"""
    DEFAULT = 'cosine' # 각도 기반
    DOT_PRODUCT = 'dot_product' # 각도 + 길이(크기) 기반
    EUCLIDEAN = 'euclidean' # 거리 기반


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