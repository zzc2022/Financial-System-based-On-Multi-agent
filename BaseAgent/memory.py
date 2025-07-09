import os
import json
import glob
from typing import Dict, Any, List, Optional

class AgentMemory:
    """
    多层次记忆系统：
    - short_term_memory: 每次 run 中的上下文缓存
    - long_term_memory: 可持久化的数据（结构化 + 文本）
    - vector_memory: 未来 RAG 支持（向量数据库对接接口预留）
    """
    def __init__(self, data_dir: str, info_dir: str, industry_dir: str, vector_dir: Optional[str] = None):
        self.data_dir = data_dir
        self.info_dir = info_dir
        self.industry_dir = industry_dir
        self.vector_dir = vector_dir or "./data/vectors"

        for d in [data_dir, info_dir, industry_dir, self.vector_dir]:
            os.makedirs(d, exist_ok=True)

        self.short_term_memory: Dict[str, Any] = {}

    # ======== 短期记忆接口 ========
    def read_context(self, key: str) -> Any:
        return self.short_term_memory.get(key, None)

    def write_context(self, key: str, value: Any):
        self.short_term_memory[key] = value

    def all_context(self) -> Dict[str, Any]:
        return self.short_term_memory

    def clear_context(self):
        self.short_term_memory = {}

    # ======== 长期结构化记忆（JSON） ========
    def save_json(self, path: str, data: dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_info(self, name: str, content: dict):
        path = os.path.join(self.info_dir, f"{name}.json")
        self.save_json(path, content)

    def load_info(self, name: str) -> dict:
        path = os.path.join(self.info_dir, f"{name}.json")
        return self.load_json(path)

    def list_infos(self) -> List[str]:
        return glob.glob(os.path.join(self.info_dir, "*.json"))

    # ======== 长期原始文本（如搜索记录） ========
    def save_raw_text(self, name: str, text: str):
        path = os.path.join(self.info_dir, f"{name}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def load_raw_text(self, name: str) -> str:
        path = os.path.join(self.info_dir, f"{name}.txt")
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # ======== 向量记忆预留接口（供未来集成 RAG） ========
    def save_embedding(self, vector_id: str, vector: List[float], metadata: dict):
        """保存向量嵌入（可选：支持 faiss / chroma 集成）"""
        path = os.path.join(self.vector_dir, f"{vector_id}.json")
        data = {"vector": vector, "metadata": metadata}
        self.save_json(path, data)

    def load_embedding(self, vector_id: str) -> Optional[dict]:
        path = os.path.join(self.vector_dir, f"{vector_id}.json")
        if os.path.exists(path):
            return self.load_json(path)
        return None
