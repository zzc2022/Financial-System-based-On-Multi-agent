#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Qwen API配置
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_qwen_api_config():
    """测试Qwen API配置"""
    print("=== 测试Qwen API配置 ===")
    
    # 检查API密钥
    api_key = os.getenv("QWEN_API_KEY")
    if not api_key:
        print("❌ 未设置QWEN_API_KEY环境变量")
        print("请在.env文件中添加：")
        print("QWEN_API_KEY=your_api_key_here")
        return False
    
    print("✅ 找到QWEN_API_KEY")
    
    # 测试API调用
    try:
        import requests
        
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 修正的请求格式 - 兼容OpenAI格式
        data = {
            "model": "text-embedding-v1",
            "input": "测试文本"
        }
        
        print("正在测试API调用...")
        print(f"请求URL: {url}")
        print(f"请求数据: {data}")
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API调用成功！")
            print(f"响应: {result}")
            if "data" in result and len(result["data"]) > 0:
                embedding = result["data"][0]["embedding"]
                print(f"嵌入向量维度: {len(embedding)}")
            else:
                print("❌ 响应格式不符合预期")
            return True
        else:
            print(f"❌ API调用失败，状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

if __name__ == "__main__":
    test_qwen_api_config() 