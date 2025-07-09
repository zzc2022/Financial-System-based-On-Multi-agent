import yaml
from jinja2 import Environment, FileSystemLoader

class PromptManager:
    def __init__(self, base_dir="prompts"):
        self.env = Environment(loader=FileSystemLoader(f"{base_dir}/template"))

    def load_system_prompt(self, planner_yaml_path: str) -> str:
        with open(planner_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        prompt = data.get("identity", "") + "\n\n"
        for tool in data.get("tools", []):
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
