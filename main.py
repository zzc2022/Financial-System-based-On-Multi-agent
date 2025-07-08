from agents.agent_data.data_scratch_agent import DataAgent
# from agents.agent_analysis.data_analysis_agent import AgentA
from config.llm_config import LLMConfig
import os
import json
from dotenv import load_dotenv

# ========== 环境变量与全局配置 ==========
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model = os.getenv("OPENAI_MODEL", "gpt-4")

llm_config = LLMConfig(
    api_key=api_key,
    base_url=base_url,
    model=model,
    temperature=0.7,
    max_tokens=8192,
)

# ========== 数据代理实例化 ==========
agent_d = DataAgent("商汤科技", "00020", "HK", llm_config=llm_config)

competitors = agent_d.get_competitor_listed_companies()
agent_d.get_all_financial_data(competitors)

companies_info = [(agent_d.target_company, agent_d.target_code, agent_d.target_market)]
companies_info += [(c['name'], c['code'], c['market']) for c in competitors]
company_infos = agent_d.get_all_company_info(companies_info)

shareholder_analysis = agent_d.get_shareholder_analysis()

# 如果all_search_results.json文件存在，则读取
search_results_path = os.path.join(agent_d.industry_dir, "all_search_results.json")
if os.path.exists(search_results_path):
    with open(search_results_path, 'r', encoding='utf-8') as f:
        all_search_results = json.load(f)
else:
    industry_info_path = agent_d.search_industry_info([agent_d.target_company] + [c['name'] for c in competitors])


'''# ========== 分析代理实例化 ==========
agent_a = AgentA(
    llm_config=llm_config
)'''