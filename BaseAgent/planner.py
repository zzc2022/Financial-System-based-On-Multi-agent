# planner.py
from typing import Dict, Any, List
from utils.prompt_manager import PromptManager

class AgentPlanner:
    def __init__(self, profile, llm, prompt_path="prompts/planner/toolset_illustration.yaml"):
        self.profile = profile
        self.llm = llm
        self.prompt_manager = PromptManager()
        self.prompt_path = prompt_path

    def decide_next_step(self, context: Dict[str, Any], completed: List[str], failed: List[str], toolset: List[str]) -> str:
        context_summary = ""
        for k, v in context.items():
            if isinstance(v, str):
                context_summary += f"【{k}】{v[:1000]}\n"
            else:
                context_summary += f"【{k}】[结构化数据]\n"

        # 生成任务描述
        report_type = self.profile.get_config().get("report_type", "company")
        if report_type == "industry":
            task = f"请规划{self.profile.get_config().get('industry', '目标行业')}行业研报的数据收集和分析任务"
        elif report_type == "macro":
            task = f"请规划{self.profile.get_config().get('country', '中国')}宏观经济研报的数据收集和分析任务"
        else:  # company
            if self.profile.name == "AnalysisAgent":
                task = "请规划分析阶段的图表生成、两两对比、估值建模等任务"
            else:
                task = f"请规划获取 {self.profile.get_identity()} 的基础信息、竞争者和财务信息。"

        # 使用新的prompt加载方法
        try:
            system_prompt = self.prompt_manager.load_system_prompt_from_profile(
                self.prompt_path, self.profile, toolset
            )
        except:
            # 如果新方法失败，回退到旧方法
            system_prompt = self.prompt_manager.load_system_prompt(self.prompt_path, self.profile.name)
            
        # Prepare the prompt for the LLM
        user_prompt = self.prompt_manager.render_user_prompt(
            "user_prompt.jinja", {
                "profile": self.profile,
                "task": task,
                "context": context,
                "completed": completed,
                "failed": failed
            }
        )

        reply = self.llm.call(user_prompt, system_prompt=system_prompt + "你是一个规划器，只返回函数名")
        return reply.strip() if reply.strip() in toolset else "done"
