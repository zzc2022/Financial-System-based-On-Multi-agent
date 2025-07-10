# action_financial.py
from toolset.utils.get_financial_statements import get_all_financial_statements, save_financial_statements_to_csv
from toolset.utils.get_stock_intro import get_stock_intro, save_stock_intro_to_txt
from toolset.utils.get_shareholder_info import get_shareholder_info, get_table_content
from toolset.utils.search_info import search_industry_info
from toolset.utils.identify_competitors import identify_competitors_with_ai
from duckduckgo_search import DDGS
import time, random, os
import json

class FinancialActionToolset:
    def __init__(self, profile, memory, llm, llm_config):
        self.p = profile
        self.m = memory
        self.llm = llm
        self.cfg = llm_config

    def get_competitor_listed_companies(self, context):

        result = identify_competitors_with_ai(
            api_key=self.cfg.api_key,
            base_url=self.cfg.base_url,
            model_name=self.cfg.model,
            company_name=self.p.company
        )
        result = [c for c in result if c.get('market') != "未上市"]
        return result

    def get_all_financial_data(self, context):
        companies = context.get("all_companies", [])
        data_lst = []
        for p in companies:
            try:
                name, code, market = p['name'], p['code'], p['market']
                print(f"获取：{name}({market}:{code})")
                data = get_all_financial_statements(code, market, "年度")
                data_lst.append(data)
                save_financial_statements_to_csv(data, code, market, name, "年度", self.m.data_dir)
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ 获取失败: {e}")
        return data_lst

    def get_all_company_info(self, context):
        def _parse_market( market_str: str, code: str) -> tuple[str, str]:
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
            return market_str, code

        companies = context.get("all_companies", [])
        for c in companies:
            if 'market' in c and 'code' in c:
                market, code = _parse_market(c['market'], c['code'])
                c['market'] = market
                c['code'] = code
        context["all_companies"] = companies

        result = ""
        for item in companies:
            info = get_stock_intro(item['code'], item['market'])
            if info:
                result += info
        return result

    def get_shareholder_analysis(self, context):
        info = get_shareholder_info()
        if info['success']:
            content = get_table_content(info['tables'])
            return self.llm.call("分析以下股东信息：\n" + content, system_prompt="你是股东分析专家")
        return "股东信息获取失败"

    def search_industry_info(self, context):
        # 如果data/industry_info/all_search_results.json存在，则读取
        search_results_path = os.path.join(self.m.industry_dir, "all_search_results.json")
        if os.path.exists(search_results_path):
            with open(search_results_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 否则进行搜索
        companies = [self.p.company] + [c['name'] for c in context.get("all_companies", [])]
        results = {}
        for name in companies:
            r = DDGS().text(f"{name} 市场份额 行业分析", region="cn-zh", max_results=5)
            results[name] = r
            time.sleep(random.randint(5, 10))
        return results
