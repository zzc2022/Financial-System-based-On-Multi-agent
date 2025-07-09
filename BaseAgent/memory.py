# memory.py
import os
import json
import glob
from typing import Any, Dict, List, Union, Optional

class AgentMemory:
    def __init__(self, memory_dir: str = "./memory", vector_db=None):
        self.memory_dir = memory_dir
        self.vector_db = vector_db  # 可选：向量数据库，如 Chroma、FAISS 等
        self.short_term_context: Dict[str, Any] = {}
        os.makedirs(memory_dir, exist_ok=True)

    ### === 短期记忆 === ###
    def get_context(self) -> Dict[str, Any]:
        return self.short_term_context

    def update_context(self, key: str, value: Any):
        self.short_term_context[key] = value

    def clear_context(self):
        self.short_term_context = {}

    ### === 长期记忆（结构化）=== ###
    def save_long_term(self, key: str, content: Union[str, dict]):
        path = os.path.join(self.memory_dir, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    def load_long_term(self, key: str) -> Optional[dict]:
        path = os.path.join(self.memory_dir, f"{key}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_long_term_keys(self) -> List[str]:
        return [os.path.basename(p).replace(".json", "") for p in glob.glob(os.path.join(self.memory_dir, "*.json"))]

    ### === 长期记忆（语义）=== ###
    def search_long_term(self, query: str, top_k: int = 3) -> List[str]:
        if self.vector_db:
            return self.vector_db.search(query, top_k=top_k)
        else:
            print("⚠️ 向量检索模块尚未接入，返回空结果。")
            return []

    def add_to_vector_memory(self, text: str, metadata: Dict[str, Any]):
        if self.vector_db:
            self.vector_db.add_document(text, metadata)
        else:
            print("⚠️ 向量检索模块未启用，未保存。")
