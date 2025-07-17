from BaseAgent.base_agent import BaseAgent
from BaseAgent.profile import AgentProfile
from BaseAgent.memory import AgentMemory
from BaseAgent.planner import AgentPlanner
from toolset.action_financial import FinancialActionToolset
from config.llm_config import LLMConfig
from config.embedding_config import create_embedding_config
from utils.llm_helper import LLMHelper
import os
from dotenv import load_dotenv

load_dotenv()

# 初始化组件
llm_config = LLMConfig(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
)

# 初始化嵌入模型
embedding_config = create_embedding_config("qwen")
embedding_model = embedding_config.get_model()

##### 数据提取Agent #####
data_agent_profile = AgentProfile(
    name="DataAgent",
    role="负责数据采集与清洗，涵盖财务报表、公司信息、行业情报等",
    objectives=[
        "采集目标公司财务三大表数据",
        "收集主要竞争对手名单及其财务数据",
        "获取公司基本介绍和行业信息"
    ],
    tools=["get_financials", "get_stock_info", "web_search"],
    knowledge="具备港股和A股市场结构与财报格式知识，理解基本财务术语",
    interaction={
        "input": "公司名称与代码",
        "output": "结构化的数据表（CSV）、文本信息（TXT/JSON）"
    },
    memory_type="short-term",
    config={
        "company": "商汤科技",
        "code": "00020",
        "market": "HK"
    }
)

memory = AgentMemory("./data/financials", "./data/info", "./data/industry", embedding_model)
llm = LLMHelper(llm_config)
planner = AgentPlanner(data_agent_profile, llm)
action = FinancialActionToolset(data_agent_profile, memory, llm, llm_config)

toolset = [fn for fn in dir(action) if not fn.startswith("__") and callable(getattr(action, fn))]

agent_d = BaseAgent(data_agent_profile, memory, planner, action, toolset)

result = agent_d.run()

for k, v in result.items():
    print(f"[{k}]\n{v if isinstance(v, str) else '[结构化数据]'}")