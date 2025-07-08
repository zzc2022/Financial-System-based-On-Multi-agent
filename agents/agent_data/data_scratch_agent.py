# agents/data_agent.py

import os
import time
import json
import glob
from typing import List, Dict, Tuple

from .utils.get_shareholder_info import get_shareholder_info, get_table_content
from .utils.get_financial_statements import get_all_financial_statements, save_financial_statements_to_csv
from .utils.identify_competitors import identify_competitors_with_ai
from .utils.get_stock_intro import get_stock_intro, save_stock_intro_to_txt

from duckduckgo_search import DDGS
from utils.llm_helper import LLMHelper
from config.llm_config import LLMConfig


class DataAgent:
    def __init__(self, target_company: str, target_code: str, target_market: str, 
                 data_dir: str = "./data/download_financial_statement_files", 
                 info_dir: str = "./data/company_info",
                 industry_dir: str = "./data/industry_info",
                 llm_config: LLMConfig = None):
        """
        初始化数据采集代理
        
        Args:
            target_company (str): 目标公司名称
            target_code (str): 目标公司股票代码
            target_market (str): 目标公司所在市场（如A股、港股等）
            data_dir (str): 财务报表数据存储目录
            info_dir (str): 公司信息存储目录
            industry_dir (str): 行业信息存储目录
            llm_config (LLMConfig): LLM配置对象
        """
        self.target_company = target_company
        self.target_code = target_code
        self.target_market = target_market
        self.data_dir = data_dir
        self.info_dir = info_dir
        self.industry_dir = industry_dir
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.info_dir, exist_ok=True)
        os.makedirs(self.industry_dir, exist_ok=True)

        self.llm_config = llm_config
        self.llm = LLMHelper(self.llm_config)

    def get_competitor_listed_companies(self) -> List[Dict]:
        """
        获取目标公司的竞争对手上市公司列表
        
        Returns:
            List[Dict]: 竞争对手公司信息列表，每个字典包含name、code、market等字段
                       过滤掉未上市的公司
        """
        competitors = identify_competitors_with_ai(
            api_key=self.llm_config.api_key,
            base_url=self.llm_config.base_url,
            model_name=self.llm_config.model,
            company_name=self.target_company
        )
        return [c for c in competitors if c.get('market') != "未上市"]

    def get_all_financial_data(self, listed_companies: List[Dict]) -> Dict[str, List[Dict]]:
        """
        获取目标公司及其竞争对手的财务数据
        
        Args:
            listed_companies (List[Dict]): 竞争对手公司信息列表
            
        Returns:
            Dict[str, List[Dict]]: 竞争对手公司的财务数据字典，键为公司名称，值为财务数据列表
                                  目标公司的财务数据会保存到文件但不返回
        """
        def _parse_market( market_str: str, code: str) -> str:
            """
            解析市场信息并格式化股票代码
            
            Args:
                market_str (str): 市场描述字符串（如"A股"、"港股"等）
                code (str): 原始股票代码
                
            Returns:
                Tuple[str, str]: 解析后的市场代码和格式化的股票代码
                            - A股：返回("A", "SH000001"或"SZ000001"格式)
                            - 港股：返回("HK", 原代码)
            """
            if "A" in market_str:
                market = "A"
                if not code.startswith("SH") and not code.startswith("SZ"):
                    code = "SH" + code if code.startswith("6") else "SZ" + code
                return market, code
            elif "港" in market_str:
                market = "HK"
                return market, code

        # 目标公司
        target_financials = get_all_financial_statements(self.target_code, self.target_market, period="年度")
        save_financial_statements_to_csv(target_financials, self.target_code, self.target_market,
                                         self.target_company, "年度", self.data_dir)

        # 竞争对手
        competitors_data = {}
        for c in listed_companies:
            name, code, market = c['name'], c['code'], c['market']
            market, company_code = _parse_market(market, code)
            print(f"获取：{name}({market}:{company_code})")
            try:
                data = get_all_financial_statements(company_code, market, "年度")
                save_financial_statements_to_csv(data, company_code, market, name, "年度", self.data_dir)
                competitors_data[name] = data
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ 获取失败: {e}")
        return competitors_data

    def get_all_company_info(self, companies: List[Tuple[str, str, str]]) -> str:
        """
        获取所有公司的基础信息
        
        Args:
            companies (List[Tuple[str, str, str]]): 公司信息元组列表，格式为(公司名称, 股票代码, 市场)
            
        Returns:
            str: 合并后的所有公司信息文本，包含格式化的公司介绍
                如果获取失败则返回"未获取到公司基础信息"
        """
        merged_info = ""
        for name, code, market in companies:
            try:
                info = get_stock_intro(code, market)
                if info:
                    merged_info += f"【公司信息开始】\n公司名称: {name}\n{info}\n【公司信息结束】\n\n"
                    save_stock_intro_to_txt(code, market, os.path.join(self.info_dir, f"{name}_{market}_{code}_info.txt"))
            except Exception as e:
                print(f"获取 {name} 信息失败: {e}")
            time.sleep(1)
        return merged_info or "未获取到公司基础信息"

    def get_shareholder_analysis(self) -> str:
        """
        获取并分析股东信息
        
        Returns:
            str: LLM分析后的股东信息分析结果
                如果获取失败则返回错误信息
        """
        try:
            info = get_shareholder_info()
            if info['success'] and info.get("tables"):
                table_content = get_table_content(info.get("tables"))
                analysis = self.llm.call(
                    "请分析以下股东信息表格内容：\n" + table_content,
                    system_prompt="你是一个专业的股东信息分析师。"
                )
                return analysis
            return f"股东信息获取失败: {info.get('error', '未知错误')}"
        except Exception as e:
            return f"股东信息获取失败: {e}"

    def search_industry_info(self, companies: List[str]) -> str:
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
                results = DDGS().text(keywords=keywords, region="cn-zh", max_results=10)
                all_results[name] = results
                import random
                time.sleep(random.randint(20, 35))  # 随机延时，避免请求过快
            except Exception as e:
                print(f"搜索失败: {e}")
        result_path = os.path.join(self.industry_dir, "all_search_results.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        return result_path

    def collect_company_file_paths(self) -> Dict[str, List[str]]:
        """
        收集公司财务数据文件路径
        
        Returns:
            Dict[str, List[str]]: 公司文件路径字典，键为公司名称，值为该公司相关的CSV文件路径列表
                                 通过文件名前缀识别归属公司
        """
        files = glob.glob(os.path.join(self.data_dir, "*.csv"))
        company_files = {}
        for file in files:
            name = os.path.basename(file).split("_")[0]
            company_files.setdefault(name, []).append(file)
        return company_files
