# profile.py
from typing import List, Dict, Optional

class AgentProfile:
    def __init__(
        self,
        name: str,                      # Agent 名称，如 "DataAgent"
        role: str,                      # 职责说明，如 "负责数据采集和预处理"
        objectives: List[str],         # Agent 的目标清单
        tools: List[str],              # 可使用的工具名称（与 tool registry 中的名称一致）
        knowledge: Optional[str] = "", # 可选：该 agent 的领域知识或背景假设
        interaction: Optional[Dict] = None, # 可选：交互模式（如接收哪些输入，输出格式）
        memory_type: Optional[str] = "short-term", # 记忆类型：short-term / long-term / none
        config: Optional[Dict] = None  # 运行所需的具体配置，如公司名、股票代码等
    ):
        self.name = name
        self.role = role
        self.objectives = objectives
        self.tools = tools
        self.knowledge = knowledge
        self.interaction = interaction or {}
        self.memory_type = memory_type
        self.config = config or {}

    def describe(self) -> str:
        return (
            f"Agent: {self.name}\n"
            f"Role: {self.role}\n"
            f"Objectives: {self.objectives}\n"
            f"Tools: {self.tools}\n"
            f"Knowledge: {self.knowledge}\n"
            f"Memory: {self.memory_type}\n"
            f"Interaction: {self.interaction}\n"
        )

    def get_tool_list(self) -> List[str]:
        return self.tools

    def get_config(self) -> Dict:
        return self.config

    def get_identity(self) -> str:
        return f"{self.config['company']}（{self.config['market']}:{self.config['code']}）"

    def get_objectives(self) -> List[str]:
        return self.objectives