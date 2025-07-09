

# # 示例：搜索中文文本
# from duckduckgo_search import DDGS


# results2 = DDGS().text(
#     keywords="百度的行业地位",  # 输入中文查询词
#     region="cn-zh",           # 指定中国-中文区域
#     max_results=10
# )
# print("搜索结果：")
# print(results2)

from duckduckgo_search import DDGS
import json
import os
import time
from typing import List

def search_industry_info(companies: List[str], max_results) -> str:
        """
        搜索行业相关信息
        
        Args:
            companies (List[str]): 需要搜索的公司名称列表
            
        Returns:
            str: 搜索结果保存的JSON文件路径
                搜索内容包括行业地位、市场份额、竞争分析、业务模式等
        """
        all_results = {}
        for name in companies:
            keywords = f"{name} 行业地位 市场份额 竞争分析 业务模式"
            try:
                print(f"🔍 搜索: {keywords}")
                results = DDGS().text(keywords=keywords, region="cn-zh", max_results=max_results)
                all_results[name] = results
                import random
                time.sleep(random.randint(20, 35))  # 随机延时，避免请求过快
            except Exception as e:
                print(f"搜索失败: {e}")
        # result_path = os.path.join(self.industry_dir, "all_search_results.json")
        # with open(result_path, 'w', encoding='utf-8') as f:
        #     json.dump(all_results, f, ensure_ascii=False, indent=2)
        # return result_path
        return results