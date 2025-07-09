# planner.py
from typing import Dict, Any, List
from utils.prompt_manager import PromptManager

class AgentPlanner:
    def __init__(self, profile, llm, prompt_path="prompts/planner/agent_d.yaml"):
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

        # Load system prompt from YAML file
        system_prompt = self.prompt_manager.load_system_prompt(self.prompt_path)
        # Prepare the prompt for the LLM
        user_prompt = self.prompt_manager.render_user_prompt(
            "user_prompt.jinja", {
                "profile": self.profile,
                "task": f"请规划获取 {self.profile.get_identity()} 的基础信息、竞争者和财务信息。",
                "context": context,
                "completed": completed,
                "failed": failed
            }
        )

        # prompt = (
        #     f"你是一个金融分析流程规划Agent。\n"
        #     f"目标公司为：{self.profile.get_identity()}。\n"
        #     f"当前已完成步骤：{', '.join(completed) or '无'}。\n"
        #     f"失败步骤：{', '.join(failed) or '无'}。\n"
        #     f"可调用工具函数有：{', '.join(toolset)}。\n\n"
        #     f"以下是当前上下文：\n{context_summary}\n"
        #     f"请决定下一步要调用哪个函数（只返回函数名），若任务已完成请返回 'done'。\n"
        #     f"注意：必须先执行 get_competitor_listed_companies()，且执行一遍就行了。"
        # )
        reply = self.llm.call(user_prompt, system_prompt=system_prompt + "你是一个规划器，只返回函数名")
        return reply.strip() if reply.strip() in toolset else "done"
