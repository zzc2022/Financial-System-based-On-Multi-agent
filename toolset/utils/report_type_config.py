# report_type_config.py
from typing import Dict, List, Any
from enum import Enum

class ReportType(Enum):
    COMPANY = "company"
    INDUSTRY = "industry" 
    MACRO = "macro"

class ReportTypeConfig:
    """研报类型配置管理器"""
    
    def __init__(self):
        self.configs = {
            ReportType.COMPANY: {
                "name": "公司研报",
                "description": "针对特定公司的深度分析研报",
                "data_requirements": [
                    "目标企业财务三大报表",
                    "同行企业财务数据",
                    "股权结构信息",
                    "公司基本信息",
                    "竞争对手分析"
                ],
                "data_tools": [
                    "get_competitor_listed_companies",
                    "get_all_financial_data", 
                    "get_all_company_info",
                    "get_shareholder_analysis",
                    "get_company_search_info"
                ],
                "analysis_tools": [
                    "analyze_companies_in_directory",
                    "run_comparison_analysis", 
                    "merge_reports",
                    "evaluation",
                    "get_analysis_report",
                    "deep_report_generation"
                ],
                "prompt_template": "company_report_template",
                "output_sections": [
                    "公司概况",
                    "财务分析", 
                    "竞争对手分析",
                    "投资建议",
                    "风险提示"
                ]
            },
            
            ReportType.INDUSTRY: {
                "name": "行业研报",
                "description": "针对特定行业的全面分析研报",
                "data_requirements": [
                    "行业发展现状与规模",
                    "产业链上下游分析",
                    "行业协会年报数据",
                    "主要企业财报数据",
                    "相关政策影响",
                    "技术发展趋势"
                ],
                "data_tools": [
                    "get_industry_overview",
                    "get_industry_chain_analysis",
                    "get_industry_policy_impact", 
                    "get_industry_technology_trends",
                    "get_industry_association_reports",
                    "get_industry_market_scale",
                    "get_leading_companies_data"
                ],
                "analysis_tools": [
                    "analyze_industry_structure",
                    "analyze_industry_trends",
                    "analyze_industry_competition",
                    "industry_valuation_analysis",
                    "industry_risk_assessment",
                    "generate_industry_report"
                ],
                "prompt_template": "industry_report_template",
                "output_sections": [
                    "行业概况",
                    "产业链分析",
                    "市场规模与竞争格局",
                    "技术发展趋势", 
                    "政策环境分析",
                    "投资机会与风险"
                ]
            },
            
            ReportType.MACRO: {
                "name": "宏观经济研报",
                "description": "宏观经济形势分析与策略研报",
                "data_requirements": [
                    "GDP增长数据",
                    "CPI通胀数据", 
                    "利率走势数据",
                    "汇率变动数据",
                    "政府政策报告",
                    "美联储利率政策",
                    "行业政策影响"
                ],
                "data_tools": [
                    "get_gdp_data",
                    "get_cpi_data",
                    "get_interest_rate_data",
                    "get_exchange_rate_data", 
                    "get_federal_reserve_data",
                    "get_policy_reports",
                    "get_macro_industry_impact"
                ],
                "analysis_tools": [
                    "analyze_macro_trends",
                    "analyze_policy_impact",
                    "analyze_global_influence", 
                    "macro_forecasting",
                    "sector_rotation_analysis",
                    "generate_macro_report"
                ],
                "prompt_template": "macro_report_template",
                "output_sections": [
                    "宏观经济概况",
                    "货币政策分析",
                    "财政政策分析",
                    "国际环境影响",
                    "行业影响分析", 
                    "投资策略建议"
                ]
            }
        }
    
    def get_config(self, report_type: ReportType) -> Dict[str, Any]:
        """获取指定研报类型的配置"""
        return self.configs.get(report_type, {})
    
    def get_data_tools(self, report_type: ReportType) -> List[str]:
        """获取数据收集工具列表"""
        config = self.get_config(report_type)
        return config.get("data_tools", [])
    
    def get_analysis_tools(self, report_type: ReportType) -> List[str]:
        """获取分析工具列表"""
        config = self.get_config(report_type)
        return config.get("analysis_tools", [])
    
    def get_output_sections(self, report_type: ReportType) -> List[str]:
        """获取输出章节列表"""
        config = self.get_config(report_type)
        return config.get("output_sections", [])
    
    def identify_report_type(self, instruction: str) -> ReportType:
        """根据指令识别研报类型"""
        instruction_lower = instruction.lower()
        
        # 关键词匹配
        if any(keyword in instruction_lower for keyword in ["公司研报", "企业分析", "公司分析", "个股研报"]):
            return ReportType.COMPANY
        elif any(keyword in instruction_lower for keyword in ["行业研报", "行业分析", "产业分析", "行业报告"]):
            return ReportType.INDUSTRY
        elif any(keyword in instruction_lower for keyword in ["宏观", "经济研报", "策略研报", "宏观分析", "经济分析"]):
            return ReportType.MACRO
        
        # 默认返回公司研报
        return ReportType.COMPANY
    
    def get_prompt_template_path(self, report_type: ReportType) -> str:
        """获取prompt模板路径"""
        config = self.get_config(report_type)
        template_name = config.get("prompt_template", "company_report_template")
        return f"prompts/template/{template_name}.yaml"