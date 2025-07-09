# base_agent.py
from typing import Dict, List, Any

class BaseAgent:
    def __init__(self, profile, memory, planner, action, toolset: List[str]):
        self.profile = profile
        self.memory = memory
        self.planner = planner
        self.action = action
        self.toolset = toolset

    def run(self):
        completed, failed = [], []
        context = {}

        while True:
            next_step = self.planner.decide_next_step(context, completed, failed, self.toolset)
            if next_step == "done":
                break

            if next_step in completed or next_step in failed:
                print(f"🔄 重复步骤：{next_step}，跳过执行。")
                continue

            print(f"🧠 LLM决定执行：{next_step}")
            func = getattr(self.action, next_step, None)
            if not func:
                print(f"❌ 无效步骤：{next_step}")
                failed.append(next_step)
                continue

            try:
                result = func(context)  # 所有函数以 context 为参数
                if next_step == "get_competitor_listed_companies":
                    result.append(self.profile.get_config())
                    context["all_companies"] = result
                else:
                    context[next_step] = result
                completed.append(next_step)
            except Exception as e:
                print(f"❌ {next_step} 执行失败: {e}")
                failed.append(next_step)
        return context
