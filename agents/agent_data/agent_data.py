import os
import json
import time
import glob
from .utils.get_financial_statements import get_all_financial_statements, save_financial_statements_to_csv
from .utils.get_stock_intro import get_stock_intro, save_stock_intro_to_txt
from .utils.get_shareholder_info import get_shareholder_info, get_table_content
from .utils.search_info import search_industry_info
from .utils.identify_competitors import identify_competitors_with_ai
from typing import Dict, List, Tuple

from utils.llm_helper import LLMHelper
from duckduckgo_search import DDGS
import random

class AgentProfile:
    def __init__(self, target_company: str, target_code: str, target_market: str):
        self.company = target_company
        self.code = target_code
        self.market = target_market

    def get_identity(self) -> str:
        return f"{self.company}（{self.market}:{self.code}）"


class AgentMemory:
    def __init__(self, data_dir: str, info_dir: str, industry_dir: str):
        self.data_dir = data_dir
        self.info_dir = info_dir
        self.industry_dir = industry_dir

        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(info_dir, exist_ok=True)
        os.makedirs(industry_dir, exist_ok=True)

    def save_json(self, path: str, data: dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def collect_company_file_paths(self) -> Dict[str, List[str]]:
        files = glob.glob(os.path.join(self.data_dir, "*.csv"))
        company_files = {}
        for file in files:
            name = os.path.basename(file).split("_")[0]
            company_files.setdefault(name, []).append(file)
        return company_files

class AgentPlanner:
    def __init__(self, profile, memory, llm):
        self.profile = profile
        self.memory = memory
        self.llm = llm
        self.valid_steps = [
            "get_competitor_listed_companies",
            "get_all_financial_data",
            "get_all_company_info",
            "get_shareholder_analysis",
            "search_industry_info"
        ]

class AgentPlanner:
    def __init__(self, profile, memory, llm):
        self.profile = profile
        self.memory = memory
        self.llm = llm
        self.valid_steps = [
            "get_competitor_listed_companies",
            "get_all_financial_data",
            "get_all_company_info",
            "get_shareholder_analysis",
            "search_industry_info"
        ]

    def decide_next_step(self, context: Dict[str, any], completed: List[str], failed: List[str]) -> str:
        context_summary = ""
        for key, value in context.items():
            if isinstance(value, str):
                content = value[:1000].replace('\n', ' ')  # 截断、清理过长文本
            else:
                content = "[结构化数据]"
            context_summary += f"【{key.upper()}】{content}\n\n"

        prompt = (
            f"你是一个金融分析数据规划Agent。\n"
            f"当前目标公司为 {self.profile.get_identity()}。\n\n"
            f"以下是当前已完成的步骤与输出内容摘要：\n"
            f"{context_summary or '无'}\n"
            f"当前执行失败的步骤：{', '.join(failed) or '无'}。\n\n"
            f"可调用函数有：{', '.join(self.valid_steps)}。\n"
            f"请判断下一步应该调用哪个函数（直接返回函数名即可），"
            f"如认为需要重新执行某个步骤，也请返回该函数名。若任务已完成，请返回 done。"
        )
        reply = self.llm.call(prompt, system_prompt="你是一个金融任务规划Agent，只返回一个函数名")
        step = reply.strip()
        return step if step in self.valid_steps else "done"


class AgentAction:
    def __init__(self, profile, memory, llm, llm_config=None):
        self.p = profile
        self.m = memory
        self.llm = llm
        self.llm_config = llm_config

    def get_competitor_listed_companies(self) -> List[Dict]:
        competitors = identify_competitors_with_ai(
            api_key=self.llm_config.api_key,
            base_url=self.llm_config.base_url,
            model_name=self.llm_config.model,
            company_name=self.p.company
        )
        return [c for c in competitors if c.get('market') != "未上市"]

    def get_all_financial_data(self, competitors: List[Dict]) -> Dict[str, List[Dict]]:
        def _parse_market(market_str: str, code: str) -> Tuple[str, str]:
            if "A" in market_str:
                code = "SH" + code if code.startswith("6") else "SZ" + code
                return "A", code
            elif "港" in market_str:
                return "HK", code

        data = get_all_financial_statements(self.p.code, self.p.market, "年度")
        save_financial_statements_to_csv(data, self.p.code, self.p.market, self.p.company, "年度", self.m.data_dir)

        competitors_data = {}
        for c in competitors:
            try:
                name, code, market = c['name'], c['code'], c['market']
                market, code = _parse_market(market, code)
                print(f"获取：{name}({market}:{code})")
                d = get_all_financial_statements(code, market, "年度")
                save_financial_statements_to_csv(d, code, market, name, "年度", self.m.data_dir)
                competitors_data[name] = d
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ 获取失败: {e}")
        return competitors_data

    def get_all_company_info(self, companies: List[Tuple[str, str, str]]) -> str:
        merged_info = ""
        for name, code, market in companies:
            try:
                info = get_stock_intro(code, market)
                if info:
                    merged_info += f"【公司信息开始】\n公司名称: {name}\n{info}\n【公司信息结束】\n\n"
                    save_stock_intro_to_txt(code, market, os.path.join(self.m.info_dir, f"{name}_{market}_{code}_info.txt"))
            except Exception as e:
                print(f"获取 {name} 信息失败: {e}")
            time.sleep(1)
        return merged_info or "未获取到公司基础信息"

    def get_shareholder_analysis(self) -> str:
        try:
            info = get_shareholder_info()
            if info['success'] and info.get("tables"):
                content = get_table_content(info.get("tables"))
                return self.llm.call("请分析以下股东信息表格内容：\n" + content,
                                     system_prompt="你是一个专业的股东信息分析师。")
            return f"股东信息获取失败: {info.get('error', '未知错误')}"
        except Exception as e:
            return f"股东信息获取失败: {e}"

    def search_industry_info(self, company_names: List[str]) -> str:
        all_results = {}
        for name in company_names:
            keywords = f"{name} 行业地位 市场份额 竞争分析 业务模式"
            print(f"🔍 搜索: {keywords}")
            try:
                results = DDGS().text(keywords=keywords, region="cn-zh", max_results=10)
                all_results[name] = results
                time.sleep(random.randint(15, 30))
            except Exception as e:
                print(f"搜索失败: {e}")
        path = os.path.join(self.m.industry_dir, "all_search_results.json")
        self.m.save_json(path, all_results)
        return path


class DataAgent:
    def __init__(self, target_company, target_code, target_market, llm_config):
        self.profile = AgentProfile(target_company, target_code, target_market)
        self.memory = AgentMemory("./data/financials", "./data/info", "./data/industry")
        self.llm = LLMHelper(llm_config)
        self.actions = AgentAction(self.profile, self.memory, self.llm, llm_config)
        self.planner = AgentPlanner(self.profile, self.memory, self.llm )

    def run(self):
        completed, failed = [], []
        context = {}

        while True:
            next_step = self.planner.decide_next_step(context, completed, failed)
            if next_step == "done":
                break

            print(f"🧠 LLM决定执行：{next_step}")
            func = getattr(self.actions, next_step, None)
            try:
                if next_step == "get_all_financial_data":
                    context['financial'] = func(context.get("competitors", []))
                elif next_step == "get_all_company_info":
                    companies = [(self.profile.company, self.profile.code, self.profile.market)]
                    competitors = context.get("competitors", [])
                    companies += [(c['name'], c['code'], c['market']) for c in competitors]
                    context['company_info'] = func(companies)
                elif next_step == "search_industry_info":
                    names = [self.profile.company] + [c['name'] for c in context.get("competitors", [])]
                    context['industry_info'] = func(names)
                elif next_step == "get_shareholder_analysis":
                    context['shareholder_analysis'] = func()
                elif next_step == "get_competitor_listed_companies":
                    context['competitors'] = func()
                else:
                    print(f"⚠️ 无法识别的步骤: {next_step}")
                    failed.append(next_step)
                    continue
                completed.append(next_step)
            except Exception as e:
                print(f"❌ {next_step} 执行失败: {e}")
                failed.append(next_step)
        return context