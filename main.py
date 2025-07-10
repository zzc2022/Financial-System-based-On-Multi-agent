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

# 初始化嵌入模型（可选）
embedding_config = create_embedding_config("qwen")  # 使用Qwen API
embedding_model = embedding_config.get_model()

##### 数据提取Agent #####
profile = AgentProfile("商汤科技", "00020", "HK")
memory = AgentMemory("./data/financials", "./data/info", "./data/industry", embedding_model)
llm = LLMHelper(llm_config)
planner = AgentPlanner(profile, llm)
action = FinancialActionToolset(profile, memory, llm, llm_config)

toolset = [fn for fn in dir(action) if not fn.startswith("__") and callable(getattr(action, fn))]

agent = BaseAgent(profile, memory, planner, action, toolset)

result = agent.run()

for k, v in result.items():
    print(f"[{k}]\n{v if isinstance(v, str) else '[结构化数据]'}")