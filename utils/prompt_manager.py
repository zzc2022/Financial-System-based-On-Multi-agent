import yaml
import json
from jinja2 import Environment, FileSystemLoader
from typing import Dict, List

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
    
    def load_system_prompt_from_profile(self, planner_yaml_path: str, profile, toolset: List[str]) -> str:
        """从agent profile动态生成system prompt"""
        # 加载工具信息
        with open(planner_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 从profile生成身份描述
        identity = self._generate_identity_from_profile(profile)
        prompt = identity + "\n\n"
        
        # 根据toolset过滤工具
        for tool in data.get("tools", []):
            if tool["name"] not in toolset:
                continue
            prompt += (
                f"工具：{tool['name']}\n"
                f"功能：{tool['usage']}\n"
                f"返回示例：\n{tool['output_example']}\n\n"
                f"额外信息：{tool.get('extra', '无')}\n\n"
            )
        return prompt.strip()
    
    def _generate_identity_from_profile(self, profile) -> str:
        """从profile生成身份描述"""
        report_type_map = {
            "company": "公司研报",
            "industry": "行业研报", 
            "macro": "宏观经济研报"
        }
        
        report_type = profile.get_config().get("report_type", "company")
        report_type_name = report_type_map.get(report_type, "公司研报")
        
        identity = f"你是 {profile.name}，一个专门负责{report_type_name}的智能分析代理。\n"
        identity += f"职责: {profile.role}\n"
        identity += f"目标: {'; '.join(profile.objectives)}\n"
        identity += f"专业知识: {profile.knowledge}\n"
        identity += f"你只能使用提供的工具函数来完成任务。"
        
        return identity
    
    def render_user_prompt(self, template_name: str, context: dict) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)
