"""
RAG (Retrieval-Augmented Generation) knowledge base for ad platform expertise.

Uses in-memory vector search (no external dependencies required).
ChromaDB is optional — falls back to simple cosine similarity on TF-IDF vectors.

Provides:
- Expert knowledge about ad bidding strategies
- Attribution model explanations
- Platform-specific best practices
- Common optimization techniques

Usage:
    from backend.services.rag_service import RagService
    rag = RagService()
    results = rag.search("如何提高ROAS", top_k=3)
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Knowledge Base ──────────────────────────────────────────────────────

KNOWLEDGE_DOCS: list[dict[str, str]] = [
    # ── Bidding Strategies ──────────────────────────────────────────────
    {
        "id": "bid_001",
        "category": "出价策略",
        "title": "最大化转化 (Max Conversions)",
        "content": """
最大化转化策略会在日预算范围内自动优化出价，争取获得最多的转化量。
适用场景：预算有限但希望最大化转化数量的广告主。
工作原理：系统使用机器学习预测每次展示的转化概率，对高转化概率的展示提高出价。
建议：设置合理的日预算，配合转化追踪使用。初期建议预算不低于目标CPA的10倍。
        """.strip(),
    },
    {
        "id": "bid_002",
        "category": "出价策略",
        "title": "目标CPA (Target CPA)",
        "content": """
目标CPA策略会自动设置出价，在控制每次转化成本不超过目标值的前提下争取更多转化。
适用场景：有明确转化成本目标的广告主。
工作原理：系统根据历史转化数据和实时信号动态调整出价。
注意：实际CPA可能波动10-20%。设置过低的目标CPA可能导致流量不足。
建议：初始目标CPA设置为历史平均CPA的1.1倍，稳定后再逐步降低。
        """.strip(),
    },
    {
        "id": "bid_003",
        "category": "出价策略",
        "title": "目标ROAS (Target ROAS)",
        "content": """
目标ROAS策略以广告支出回报率为核心指标，自动出价以实现目标ROAS。
适用场景：电商、游戏等注重投资回报率的行业。
工作原理：系统预测每次展示的转化价值，计算预期ROAS后出价。
门槛：需要设置转化价值，且过去30天至少有15次转化。
建议：目标ROAS设置为历史ROAS的80-90%作为起点，逐步提升至目标值。
        """.strip(),
    },
    {
        "id": "bid_004",
        "category": "出价策略",
        "title": "增强CPC (Enhanced CPC)",
        "content": """
增强CPC在手动出价基础上，对高转化概率的展示自动提高出价（最高可超出手动出价30%）。
适用场景：希望保持手动控制的广告主，同时获得一定程度的自动优化。
工作原理：半自动策略——基准出价由你设定，系统在此基础上做微调。
建议：适合从手动CPC过渡到全自动策略的中间阶段。
        """.strip(),
    },

    # ── Attribution ─────────────────────────────────────────────────────
    {
        "id": "att_001",
        "category": "归因模型",
        "title": "归因模型选择指南",
        "content": """
归因模型决定了转化功劳如何在广告触点之间分配：
- 末次点击 (Last Touch)：100%归因给最后一次点击。适合决策周期短的行业。
- 首次点击 (First Touch)：100%归因给首次点击。适合品牌认知类广告。
- 线性 (Linear)：所有触点平均分配。适合长期决策周期的B2B行业。
- 时间衰减 (Time Decay)：越近的触点权重越高。适合促销类活动。
- 位置基础 (Position Based)：首尾各40%，中间触点平分20%。适合多渠道组合投放。
- 数据驱动 (Data-Driven)：基于Shapley值计算每个触点的边际贡献。最准确但需要大量数据。
建议：初始使用末次点击快速上线，积累数据后切换到数据驱动模型。
        """.strip(),
    },

    # ── Optimization ────────────────────────────────────────────────────
    {
        "id": "opt_001",
        "category": "优化技巧",
        "title": "CTR提升策略",
        "content": """
提高点击率(CTR)的五大方法：
1. A/B测试标题：测试3-5个不同的广告标题，每2周更新效果最差的变体。
2. 受众细化：定位CTR>2%的高表现受众分组，排除低CTR受众。
3. 创意轮换：疲劳度>60的创意降低展示频率，增加新鲜素材。
4. 行动号召优化：使用紧迫感词汇（限时/抢购/今日特价）可提升CTR 15-25%。
5. 设备优化：移动端标题不超过20字，桌面端不超过30字。
        """.strip(),
    },
    {
        "id": "opt_002",
        "category": "优化技巧",
        "title": "ROAS优化最佳实践",
        "content": """
提升ROAS的七个步骤：
1. 切换到目标ROAS出价策略，设置目标为历史ROAS的85%
2. 暂停ROAS<1.0超过7天的广告活动
3. 将预算从低ROAS平台转移到高ROAS平台（差距>1.0x时执行）
4. 检查转化追踪是否完整——丢失20%以上的转化数据会严重拉低ROAS
5. 优化落地页加载速度——加载时间每增加1秒，转化率下降7%
6. 使用数据驱动归因替代末次点击——通常会提升ROAS 10-20%
7. 设置自动规则：花费>预算×2且ROAS<1.5时暂停活动
        """.strip(),
    },
    {
        "id": "opt_003",
        "category": "优化技巧",
        "title": "预算分配策略",
        "content": """
广告预算分配最佳实践：
1. 70-20-10法则：70%预算给已验证的高ROAS活动，20%给测试中活动，10%给全新实验。
2. 时段分配：高峰时段(10-12,19-22)分配50-60%预算，其余时段均匀。
3. 跨平台分配：按各平台历史ROAS比例分配，ROAS最高的平台获得最多预算。
4. 预算上限：单个活动日预算不超过总预算的40%，避免过度集中风险。
5. 预留缓冲：保留10%预算用于应对突发机会或竞争对手活动。
        """.strip(),
    },

    # ── Platform-specific ────────────────────────────────────────────────
    {
        "id": "plat_001",
        "category": "平台指南",
        "title": "Google Ads 投放要点",
        "content": """
Google Ads优化要点：
- 搜索广告：关键词匹配类型从广泛匹配开始，收集数据后逐步收窄到词组/精确匹配
- 展示广告：使用自定义受众+再营销列表，排除已转化用户
- 购物广告：优化产品标题包含核心关键词，价格竞争力影响排名
- 质量得分：CTR×广告相关性×落地页体验，得分>7为优
- 建议出价：增强CPC配合目标CPA，适合大多数电商场景
        """.strip(),
    },
    {
        "id": "plat_002",
        "category": "平台指南",
        "title": "Meta Ads (Facebook/Instagram) 优化",
        "content": """
Meta Ads投放要点：
- 受众：利用Lookalike受众扩展核心客户（1-3%相似度效果最佳）
- 创意：视频广告CPM通常比图片低30-50%，3-15秒短视频效果最好
- 版位：初期使用自动版位，收集数据后手动优化
- 转化API：务必配置Conversion API(转化API)弥补浏览器端pixel的数据丢失(约15-20%)
- 频次控制：同一用户每周展示不超过3次，避免广告疲劳
        """.strip(),
    },

    # ── Experimentation ──────────────────────────────────────────────────
    {
        "id": "exp_001",
        "category": "实验方法",
        "title": "A/B测试设计原则",
        "content": """
广告A/B测试最佳实践：
1. 每次只测试一个变量（出价策略/创意/受众），避免混淆效果。
2. 样本量计算：每组至少需要500次展示才能检测到5%的差异（80%统计功效）。
3. 测试周期：至少运行7天覆盖完整周循环，避免单日波动误导。
4. 流量分配：初期50/50均分，结果显著后可调整为80/20（胜者/败者）。
5. 置信度阈值：95%置信度(p<0.05)可判定显著，90%可视为趋势。
6. 贝叶斯方法：比频率派方法收敛更快，适合快速迭代场景。
7. 自动停止：达到显著性且样本量足够时自动结束实验，避免浪费预算。
        """.strip(),
    },
]


# ── In-Memory TF-IDF Vector Search ──────────────────────────────────────

class RagService:
    """Lightweight RAG using TF-IDF + cosine similarity. Zero external deps."""

    def __init__(self):
        self._docs = KNOWLEDGE_DOCS
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._doc_vectors: list[np.ndarray] = []
        self._build_index()

    def _tokenize(self, text: str) -> list[str]:
        """Simple Chinese + English tokenizer."""
        # Split Chinese by extracting continuous CJK sequences, English by word boundaries
        tokens: list[str] = []
        # Chinese: split by non-CJK, keep each CJK char pair
        cjk = re.findall(r'[\u4e00-\u9fff]{1,2}', text)
        tokens.extend(cjk)
        # English: lowercase and split
        eng = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend(eng)
        # Numbers
        nums = re.findall(r'\d+\.?\d*', text)
        tokens.extend(nums)
        return tokens

    def _build_index(self) -> None:
        """Build TF-IDF index from knowledge documents."""
        # Tokenize all docs
        doc_tokens = [self._tokenize(d["title"] + " " + d["content"]) for d in self._docs]

        # Build vocabulary
        vocab_set: set[str] = set()
        for tokens in doc_tokens:
            vocab_set.update(tokens)
        self._vocab = {word: i for i, word in enumerate(sorted(vocab_set))}

        # Compute TF
        N = len(self._docs)
        tf_matrix = np.zeros((N, len(self._vocab)))
        for i, tokens in enumerate(doc_tokens):
            for token in tokens:
                if token in self._vocab:
                    tf_matrix[i, self._vocab[token]] += 1
            # Normalize TF by doc length
            row_sum = tf_matrix[i].sum()
            if row_sum > 0:
                tf_matrix[i] /= row_sum

        # Compute IDF
        df = np.sum(tf_matrix > 0, axis=0)
        self._idf = {
            word: np.log((N + 1) / (df[idx] + 1)) + 1
            for word, idx in self._vocab.items()
        }

        # Compute TF-IDF vectors
        self._doc_vectors = []
        for i in range(N):
            vec = np.zeros(len(self._vocab))
            for word, idx in self._vocab.items():
                vec[idx] = tf_matrix[i, idx] * self._idf.get(word, 0)
            # Normalize
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            self._doc_vectors.append(vec)

    def search(self, query: str, top_k: int = 3, category: str | None = None) -> list[dict[str, Any]]:
        """Search knowledge base and return top-K results.

        Returns list of {id, category, title, content, score}.
        """
        # Build query vector
        query_tokens = self._tokenize(query)
        query_vec = np.zeros(len(self._vocab))
        for token in query_tokens:
            if token in self._vocab:
                tf = query_tokens.count(token) / max(len(query_tokens), 1)
                query_vec[self._vocab[token]] = tf * self._idf.get(token, 0)
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec /= norm

        # Compute similarities
        scores: list[tuple[int, float]] = []
        for i, doc_vec in enumerate(self._doc_vectors):
            if category and self._docs[i]["category"] != category:
                continue
            sim = float(np.dot(query_vec, doc_vec))
            if sim > 0.01:  # minimum relevance threshold
                scores.append((i, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[:top_k]

        return [
            {
                "id": self._docs[i]["id"],
                "category": self._docs[i]["category"],
                "title": self._docs[i]["title"],
                "content": self._docs[i]["content"],
                "score": round(score, 4),
            }
            for i, score in top
        ]

    def get_categories(self) -> list[str]:
        """Get all knowledge categories."""
        return sorted(set(d["category"] for d in self._docs))

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        return {
            "total_documents": len(self._docs),
            "categories": self.get_categories(),
            "vocabulary_size": len(self._vocab),
        }


# ── Singleton ───────────────────────────────────────────────────────────
_rag_service: RagService | None = None


def get_rag_service() -> RagService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
