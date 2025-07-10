# memory.py
import os
import json
import glob
import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta

class AgentMemory:
    """
    混合记忆系统：
    - 临时缓存：快速访问，自动过期
    - 长期记忆：持久化存储，结构化数据
    - 上下文记忆：当前会话状态
    - 向量记忆：语义搜索支持
    """
    def __init__(self, data_dir: str, info_dir: str, industry_dir: str, 
                 embedding_model: Optional[Any] = None, vector_dir: Optional[str] = None):
        self.data_dir = data_dir
        self.info_dir = info_dir
        self.industry_dir = industry_dir
        self.vector_dir = vector_dir or os.path.join(data_dir, "vectors")
        
        # 创建目录
        for d in [data_dir, info_dir, industry_dir, self.vector_dir]:
            os.makedirs(d, exist_ok=True)
        
        # 临时缓存 (内存)
        self.temp_cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_ttl = 3600  # 1小时默认TTL
        
        # 上下文记忆 (当前会话)
        self.context_memory: Dict[str, Any] = {}
        
        # 向量记忆
        self.embedding_model = embedding_model
        self.vector_memory: Dict[str, np.ndarray] = {}
        self.vector_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 加载持久化数据
        self._load_persistent_data()
        self._load_vector_data()

    def _load_persistent_data(self):
        """加载持久化数据到内存"""
        self.persistent_data = {}
        for file_path in glob.glob(os.path.join(self.info_dir, "*.json")):
            key = os.path.splitext(os.path.basename(file_path))[0]
            try:
                self.persistent_data[key] = self.load_json(file_path)
            except:
                continue

    def _load_vector_data(self):
        """加载向量数据"""
        vector_file = os.path.join(self.vector_dir, "vectors.json")
        metadata_file = os.path.join(self.vector_dir, "metadata.json")
        
        if os.path.exists(vector_file):
            try:
                vector_data = self.load_json(vector_file)
                for key, vector_list in vector_data.items():
                    self.vector_memory[key] = np.array(vector_list)
            except:
                pass
        
        if os.path.exists(metadata_file):
            try:
                self.vector_metadata = self.load_json(metadata_file)
            except:
                pass

    def _save_vector_data(self):
        """保存向量数据"""
        vector_file = os.path.join(self.vector_dir, "vectors.json")
        metadata_file = os.path.join(self.vector_dir, "metadata.json")
        
        # 转换numpy数组为列表以便JSON序列化
        vector_data = {
            key: vector.tolist() 
            for key, vector in self.vector_memory.items()
        }
        
        self.save_json(vector_file, vector_data)
        self.save_json(metadata_file, self.vector_metadata)

    # ======== 向量记忆接口 ========
    def create_embedding(self, text: str) -> Optional[np.ndarray]:
        """创建文本嵌入向量"""
        if self.embedding_model is None:
            return None
        
        try:
            # 支持不同的嵌入模型接口
            if hasattr(self.embedding_model, 'encode'):
                # OpenAI, sentence-transformers 等
                embedding = self.embedding_model.encode(text)
            elif hasattr(self.embedding_model, 'embed_query'):
                # LangChain 兼容
                embedding = self.embedding_model.embed_query(text)
            elif callable(self.embedding_model):
                # 自定义函数
                embedding = self.embedding_model(text)
            else:
                return None
            
            return np.array(embedding)
        except Exception as e:
            print(f"嵌入创建失败: {e}")
            return None

    def save_embedding(self, key: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """保存文本及其嵌入向量"""
        embedding = self.create_embedding(text)
        if embedding is not None:
            self.vector_memory[key] = embedding
            self.vector_metadata[key] = {
                "text": text,
                "created_at": datetime.now().isoformat(),
                **(metadata or {})
            }
            self._save_vector_data()

    def semantic_search(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """语义搜索"""
        if not self.vector_memory or self.embedding_model is None:
            return []
        
        query_embedding = self.create_embedding(query)
        if query_embedding is None:
            return []
        
        results = []
        for key, stored_embedding in self.vector_memory.items():
            # 计算余弦相似度
            similarity = np.dot(query_embedding, stored_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
            )
            
            if similarity >= threshold:
                results.append({
                    "key": key,
                    "similarity": float(similarity),
                    "text": self.vector_metadata[key]["text"],
                    "metadata": self.vector_metadata[key]
                })
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def get_embedding_stats(self) -> Dict[str, Any]:
        """获取向量记忆统计"""
        return {
            "total_embeddings": len(self.vector_memory),
            "embedding_keys": list(self.vector_memory.keys()),
            "has_embedding_model": self.embedding_model is not None
        }

    # ======== 临时缓存接口 ========
    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置临时缓存"""
        expire_time = time.time() + (ttl or self.cache_ttl)
        self.temp_cache[key] = (value, expire_time)

    def cache_get(self, key: str) -> Any:
        """获取临时缓存"""
        if key in self.temp_cache:
            value, expire_time = self.temp_cache[key]
            if time.time() < expire_time:
                return value
            else:
                del self.temp_cache[key]
        return None

    def cache_clear_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expire_time) in self.temp_cache.items()
            if current_time >= expire_time
        ]
        for key in expired_keys:
            del self.temp_cache[key]

    # ======== 上下文记忆接口 ========
    def context_set(self, key: str, value: Any):
        """设置上下文记忆"""
        self.context_memory[key] = value

    def context_get(self, key: str) -> Any:
        """获取上下文记忆"""
        return self.context_memory.get(key)

    def context_clear(self):
        """清空上下文记忆"""
        self.context_memory.clear()

    def context_all(self) -> Dict[str, Any]:
        """获取所有上下文"""
        return self.context_memory.copy()

    # ======== 长期记忆接口 ========
    def save_json(self, path: str, data: dict):
        """保存JSON数据"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, path: str) -> dict:
        """加载JSON数据"""
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_persistent(self, key: str, data: dict):
        """保存到长期记忆"""
        path = os.path.join(self.info_dir, f"{key}.json")
        self.save_json(path, data)
        self.persistent_data[key] = data

    def load_persistent(self, key: str) -> dict:
        """从长期记忆加载"""
        return self.persistent_data.get(key, {})

    def list_persistent_keys(self) -> List[str]:
        """列出所有长期记忆键"""
        return list(self.persistent_data.keys())

    # ======== 智能记忆接口 ========
    def smart_get(self, key: str, default: Any = None) -> Any:
        """
        智能获取：优先从缓存获取，然后上下文，最后长期记忆
        """
        # 1. 检查临时缓存
        cached = self.cache_get(key)
        if cached is not None:
            return cached
        
        # 2. 检查上下文记忆
        context_value = self.context_get(key)
        if context_value is not None:
            return context_value
        
        # 3. 检查长期记忆
        persistent_value = self.load_persistent(key)
        if persistent_value:
            return persistent_value
        
        return default

    def smart_set(self, key: str, value: Any, storage_type: str = "auto"):
        """
        智能设置：根据数据类型和大小自动选择存储位置
        storage_type: "cache", "context", "persistent", "auto"
        """
        if storage_type == "auto":
            # 自动选择存储类型
            if isinstance(value, dict) and len(str(value)) > 1000:
                storage_type = "persistent"
            elif isinstance(value, (str, dict, list)) and len(str(value)) < 500:
                storage_type = "cache"
            else:
                storage_type = "context"
        
        if storage_type == "cache":
            self.cache_set(key, value)
        elif storage_type == "context":
            self.context_set(key, value)
        elif storage_type == "persistent":
            if isinstance(value, dict):
                self.save_persistent(key, value)
            else:
                self.save_persistent(key, {"value": value, "type": type(value).__name__})

    # ======== 记忆统计 ========
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计信息"""
        self.cache_clear_expired()
        return {
            "cache_size": len(self.temp_cache),
            "context_size": len(self.context_memory),
            "persistent_size": len(self.persistent_data),
            "vector_size": len(self.vector_memory),
            "cache_keys": list(self.temp_cache.keys()),
            "context_keys": list(self.context_memory.keys()),
            "persistent_keys": list(self.persistent_data.keys()),
            "vector_keys": list(self.vector_memory.keys()),
            "has_embedding_model": self.embedding_model is not None
        }

    # ======== 向后兼容接口 ========
    def save_info(self, name: str, content: dict):
        """兼容旧接口"""
        self.save_persistent(name, content)

    def load_info(self, name: str) -> dict:
        """兼容旧接口"""
        return self.load_persistent(name)