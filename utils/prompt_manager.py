import yaml
import json
from jinja2 import Environment, FileSystemLoader

class PromptManager:
    def __init__(self, base_dir="prompts"):
        self.env = Environment(loader=FileSystemLoader(f"{base_dir}/template"))

    def load_system_prompt(self, planner_yaml_path: str, agent_name: str) -> str:
        # 加载工具信息
        with open(planner_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 从JSON文件加载身份信息
        json_path = "prompts/planner/agent_profile_prompt.json"
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            agent_config = json_data.get("agents", {}).get(agent_name, {})
            prompt = agent_config.get("identity", "") + "\n\n"
            tool_available = agent_config.get("tools", "")
            
        for tool in data.get("tools", []):
            if tool["name"] not in tool_available:
                continue
            prompt += (
                f"工具：{tool['name']}\n"
                f"功能：{tool['usage']}\n"
                f"返回示例：\n{tool['output_example']}\n\n"
                f"额外信息：{tool.get('extra', '无')}\n\n"
            )
        return prompt.strip()
    
    def render_user_prompt(self, template_name: str, context: dict) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)
