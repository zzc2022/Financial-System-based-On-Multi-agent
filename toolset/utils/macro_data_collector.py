# macro_data_collector.py
import os
import json
import requests
from typing import Dict, List, Any, Optional
from .search_engine import SearchEngine
import time
import random

class MacroDataCollector:
    """宏观经济数据收集器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.macro_dir = os.path.join(data_dir, "macro")
        self.search_engine = SearchEngine(engine="sogou")  # 默认使用搜狗搜索引擎
        os.makedirs(self.macro_dir, exist_ok=True)
        
    def get_gdp_data(self, country: str = "中国") -> Dict[str, Any]:
        """获取GDP数据"""
        try:
            search_queries = [
                f"{country} GDP 国内生产总值 2023 2024",
                f"{country} GDP增长率 经济增长 季度数据",
                f"{country} GDP构成 三大产业 统计数据"
            ]
            
            results = {}
            for query in search_queries:
                print(f"🔍 搜索GDP数据: {query}")
                search_results = list(self.search_engine.search(query, max_results=5))
                results[query] = search_results
                time.sleep(random.uniform(1, 2))
            
            # 保存结果
            filename = f"{country}_gdp_data.json"
            filepath = os.path.join(self.macro_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            return results
            
        except Exception as e:
            print(f"❌ 获取GDP数据失败: {e}")
            return {}
    
    def get_cpi_data(self, country: str = "中国") -> Dict[str, Any]:
        """获取CPI数据"""
        try:
            search_queries = [
                f"{country} CPI 消费者价格指数 2023 2024",
                f"{country} 通胀率 物价指数 月度数据",
                f"{country} CPI走势 价格变化 统计局"
            ]
            
            results = {}
            for query in search_queries:
                print(f"🔍 搜索CPI数据: {query}")
                search_results = list(self.search_engine.search(query, max_results=5))
                results[query] = search_results
                time.sleep(random.uniform(1, 2))
            
            # 保存结果
            filename = f"{country}_cpi_data.json"
            filepath = os.path.join(self.macro_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            return results
            
        except Exception as e:
            print(f"❌ 获取CPI数据失败: {e}")
            return {}
    
    def get_interest_rate_data(self, country: str = "中国") -> Dict[str, Any]:
        """获取利率数据"""
        try:
            search_queries = [
                f"{country} 利率 基准利率 央行利率 2023 2024",
                f"{country} 货币政策 利率调整 央行政策",
                f"{country} 市场利率 银行间利率 走势"
            ]
            
            results = {}
            for query in search_queries:
                print(f"🔍 搜索利率数据: {query}")
                search_results = list(self.search_engine.search(query, max_results=5))
                results[query] = search_results
                time.sleep(random.uniform(1, 2))
            
            # 保存结果
            filename = f"{country}_interest_rate_data.json"
            filepath = os.path.join(self.macro_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            return results
            
        except Exception as e:
            print(f"❌ 获取利率数据失败: {e}")
            return {}
    
    def get_exchange_rate_data(self, base_currency: str = "人民币", target_currency: str = "美元") -> Dict[str, Any]:
        """获取汇率数据"""
        try:
            search_queries = [
                f"{base_currency} {target_currency} 汇率 汇率走势 2023 2024",
                f"人民币汇率 美元汇率 央行中间价",
                f"汇率变动 外汇市场 汇率政策"
            ]
            
            results = {}
            for query in search_queries:
                print(f"🔍 搜索汇率数据: {query}")
                search_results = list(self.search_engine.search(query, max_results=5))
                results[query] = search_results
                time.sleep(random.uniform(1, 2))
            
            # 保存结果
            filename = f"exchange_rate.json"
            filepath = os.path.join(self.macro_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            return results
            
        except Exception as e:
            print(f"❌ 获取汇率数据失败: {e}")
            return {}
    
    def get_federal_reserve_data(self) -> Dict[str, Any]:
        """获取美联储利率数据"""
        try:
            search_queries = [
                "美联储 联邦基金利率 加息 降息 2023 2024",
                "Fed 货币政策 利率决议 美联储会议",
                "美国利率 联邦储备 利率变动 影响"
            ]
            
            results = {}
            for query in search_queries:
                print(f"🔍 搜索美联储数据: {query}")
                search_results = list(self.search_engine.search(query, max_results=5))
                results[query] = search_results
                time.sleep(random.uniform(1, 2))
            
            # 保存结果
            filename = "fed_interest_rate_data.json"
            filepath = os.path.join(self.macro_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            return results
            
        except Exception as e:
            print(f"❌ 获取美联储数据失败: {e}")
            return {}
    
    def get_policy_reports(self, country: str = "中国") -> Dict[str, Any]:
        """获取政策报告"""
        try:
            search_queries = [
                f"{country} 政府工作报告 经济政策 2023 2024",
                f"{country} 财政政策 货币政策 宏观调控",
                f"{country} 十四五规划 经济发展 政策文件"
            ]
            
            results = {}
            for query in search_queries:
                print(f"🔍 搜索政策报告: {query}")
                search_results = list(self.search_engine.search(query, max_results=5))
                results[query] = search_results
                time.sleep(random.uniform(1, 2))
            
            # 保存结果
            filename = f"{country}_policy_reports.json"
            filepath = os.path.join(self.macro_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            return results
            
        except Exception as e:
            print(f"❌ 获取政策报告失败: {e}")
            return {}
    
    def get_industry_policy_impact(self, industry_name: str) -> Dict[str, Any]:
        """获取同类行业政策影响"""
        try:
            search_queries = [
                f"{industry_name} 政策影响 监管政策 行业政策",
                f"{industry_name} 政策解读 影响分析 监管变化",
                f"{industry_name} 国家政策 发展政策 扶持政策"
            ]
            
            results = {}
            for query in search_queries:
                print(f"🔍 搜索行业政策影响: {query}")
                search_results = list(self.search_engine.search(query, max_results=5))
                results[query] = search_results
                time.sleep(random.uniform(1, 2))
            
            # 保存结果
            filename = "policy_impact.json"
            filepath = os.path.join(self.macro_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            return results
            
        except Exception as e:
            print(f"❌ 获取行业政策影响失败: {e}")
            return {}