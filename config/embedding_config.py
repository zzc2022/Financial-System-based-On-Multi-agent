# embedding_config.py
"""
嵌入模型配置
支持多种嵌入模型：OpenAI, sentence-transformers, 自定义等
"""

import os
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

class EmbeddingConfig:
    """嵌入模型配置类"""
    
    def __init__(self, model_type: str = "openai", **kwargs):
        self.model_type = model_type
        self.model = None
        self._setup_model(**kwargs)
    
    def _setup_model(self, **kwargs):
        """设置嵌入模型"""
        if self.model_type == "openai":
            self._setup_openai(**kwargs)
        elif self.model_type == "sentence_transformers":
            self._setup_sentence_transformers(**kwargs)
        elif self.model_type == "qwen":
            self._setup_qwen(**kwargs)
        elif self.model_type == "custom":
            self._setup_custom(**kwargs)
        else:
            print(f"不支持的嵌入模型类型: {self.model_type}")
    
    def _setup_openai(self, **kwargs):
        """设置OpenAI嵌入模型"""
        try:
            from openai import OpenAI
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            base_url = kwargs.get("base_url") or os.getenv("OPENAI_BASE_URL")
            
            if not api_key:
                print("警告: 未设置OPENAI_API_KEY")
                return
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # 创建嵌入函数
            def create_embedding(text: str):
                response = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            
            self.model = create_embedding
            print("✅ OpenAI嵌入模型已加载")
            
        except ImportError:
            print("❌ 请安装openai: pip install openai")
        except Exception as e:
            print(f"❌ OpenAI嵌入模型加载失败: {e}")
    
    def _setup_sentence_transformers(self, **kwargs):
        """设置sentence-transformers嵌入模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = kwargs.get("model_name", "all-MiniLM-L6-v2")
            self.model = SentenceTransformer(model_name)
            print(f"✅ sentence-transformers模型已加载: {model_name}")
            
        except ImportError:
            print("❌ 请安装sentence-transformers: pip install sentence-transformers")
        except Exception as e:
            print(f"❌ sentence-transformers模型加载失败: {e}")
    
    def _setup_qwen(self, **kwargs):
        """设置Qwen API嵌入模型"""
        try:
            import requests
            import json
            
            api_key = kwargs.get("api_key") or os.getenv("QWEN_API_KEY")
            base_url = kwargs.get("base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            
            if not api_key:
                print("❌ 请设置QWEN_API_KEY环境变量")
                return
            
            # 创建嵌入函数
            def create_embedding(text: str):
                url = f"{base_url}/embeddings"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "text-embedding-v1",
                    "input": text
                }
                
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    if "data" in result and len(result["data"]) > 0:
                        return result["data"][0]["embedding"]
                    else:
                        print(f"❌ 意外的API响应格式: {result}")
                        return None
                except Exception as e:
                    print(f"❌ Qwen API调用失败: {e}")
                    return None
            
            self.model = create_embedding
            print("✅ Qwen API嵌入模型已配置")
            
        except ImportError:
            print("❌ 请安装requests: pip install requests")
        except Exception as e:
            print(f"❌ Qwen API配置失败: {e}")
    
    def _setup_custom(self, **kwargs):
        """设置自定义嵌入模型"""
        custom_function = kwargs.get("embedding_function")
        if callable(custom_function):
            self.model = custom_function
            print("✅ 自定义嵌入模型已加载")
        else:
            print("❌ 自定义嵌入函数无效")
    
    def get_model(self) -> Optional[Any]:
        """获取嵌入模型"""
        return self.model

# 便捷函数
def create_embedding_config(model_type: str = "openai", **kwargs) -> EmbeddingConfig:
    """创建嵌入配置"""
    return EmbeddingConfig(model_type, **kwargs)

# 示例用法
if __name__ == "__main__":
    # OpenAI嵌入
    # config = create_embedding_config("openai")
    
    # sentence-transformers嵌入
    # config = create_embedding_config("sentence_transformers", model_name="all-MiniLM-L6-v2")
    
    # Qwen嵌入 (推荐)
    config = create_embedding_config("qwen", model_name="Qwen/Qwen2.5-7B-Instruct")
    
    # 自定义嵌入
    # def my_embedding(text):
    #     # 你的自定义嵌入逻辑
    #     return [0.1, 0.2, 0.3, ...]
    # config = create_embedding_config("custom", embedding_function=my_embedding)
    
    model = config.get_model()
    if model:
        print("嵌入模型可用")
    else:
        print("嵌入模型不可用") 