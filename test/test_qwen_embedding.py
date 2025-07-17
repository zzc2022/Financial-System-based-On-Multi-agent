#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Qwen嵌入模型与记忆系统的集成
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.embedding_config import create_embedding_config
from BaseAgent.memory import AgentMemory

def test_qwen_embedding():
    """测试Qwen嵌入功能"""
    print("=== 测试Qwen嵌入模型 ===")
    
    # 1. 创建嵌入配置
    print("1. 初始化Qwen API嵌入模型...")
    embedding_config = create_embedding_config("qwen")
    embedding_model = embedding_config.get_model()
    
    if not embedding_model:
        print("❌ Qwen模型加载失败")
        return False
    
    print("✅ Qwen模型加载成功")
    
    # 2. 创建记忆系统
    print("\n2. 初始化记忆系统...")
    memory = AgentMemory(
        "./data/financials", 
        "./data/info", 
        "./data/industry", 
        embedding_model
    )
    
    # 3. 测试嵌入创建
    print("\n3. 测试文本嵌入...")
    test_texts = [
        "商汤科技是一家专注于人工智能的公司",
        "腾讯在游戏和社交领域表现突出",
        "阿里巴巴在电商和云计算方面领先"
    ]
    
    for i, text in enumerate(test_texts):
        embedding = memory.create_embedding(text)
        if embedding is not None:
            print(f"✅ 文本{i+1}嵌入成功，维度: {len(embedding)}")
        else:
            print(f"❌ 文本{i+1}嵌入失败")
    
    # 4. 测试向量记忆
    print("\n4. 测试向量记忆存储...")
    for i, text in enumerate(test_texts):
        memory.save_embedding(
            f"test_company_{i+1}", 
            text, 
            {"company_id": i+1, "type": "company_intro"}
        )
        print(f"✅ 保存向量记忆: test_company_{i+1}")
    
    # 5. 测试语义搜索
    print("\n5. 测试语义搜索...")
    search_query = "人工智能公司"
    results = memory.semantic_search(search_query, top_k=3, threshold=0.5)
    
    print(f"搜索查询: '{search_query}'")
    print(f"找到 {len(results)} 个相关结果:")
    
    for i, result in enumerate(results):
        print(f"  {i+1}. 相似度: {result['similarity']:.3f}")
        print(f"     文本: {result['text']}")
        print(f"     键: {result['key']}")
    
    # 6. 查看记忆统计
    print("\n6. 记忆系统统计:")
    stats = memory.get_memory_stats()
    print(f"  向量记忆数量: {stats['vector_size']}")
    print(f"  嵌入模型可用: {stats['has_embedding_model']}")
    
    print("\n✅ Qwen嵌入测试完成!")
    return True

if __name__ == "__main__":
    test_qwen_embedding() 