

# 示例：搜索中文文本
from duckduckgo_search import DDGS


results2 = DDGS().text(
    keywords="百度的行业地位",  # 输入中文查询词
    region="cn-zh",           # 指定中国-中文区域
    max_results=10
)
print("搜索结果：")
print(results2)