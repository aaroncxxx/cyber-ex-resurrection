#!/usr/bin/env python3
"""
RAG 知识库 — 聊天记录向量化 + 检索增强生成
轻量级实现：TF-IDF 向量化 + 余弦相似度检索
可选升级：chromadb / sentence-transformers
"""

import json
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class Document:
    """文档块"""
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    embedding: list = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata,
        }


class TFIDFVectorStore:
    """TF-IDF 向量存储 — 纯 Python 实现，无需外部依赖"""

    def __init__(self):
        self.documents: list[Document] = []
        self.idf: dict[str, float] = {}
        self.vocabulary: dict[str, int] = {}
        self._idf_computed = False

    def add(self, doc: Document):
        """添加文档"""
        self.documents.append(doc)
        self._idf_computed = False

    def add_batch(self, docs: list[Document]):
        """批量添加"""
        self.documents.extend(docs)
        self._idf_computed = False

    def _tokenize(self, text: str) -> list[str]:
        """中文分词 — 正向最大匹配 + unigram"""
        text = text.lower()
        # 提取中文 unigram + 英文单词
        tokens = []
        # 中文字符（unigram）
        chinese = re.findall(r'[\u4e00-\u9fff]', text)
        tokens.extend(chinese)
        # 中文 bigram（提升短语匹配）
        for i in range(len(chinese) - 1):
            tokens.append(chinese[i] + chinese[i + 1])
        # 英文单词
        english = re.findall(r'[a-zA-Z]+', text)
        tokens.extend(english)
        # 数字
        numbers = re.findall(r'\d+', text)
        tokens.extend(numbers)
        return tokens

    def _compute_idf(self):
        """计算 IDF"""
        if self._idf_computed:
            return

        n = len(self.documents)
        if n == 0:
            return

        df = defaultdict(int)
        all_tokens = set()

        for doc in self.documents:
            tokens = set(self._tokenize(doc.text))
            for token in tokens:
                df[token] += 1
                all_tokens.add(token)

        # 构建词汇表
        self.vocabulary = {token: idx for idx, token in enumerate(sorted(all_tokens))}

        # IDF: log(N / df)
        self.idf = {}
        for token, count in df.items():
            self.idf[token] = math.log(n / (count + 1)) + 1

        self._idf_computed = True

    def _vectorize(self, text: str) -> dict[int, float]:
        """文本 → TF-IDF 向量"""
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        total = len(tokens) or 1

        vector = {}
        for token, count in tf.items():
            if token in self.vocabulary and token in self.idf:
                idx = self.vocabulary[token]
                tfidf = (count / total) * self.idf[token]
                vector[idx] = tfidf

        return vector

    def _cosine_similarity(self, a: dict[int, float], b: dict[int, float]) -> float:
        """余弦相似度"""
        common_keys = set(a.keys()) & set(b.keys())
        if not common_keys:
            return 0.0

        dot = sum(a[k] * b[k] for k in common_keys)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def search(self, query: str, top_k: int = 5, min_score: float = 0.01) -> list[Document]:
        """检索最相关文档"""
        self._compute_idf()

        if not self.documents:
            return []

        query_vec = self._vectorize(query)
        if not query_vec:
            return []

        scored = []
        for doc in self.documents:
            doc_vec = self._vectorize(doc.text)
            score = self._cosine_similarity(query_vec, doc_vec)
            if score >= min_score:
                doc.score = score
                scored.append(doc)

        scored.sort(key=lambda d: d.score, reverse=True)
        return scored[:top_k]

    def save(self, path: Path):
        """保存到文件"""
        data = {
            "documents": [d.to_dict() for d in self.documents],
            "vocabulary": self.vocabulary,
            "idf": {k: v for k, v in self.idf.items()},
            "saved_at": time.time(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: Path):
        """从文件加载"""
        if not path.exists():
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.documents = []
        for d in data.get("documents", []):
            self.documents.append(Document(
                id=d["id"], text=d["text"], metadata=d.get("metadata", {})
            ))
        self.vocabulary = data.get("vocabulary", {})
        self.idf = data.get("idf", {})
        self._idf_computed = True

    def stats(self) -> dict:
        return {
            "documents": len(self.documents),
            "vocabulary_size": len(self.vocabulary),
        }


class RAGStore:
    """RAG 知识库 — 聊天记录作为知识库"""

    def __init__(self, config: dict, store_dir: str = "data/rag"):
        self.config = config
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self.store = TFIDFVectorStore()
        self.store_path = self.store_dir / "tfidf_store.json"

        # 尝试加载已有数据
        self.store.load(self.store_path)

    def index_chat_messages(self, messages: list[dict], chunk_size: int = 5):
        """
        将聊天记录索引为知识库
        按对话轮次分块，每 chunk_size 轮为一个文档
        """
        console.print(f"[cyan]索引 {len(messages)} 条消息到 RAG 知识库...[/cyan]")

        chunks = []
        current_chunk = []
        current_speakers = set()

        for i, msg in enumerate(messages):
            text = msg.get("text", "")
            role = msg.get("role", "unknown")

            if not text.strip():
                continue

            current_chunk.append(msg)
            current_speakers.add(role)

            # 每 chunk_size 条或切换话题时分块
            if len(current_chunk) >= chunk_size:
                chunk_text = "\n".join(
                    f"{'我' if m.get('role') == 'me' else 'TA'}: {m.get('text', '')}"
                    for m in current_chunk
                )
                doc = Document(
                    id=f"chat_{i}",
                    text=chunk_text,
                    metadata={
                        "type": "chat_chunk",
                        "start_idx": i - len(current_chunk) + 1,
                        "end_idx": i,
                        "speakers": list(current_speakers),
                        "msg_count": len(current_chunk),
                    }
                )
                chunks.append(doc)
                current_chunk = []
                current_speakers = set()

        # 处理剩余
        if current_chunk:
            chunk_text = "\n".join(
                f"{'我' if m.get('role') == 'me' else 'TA'}: {m.get('text', '')}"
                for m in current_chunk
            )
            doc = Document(
                id=f"chat_{len(messages)}",
                text=chunk_text,
                metadata={
                    "type": "chat_chunk",
                    "start_idx": len(messages) - len(current_chunk),
                    "end_idx": len(messages) - 1,
                    "speakers": list(current_speakers),
                    "msg_count": len(current_chunk),
                }
            )
            chunks.append(doc)

        self.store.add_batch(chunks)
        self.store.save(self.store_path)

        console.print(f"[green]✅ 索引完成: {len(chunks)} 个文档块[/green]")
        return len(chunks)

    def index_key_events(self, events: list[str]):
        """索引关键事件"""
        docs = []
        for i, event in enumerate(events):
            docs.append(Document(
                id=f"event_{i}",
                text=event,
                metadata={"type": "key_event", "index": i},
            ))
        self.store.add_batch(docs)
        self.store.save(self.store_path)

    def search(self, query: str, top_k: int = 5) -> list[Document]:
        """检索相关对话"""
        return self.store.search(query, top_k=top_k)

    def search_for_context(self, query: str, top_k: int = 3) -> str:
        """检索并格式化为上下文文本"""
        results = self.search(query, top_k=top_k)
        if not results:
            return ""

        lines = ["## 相关记忆（RAG 检索）\n"]
        for i, doc in enumerate(results, 1):
            score_pct = int(doc.score * 100)
            lines.append(f"【相关度 {score_pct}%】{doc.text}")
            lines.append("")

        return "\n".join(lines)

    def index_persona(self, persona_text: str):
        """索引人格模型内容"""
        # 按段落分块
        paragraphs = [p.strip() for p in persona_text.split("\n\n") if p.strip()]
        docs = []
        for i, para in enumerate(paragraphs):
            if len(para) > 10:  # 跳过太短的段落
                docs.append(Document(
                    id=f"persona_{i}",
                    text=para,
                    metadata={"type": "persona", "index": i},
                ))
        self.store.add_batch(docs)
        self.store.save(self.store_path)

    def get_stats(self) -> dict:
        """知识库统计"""
        stats = self.store.stats()
        doc_types = Counter()
        for doc in self.store.documents:
            doc_type = doc.metadata.get("type", "unknown")
            doc_types[doc_type] += 1
        stats["document_types"] = dict(doc_types)
        return stats
