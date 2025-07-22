# -*- coding: utf-8 -*-

import os
import json
import yaml
from typing import Dict, Any, List, Optional
from .create_session_dir import create_session_output_dir
from .format_execution_result import format_execution_result
from .extract_code import extract_code_from_response
from utils.llm_helper import LLMHelper
from .code_executor import CodeExecutor
from config.llm_config import LLMConfig
from prompts.planner.prompts import data_analysis_system_prompt, final_report_system_prompt,final_report_system_prompt_absolute


class Analyzer:
    """
    数据分析执行器
    
    职责：
    - 接收用户自然语言需求
    - 生成Python分析代码
    - 执行代码并收集结果
    - 基于执行结果继续生成后续分析代码
    """
    def __init__(self, llm_config: LLMConfig = None,
                 llm: Optional[LLMHelper] = None,
                 output_dir: str = "outputs",
                 max_rounds: int = 15,
                 absolute_path: bool = False):
        """
        初始化智能体
        
        Args:
            config: LLM配置
            output_dir: 输出目录
            max_rounds: 最大对话轮数
        """
        self.config = llm_config or LLMConfig()
        self.llm = llm or LLMHelper(self.config)
        self.base_output_dir = output_dir
        self.max_rounds = max_rounds
        # 对话历史和上下文
        self.conversation_history = []
        self.analysis_results = []
        self.current_round = 0
        self.session_output_dir = None
        self.executor = None
        self.absolute_path = absolute_path

    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        统一处理LLM响应，判断行动类型并执行相应操作
        
        Args:
            response: LLM的响应内容
            
        Returns:
            处理结果字典
        """
        try:
            yaml_data = self.llm.parse_yaml_response(response)
            action = yaml_data.get('action', 'generate_code')
            
            print(f"🎯 检测到动作: {action}")
            
            if action == 'analysis_complete':
                return self._handle_analysis_complete(response, yaml_data)
            elif action == 'collect_figures':
                return self._handle_collect_figures(response, yaml_data)
            elif action == 'generate_code':
                return self._handle_generate_code(response, yaml_data)
            else:
                print(f"⚠️ 未知动作类型: {action}，按generate_code处理")
                return self._handle_generate_code(response, yaml_data)
                
        except Exception as e:
            print(f"⚠️ 解析响应失败: {str(e)}，按generate_code处理")
            return self._handle_generate_code(response, {})
    
    def _handle_analysis_complete(self, response: str, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理分析完成动作"""
        print("✅ 分析任务完成")
        final_report = yaml_data.get('final_report', '分析完成，无最终报告')
        return {
            'action': 'analysis_complete',
            'final_report': final_report,
            'response': response,
            'continue': False
        }
    
    def _handle_collect_figures(self, response: str, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理图片收集动作"""
        print("📊 开始收集图片")
        figures_to_collect = yaml_data.get('figures_to_collect', [])
        
        collected_figures = []
        
        for figure_info in figures_to_collect:
            figure_number = figure_info.get('figure_number')
            filename = figure_info.get('filename', f'figure_{figure_number}.png')
            file_path = figure_info.get('file_path', '')  # 获取具体的文件路径
            description = figure_info.get('description', '')
            analysis = figure_info.get('analysis', '')
            
            print(f"📈 收集图片 {figure_number}: {filename}")
            print(f"   📂 路径: {file_path}")
            print(f"   📝 描述: {description}")
            print(f"   🔍 分析: {analysis}")
            
            # 只保留真实存在的图片
            if file_path and os.path.exists(file_path):
                print(f"   ✅ 文件存在: {file_path}")
                collected_figures.append({
                    'figure_number': figure_number,
                    'filename': filename,
                    'file_path': file_path,
                    'description': description,
                    'analysis': analysis
                })
            elif file_path:
                print(f"   ⚠️ 文件不存在: {file_path}，已跳过该图片")
            else:
                print(f"   ⚠️ 未提供文件路径，已跳过该图片")
        
        
        return {
            'action': 'collect_figures',
            'collected_figures': collected_figures,
            'response': response,  # response 仍然原样保留，若需彻底净化可进一步处理
            'continue': True
        }
    def _handle_generate_code(self, response: str, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理代码生成和执行动作"""
        code = yaml_data.get('code', '')
        if not code:
            code = extract_code_from_response(response)
        if code:
            print(f"🔧 执行代码:\n{code}")
            print("-" * 40)
            result = self.executor.execute_code(code)
            feedback = format_execution_result(result)
            print(f"📋 执行反馈:\n{feedback}")
            # 检查代码执行结果中是否有图片生成但文件不存在的情况
            # 假设图片保存路径会在 result['output'] 或 result['figures'] 里体现
            # 如果检测到图片文件不存在，建议用户重新分析
            missing_figures = []
            output = result.get('output', '')
            # 简单正则或字符串查找图片路径并判断是否存在
            import re
            img_paths = re.findall(r'(?:[\w./\\-]+\.(?:png|jpg|jpeg|svg))', str(output))
            for img_path in img_paths:
                if not os.path.isabs(img_path):
                    abs_path = os.path.join(self.session_output_dir, img_path)
                else:
                    abs_path = img_path
                if not os.path.exists(abs_path):
                    missing_figures.append(img_path)
            if missing_figures:
                feedback += f"\n⚠️ 检测到以下图片未生成成功: {missing_figures}\n建议重新分析本轮或修正代码后再试。"
                # 可以在这里返回一个特殊标志，供 analyze 主流程判断是否需要重启分析
                return {
                    'action': 'generate_code',
                    'code': code,
                    'result': result,
                    'feedback': feedback,
                    'response': response,
                    'continue': False,  # 终止本轮分析
                    'need_restart': True,
                    'missing_figures': missing_figures
                }
            return {
                'action': 'generate_code',
                'code': code,
                'result': result,
                'feedback': feedback,
                'response': response,
                'continue': True
            }
        else:
            print("⚠️ 未从响应中提取到可执行代码，要求LLM重新生成")
            return {
                'action': 'invalid_response',
                'error': '响应中缺少可执行代码',
                'response': response,
                'continue': True
            }

    def analyze(self, user_input: str, files: List[str] = None) -> Dict[str, Any]:
        """
        开始分析流程
        
        Args:
            user_input: 用户的自然语言需求
            files: 数据文件路径列表
            
        Returns:
            分析结果字典
        """
        # 重置状态
        self.conversation_history = []
        self.analysis_results = []
        self.current_round = 0
        
        # 创建本次分析的专用输出目录
        self.session_output_dir = create_session_output_dir(self.base_output_dir,user_input)
        
        # 初始化代码执行器，使用会话目录
        self.executor = CodeExecutor(self.session_output_dir)
        
        # 设置会话目录变量到执行环境中
        self.executor.set_variable('session_output_dir', self.session_output_dir)
        
        # 构建初始prompt
        initial_prompt = f"""用户需求: {user_input}"""
        if files:
            initial_prompt += f"\n数据文件: {', '.join(files)}"
        
        print(f"🚀 开始数据分析任务")
        print(f"📝 用户需求: {user_input}")
        if files:
            print(f"📁 数据文件: {', '.join(files)}")
        print(f"📂 输出目录: {self.session_output_dir}")
        print(f"🔢 最大轮数: {self.max_rounds}")
        print("=" * 60)
          # 添加到对话历史
        self.conversation_history.append({
            'role': 'user',
            'content': initial_prompt
        })
        
        while self.current_round < self.max_rounds:
            self.current_round += 1
            print(f"\n🔄 第 {self.current_round} 轮分析")
              # 调用LLM生成响应
            try:                
                # 获取当前执行环境的变量信息
                notebook_variables = self.executor.get_environment_info()
                
                # 格式化系统提示词，填入动态的notebook变量信息
                formatted_system_prompt = data_analysis_system_prompt.format(
                    notebook_variables=notebook_variables
                )
                
                response = self.llm.call(
                    prompt=self._build_conversation_prompt(),
                    system_prompt=formatted_system_prompt
                )
                
                print(f"🤖 助手响应:\n{response}")
                
                # 使用统一的响应处理方法
                process_result = self._process_response(response)
                
                # 根据处理结果决定是否继续
                if not process_result.get('continue', True):
                    print(f"\n✅ 分析完成！")
                    break
                
                # 添加到对话历史
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response
                })
                
                # 根据动作类型添加不同的反馈
                if process_result['action'] == 'generate_code':
                    feedback = process_result.get('feedback', '')
                    self.conversation_history.append({
                        'role': 'user',
                        'content': f"代码执行反馈:\n{feedback}"
                    })
                    
                    # 记录分析结果
                    self.analysis_results.append({
                        'round': self.current_round,
                        'code': process_result.get('code', ''),
                        'result': process_result.get('result', {}),
                        'response': response
                    })                
                elif process_result['action'] == 'collect_figures':
                    # 记录图片收集结果
                    collected_figures = process_result.get('collected_figures', [])
                    filtered_figures_to_collect = process_result.get('filtered_figures_to_collect', [])
                    feedback = f"已收集 {len(collected_figures)} 个图片及其分析"
                    self.conversation_history.append({
                        'role': 'user', 
                        'content': f"图片收集反馈:\n{feedback}\n请继续下一步分析。"
                    })
                    # 只记录过滤后的图片记忆
                    self.analysis_results.append({
                        'round': self.current_round,
                        'action': 'collect_figures',
                        'collected_figures': collected_figures,
                        'filtered_figures_to_collect': filtered_figures_to_collect,
                        'response': response
                    })
           
            except Exception as e:
                error_msg = f"LLM调用错误: {str(e)}"
                print(f"❌ {error_msg}")
                self.conversation_history.append({
                    'role': 'user',
                    'content': f"发生错误: {error_msg}，请重新生成代码。"
                })
        # 生成最终总结
        if self.current_round >= self.max_rounds:
            print(f"\n⚠️ 已达到最大轮数 ({self.max_rounds})，分析结束")
        
        return self._generate_final_report()
    
    def _build_conversation_prompt(self) -> str:
        """构建对话提示词"""
        prompt_parts = []
        
        for msg in self.conversation_history:
            role = msg['role']
            content = msg['content']
            if role == 'user':
                prompt_parts.append(f"用户: {content}")
            else:
                prompt_parts.append(f"助手: {content}")
        
        return "\n\n".join(prompt_parts)
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """生成最终分析报告"""
        # 收集所有生成的图片信息
        all_figures = []
        for result in self.analysis_results:
            if result.get('action') == 'collect_figures':
                all_figures.extend(result.get('collected_figures', []))
        
        print(f"\n📊 开始生成最终分析报告...")
        print(f"📂 输出目录: {self.session_output_dir}")
        print(f"🔢 总轮数: {self.current_round}")
        print(f"📈 收集图片: {len(all_figures)} 个")
        
        # 构建用于生成最终报告的提示词
        final_report_prompt = self._build_final_report_prompt(all_figures)
        
        # 调用LLM生成最终报告
        response = self.llm.call(
            prompt=final_report_prompt,
            system_prompt="你将会接收到一个数据分析任务的最终报告请求，请根据提供的分析结果和图片信息生成完整的分析报告。",
            max_tokens=8192  
        )
        
        # 解析响应，提取最终报告
        try:
            yaml_data = self.llm.parse_yaml_response(response)
            if yaml_data.get('action') == 'analysis_complete':
                final_report_content = yaml_data.get('final_report', '报告生成失败')
            else:
                final_report_content = "LLM未返回analysis_complete动作，报告生成失败"
        except:
            # 如果解析失败，直接使用响应内容
            final_report_content = response
        
        print("✅ 最终报告生成完成")
        # 手动添加附件清单到报告末尾
        if all_figures:
            appendix_section = "\n\n## 附件清单\n\n"
            appendix_section += "本报告包含以下图片附件：\n\n"
            
            for i, figure in enumerate(all_figures, 1):
                filename = figure.get('filename', '未知文件名')
                description = figure.get('description', '无描述')
                analysis = figure.get('analysis', '无分析')
                file_path = figure.get('file_path', '')
                
                appendix_section += f"{i}. **{filename}**\n"
                appendix_section += f"   - 描述：{description}\n"
                appendix_section += f"   - 细节分析：{analysis}\n"
                if self.absolute_path:
                    appendix_section += f"   - 文件路径：{file_path}\n"
                else:
                    appendix_section += f"   - 文件路径：./{filename}\n"
                appendix_section += "\n"
            
            # 将附件清单添加到报告内容末尾
            final_report_content += appendix_section
        
        # 保存最终报告到文件
        report_file_path = os.path.join(self.session_output_dir, "最终分析报告.md")
        try:
            with open(report_file_path, 'w', encoding='utf-8') as f:
                f.write(final_report_content)
            print(f"📄 最终报告已保存至: {report_file_path}")
            if all_figures:
                print(f"📎 已添加 {len(all_figures)} 个图片的附件清单")
        except Exception as e:
            print(f"❌ 保存报告文件失败: {str(e)}")
        
        # 返回完整的分析结果
        return {
            'session_output_dir': self.session_output_dir,
            'total_rounds': self.current_round,
            'analysis_results': self.analysis_results,
            'collected_figures': all_figures,
            'conversation_history': self.conversation_history,
            'final_report': final_report_content,
            'report_file_path': report_file_path       
            }

    def _build_final_report_prompt(self, all_figures: List[Dict[str, Any]]) -> str:
        """构建用于生成最终报告的提示词"""
        
        # 构建图片信息摘要，使用相对路径
        figures_summary = ""
        if all_figures:
            figures_summary = "\n生成的图片及分析:\n"
            for i, figure in enumerate(all_figures, 1):
                filename = figure.get('filename', '未知文件名')
                # 使用相对路径格式，适合在报告中引用
                relative_path = f"./{filename}"
                figures_summary += f"{i}. {filename}\n"
                figures_summary += f"   路径: {relative_path}\n"
                figures_summary += f"   描述: {figure.get('description', '无描述')}\n"
                figures_summary += f"   分析: {figure.get('analysis', '无分析')}\n\n"
        else:
            figures_summary = "\n本次分析未生成图片。\n"
        
        # 构建代码执行结果摘要（仅包含成功执行的代码块）
        code_results_summary = ""
        success_code_count = 0
        for result in self.analysis_results:
            if result.get('action') != 'collect_figures' and result.get('code'):
                exec_result = result.get('result', {})
                if exec_result.get('success'):
                    success_code_count += 1
                    code_results_summary += f"代码块 {success_code_count}: 执行成功\n"
                    if exec_result.get('output'):
                        code_results_summary += f"输出: {exec_result.get('output')[:]}\n\n"

        
        # 使用 prompts.py 中的统一提示词模板，并添加相对路径使用说明
        pre_prompt = final_report_system_prompt_absolute if self.absolute_path else final_report_system_prompt
        prompt = pre_prompt.format(
            current_round=self.current_round,
            session_output_dir=self.session_output_dir,
            figures_summary=figures_summary,
            code_results_summary=code_results_summary
        )
        
        return prompt

    def reset(self):
        """重置智能体状态"""
        self.conversation_history = []
        self.analysis_results = []
        self.current_round = 0
        self.executor.reset_environment()
