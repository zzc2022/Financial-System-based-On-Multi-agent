# evaluation_agent.py
from typing import Dict, List, Any, Optional
import os
from datetime import datetime
from .base_agent import BaseAgent
from .memory import AgentMemory
from .profile import AgentProfile
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from toolset.action_financial import FinancialActionToolset
from toolset.utils.report_type_config import ReportTypeConfig, ReportType


class EvaluationAgent(BaseAgent):
    """
    评价Agent - 专门用于评价研报质量
    继承BaseAgent，复用现有框架
    支持不同类型研报的差异化评价标准
    """
    
    def __init__(self, profile: AgentProfile, memory: AgentMemory, planner, llm, llm_config):
        # 创建专用的action工具集（复用FinancialActionToolset）
        action = FinancialActionToolset(profile, memory, llm, llm_config)
        
        # 定义evaluation专用工具集
        toolset = [
            "load_report_content",
            "identify_report_type_for_evaluation",
            "evaluate_content_completeness",
            "evaluate_data_accuracy", 
            "evaluate_analysis_depth",
            "evaluate_logical_coherence",
            "evaluate_professional_quality",
            "evaluate_market_insight",  # 行业研报专用
            "evaluate_macroeconomic_insight",  # 宏观研报专用
            "calculate_overall_evaluation_score",
            "generate_evaluation_report",
            "save_evaluation_result"
        ]
        
        # 调用父类初始化
        super().__init__(profile, memory, planner, action, toolset)
        
        # 初始化评价相关配置
        self.report_config = ReportTypeConfig()
        
        # 设置评价专用的配置
        self._setup_evaluation_config()
    
    def _setup_evaluation_config(self):
        """设置评价专用配置"""
        # 确保profile中有评价任务的标识
        current_config = self.profile.get_config()
        current_config.update({
            "task_type": "evaluation",
            "evaluation_standards": "professional",
            "output_format": "detailed_report"
        })
    
    def evaluate_report(self, report_path: str) -> Dict[str, Any]:
        """评价指定的研报文件"""
        # 设置评价任务的上下文
        context = {"report_path": report_path}
        
        # 执行评价流程
        result = self.run(context)
        
        # 返回最终评价结果
        final_evaluation = self.memory.context_get("final_evaluation")
        if final_evaluation:
            return final_evaluation
        else:
            return {
                "error": "评价未完成",
                "context_keys": list(result.keys()) if isinstance(result, dict) else []
            }
    
    def run(self, initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """重写run方法，支持传入初始上下文"""
        # 如果有初始上下文，设置到memory中
        if initial_context:
            for key, value in initial_context.items():
                self.memory.context_set(key, value)
        
        # 调用父类的run方法
        return super().run()
    
    def batch_evaluate_reports(self, report_paths: List[str]) -> List[Dict[str, Any]]:
        """批量评价多个研报"""
        results = []
        
        for report_path in report_paths:
            try:
                # 为每个报告重置memory context
                self.memory.context_clear()
                
                result = self.evaluate_report(report_path)
                result["report_path"] = report_path
                results.append(result)
                
                print(f"✅ 完成评价: {os.path.basename(report_path)}")
                
            except Exception as e:
                error_result = {
                    "report_path": report_path,
                    "error": str(e),
                    "overall_score": 0,
                    "grade": "评价失败"
                }
                results.append(error_result)
                print(f"❌ 评价失败: {os.path.basename(report_path)} - {e}")
        
        return results
    
    def get_evaluation_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取批量评价的汇总信息"""
        if not results:
            return {"error": "没有评价结果"}
        
        # 统计评价结果
        successful_evaluations = [r for r in results if "error" not in r]
        failed_evaluations = [r for r in results if "error" in r]
        
        if not successful_evaluations:
            return {
                "total_reports": len(results),
                "successful": 0,
                "failed": len(failed_evaluations),
                "average_score": 0,
                "grade_distribution": {}
            }
        
        # 计算统计信息
        scores = [r.get("overall_score", 0) for r in successful_evaluations]
        average_score = sum(scores) / len(scores) if scores else 0
        
        # 等级分布
        grade_counts = {}
        for result in successful_evaluations:
            grade = result.get("grade", "未知")
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # 按研报类型分布
        type_distribution = {}
        for result in successful_evaluations:
            report_type = result.get("report_type", "未知")
            type_distribution[report_type] = type_distribution.get(report_type, 0) + 1
        
        return {
            "total_reports": len(results),
            "successful": len(successful_evaluations),
            "failed": len(failed_evaluations),
            "average_score": round(average_score, 2),
            "grade_distribution": grade_counts,
            "type_distribution": type_distribution,
            "score_range": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0
            }
        }
    
    def generate_batch_evaluation_report(self, results: List[Dict[str, Any]], 
                                       output_path: str = None) -> str:
        """生成批量评价汇总报告"""
        summary = self.get_evaluation_summary(results)
        
        if output_path is None:
            output_path = f"批量评价汇总报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # 构建汇总报告内容
        report_content = f"""
# 批量研报评价汇总报告

## 评价概况
- **评价时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **报告总数**: {summary['total_reports']}
- **成功评价**: {summary['successful']}
- **失败评价**: {summary['failed']}
- **平均评分**: {summary['average_score']}/100

## 评分分布
"""
        
        # 等级分布
        if summary.get('grade_distribution'):
            report_content += "\n### 等级分布\n"
            for grade, count in summary['grade_distribution'].items():
                percentage = (count / summary['successful']) * 100
                report_content += f"- **{grade}**: {count}份 ({percentage:.1f}%)\n"
        
        # 研报类型分布  
        if summary.get('type_distribution'):
            report_content += "\n### 研报类型分布\n"
            for report_type, count in summary['type_distribution'].items():
                percentage = (count / summary['successful']) * 100
                report_content += f"- **{report_type}**: {count}份 ({percentage:.1f}%)\n"
        
        # 详细评价结果
        report_content += "\n## 详细评价结果\n"
        
        successful_results = [r for r in results if "error" not in r]
        # 按评分排序
        successful_results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        
        for i, result in enumerate(successful_results, 1):
            report_name = os.path.basename(result.get("report_path", f"报告{i}"))
            score = result.get("overall_score", 0)
            grade = result.get("grade", "未知")
            report_type = result.get("report_type", "未知")
            
            report_content += f"""
### {i}. {report_name}
- **类型**: {report_type}
- **评分**: {score}/100
- **等级**: {grade}
"""
        
        # 失败的评价
        failed_results = [r for r in results if "error" in r]
        if failed_results:
            report_content += "\n## 评价失败的报告\n"
            for result in failed_results:
                report_name = os.path.basename(result.get("report_path", "未知"))
                error_msg = result.get("error", "未知错误")
                report_content += f"- **{report_name}**: {error_msg}\n"
        
        # 保存报告
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content.strip())
            return f"批量评价汇总报告已保存至: {output_path}"
        except Exception as e:
            return f"保存汇总报告失败: {str(e)}"
    
    def compare_reports(self, report_paths: List[str]) -> Dict[str, Any]:
        """比较多个研报的质量"""
        # 批量评价
        results = self.batch_evaluate_reports(report_paths)
        
        # 过滤成功的评价结果
        successful_results = [r for r in results if "error" not in r]
        
        if len(successful_results) < 2:
            return {"error": "至少需要2个成功评价的研报才能进行比较"}
        
        # 按评分排序
        successful_results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        
        # 比较分析
        best_report = successful_results[0]
        worst_report = successful_results[-1]
        
        comparison = {
            "total_compared": len(successful_results),
            "best_report": {
                "path": best_report.get("report_path", ""),
                "name": os.path.basename(best_report.get("report_path", "")),
                "score": best_report.get("overall_score", 0),
                "grade": best_report.get("grade", ""),
                "type": best_report.get("report_type", "")
            },
            "worst_report": {
                "path": worst_report.get("report_path", ""),
                "name": os.path.basename(worst_report.get("report_path", "")),
                "score": worst_report.get("overall_score", 0),
                "grade": worst_report.get("grade", ""),
                "type": worst_report.get("report_type", "")
            },
            "score_gap": best_report.get("overall_score", 0) - worst_report.get("overall_score", 0),
            "all_results": successful_results
        }
        
        return comparison


# 便捷函数
def create_evaluation_agent(profile_config: Dict[str, Any], 
                          memory_config: Dict[str, Any] = None,
                          llm=None, llm_config=None) -> EvaluationAgent:
    """创建评价Agent的便捷函数"""
    from .memory import AgentMemory
    from .profile import AgentProfile
    from .planner import Planner
    
    # 创建profile
    profile = AgentProfile(
        name="EvaluationAgent",
        role="研报评价专家", 
        goal="对各类研报进行专业、客观的质量评价",
        memory_config=memory_config or {},
        **profile_config
    )
    
    # 创建memory
    memory = AgentMemory(
        profile.name,
        **(memory_config or {})
    )
    
    # 创建planner
    planner = Planner(profile, memory, llm, llm_config)
    
    # 创建EvaluationAgent
    agent = EvaluationAgent(profile, memory, planner, llm, llm_config)
    
    return agent