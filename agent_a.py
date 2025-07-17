from BaseAgent.base_agent import BaseAgent

class AnalysisAgent(BaseAgent):
    def __init__(self, profile, memory, planner, action, toolset):
        super().__init__(profile, memory, planner, action, toolset)

    def run(self):
        context = {}
        print("📈 [AnalysisAgent] 开始运行分析流程...")

        # Step 1: 从 memory 中加载已有财报数据
        financial_files = self.memory.load_company_financial_files(profile.company)
        
        # Step 2: 单公司分析
        individual_reports = self.analyze_individual_companies(financial_files)

        # Step 3: 竞争对手对比分析
        comparison_reports = self.compare_with_competitors(financial_files)

        # Step 4: 合并报告
        merged = self.merge_reports(individual_reports, comparison_reports)

        # Step 5: 商汤估值分析（特例）
        valuation = self.estimate_valuation_sensetime(financial_files)

        # Step 6: 整理公司简介（从 memory 读取，调用 LLM 总结）
        company_info_summary = self.summarize_company_infos()

        # Step 7: 整理股权结构（调用股东解析工具 + LLM）
        shareholder_summary = self.analyze_shareholder_structure()

        # Step 8: 行业搜索信息总结（从 RecallAgent 提供的数据 + LLM）
        industry_info_summary = self.summarize_industry_search_results()

        # Step 9: 汇总 markdown 报告
        markdown = self.assemble_markdown(
            company_info_summary,
            shareholder_summary,
            industry_info_summary,
            merged,
            valuation
        )

        # 保存到 memory / 文件
        self.memory.save("stage1_report_md", markdown)

        return {"stage1_markdown": markdown}
