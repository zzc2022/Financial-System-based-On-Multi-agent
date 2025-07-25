# action_financial.py
from toolset.utils.get_financial_statements import get_all_financial_statements, save_financial_statements_to_csv
from toolset.utils.get_stock_intro import get_stock_intro, save_stock_intro_to_txt
from toolset.utils.get_shareholder_info import get_shareholder_info, get_table_content
from toolset.utils.search_engine import SearchEngine
from toolset.utils.identify_competitors import identify_competitors_with_ai
from toolset.utils.markdown_utils import save_markdown, format_markdown, convert_to_docx, extract_images_from_markdown, load_report_content, get_background, generate_outline, generate_section
from toolset.utils.analyzer import Analyzer
from toolset.utils.industry_data_collector import IndustryDataCollector
from toolset.utils.macro_data_collector import MacroDataCollector
from toolset.utils.report_type_config import ReportTypeConfig, ReportType
import time, random, os
from datetime import datetime
import glob
import json

class FinancialActionToolset:
    def __init__(self, profile, memory, llm, llm_config):
        self.p = profile
        self.m = memory
        self.llm = llm
        self.cfg = llm_config
        # 初始化默认报告路径
        self.reports_dir = os.path.join(self.m.data_dir, "reports")
        self.default_report_path = os.path.join(self.reports_dir, "financial_analysis_report.md")
        # Analyzer initialized
        self.analyzer = Analyzer(llm_config=llm_config, llm=llm, output_dir=self.m.data_dir, absolute_path=False)
        
        # 初始化新的数据收集器
        self.industry_collector = IndustryDataCollector()
        self.macro_collector = MacroDataCollector()
        self.report_config = ReportTypeConfig()
        
        # 当前研报类型（从profile配置中获取，默认为公司研报）
        self.current_report_type = self._determine_report_type()
    
    def _determine_report_type(self) -> ReportType:
        """确定研报类型"""
        # 从profile配置中获取研报类型
        report_type_str = self.p.get_config().get("report_type", "company")
        
        # 从指令中识别（如果有的话）
        instruction = self.p.get_config().get("instruction", "")
        if instruction:
            return self.report_config.identify_report_type(instruction)
        
        # 根据字符串映射到枚举
        type_mapping = {
            "company": ReportType.COMPANY,
            "industry": ReportType.INDUSTRY, 
            "macro": ReportType.MACRO
        }
        return type_mapping.get(report_type_str.lower(), ReportType.COMPANY)

    #### DATA COLLECTION ACTIONS ####
    def get_competitor_listed_companies(self, context):
        # 只有公司研报才需要竞争对手
        if self.current_report_type != ReportType.COMPANY:
            return []
        
        result = identify_competitors_with_ai(
            api_key=self.cfg.api_key,
            base_url=self.cfg.base_url,
            model_name=self.cfg.model,
            company_name=self.p.get_config()['company']
        )
        result = [c for c in result if c.get('market') != "未上市"]
        return result

    def get_all_financial_data(self, context):
        # 只有公司研报才需要财务数据
        if self.current_report_type != ReportType.COMPANY:
            return []
        
        companies = context.get("all_companies", [])
        data_lst = []
        for p in companies:
            try:
                company, code, market = p['company'], p['code'], p['market']
                print(f"获取：{company}({market}:{code})")
                data = get_all_financial_statements(code, market, "年度")
                data_lst.append(data)
                save_financial_statements_to_csv(data, code, market, "年度", company, self.m.data_dir)
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ 获取失败: {e}")
        return data_lst

    def get_all_company_info(self, context):
        # 只有公司研报才需要公司信息
        if self.current_report_type != ReportType.COMPANY:
            return ""
        
        def _parse_market( market_str: str, code: str) -> tuple[str, str]:
            """
            解析市场信息并格式化股票代码
            
            Args:
                market_str (str): 市场描述字符串（如"A股"、"港股"等）
                code (str): 原始股票代码
                
            Returns:
                Tuple[str, str]: 解析后的市场代码和格式化的股票代码
                            - A股：返回("A", "SH000001"或"SZ000001"格式)
                            - 港股：返回("HK", 原代码)
            """
            if "A" in market_str:
                market = "A"
                if not code.startswith("SH") and not code.startswith("SZ"):
                    code = "SH" + code if code.startswith("6") else "SZ" + code
                return market, code
            elif "港" in market_str:
                market = "HK"
                return market, code
            return market_str, code

        companies = context.get("all_companies", [])
        for c in companies:
            if 'market' in c and 'code' in c:
                market, code = _parse_market(c['market'], c['code'])
                c['market'] = market
                c['code'] = code
        context["all_companies"] = companies

        result = ""
        for item in companies:
            info = get_stock_intro(item['code'], item['market'])
            if info:
                result += info
                # 保存简介到txt文件
                company = item.get('company', item['code'])
                filecompany = f"{company}_{item['market']}_{item['code']}.txt"
                save_path = os.path.join(self.m.info_dir, filecompany)
                save_stock_intro_to_txt(item['code'], item['market'], save_path)
        return result

    def get_shareholder_analysis(self, context):
        info = get_shareholder_info()
        if info['success']:
            content = get_table_content(info['tables'])
            return self.llm.call("分析以下股东信息：\n" + content, system_prompt="你是股东分析专家")
        return "股东信息获取失败"

    def search_industry_info(self, context, engine: str = "sogou"):
        # 只有公司研报才需要行业搜索
        if self.current_report_type != ReportType.COMPANY:
            return {}
        
        # 如果data/industry_info/all_search_results.json存在，则读取
        search_results_path = os.path.join(self.m.industry_dir, "all_search_results.json")
        if os.path.exists(search_results_path):
            with open(search_results_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 否则进行搜索
        companies = [self.p.get_config()['company']] + [c['company'] for c in context.get("all_companies", [])]
        results = {}
        for company in companies:
            r = SearchEngine(engine).search(f"{company} 市场份额 行业分析", max_results=10)
            results[company] = r
            # 拼接所有描述
            # all_desc = "\n".join([item['description'] for item in r if 'description' in item])
            # # 用LLM生成摘要
            # summary = self.llm.call(f"请用中文简要总结以下关于{company}的行业市场份额和竞争地位信息：\n{all_desc}", system_prompt="你是行业分析专家")
            # results[company] = {
            #     "search_results": r,
            #     "summary": summary
            # }
            time.sleep(random.randint(5, 10))

        # 确保目录存在
        os.makedirs(self.m.industry_dir, exist_ok=True)
        with open(search_results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        return results

    #### DATA ANALYSIS ACTIONS ####
    def quick_analysis(self, query, files=None):
        """
        快速数据分析函数
        
        Args:
            query: 分析需求（自然语言）
            files: 数据文件路径列表
            output_dir: 输出目录
            max_rounds: 最大分析轮数
            
        Returns:
            dict: 分析结果
        """
        return self.analyzer.analyze(query, files or [])
    
    def get_company_files(self, data_dir):
        """获取公司文件"""
        abs_data_dir = os.path.abspath(data_dir)
        print(f"获取公司数据目录: {abs_data_dir}")
        all_files = glob.glob(f"{abs_data_dir}/*.csv")
        companies = {}
        for file in all_files:
            filename = os.path.basename(file)
            company_name = filename.split("_")[0]
            companies.setdefault(company_name, []).append(file)
        return companies

    def analyze_companies_in_directory(self, context):
        """
        分析指定目录下的所有公司数据
        """
        def analyze_companies(data_directory, query="基于表格的数据，分析有价值的内容，并绘制相关图表。最后生成汇报给我。"):
            """分析目录中的所有公司"""
            def analyze_individual_company(files, query=None):
                """分析单个公司"""
                if query is None:
                    query = "基于表格的数据，分析有价值的内容，并绘制相关图表。最后生成汇报给我。"
                report = self.quick_analysis(
                    query=query, files=files
                )
                return report

            company_files = self.get_company_files(data_directory)
            all_reports = {}
            for company_name, files in company_files.items():
                report = analyze_individual_company(files, query)
                if report:
                    all_reports[company_name] = report
            return all_reports

        results = analyze_companies(
            data_directory=self.m.data_dir,
            query="基于表格的数据，分析有价值的内容，并绘制相关图表。最后生成汇报给我。"
        )

        return results

    def run_comparison_analysis(self, context):
        """
        运行竞争对手分析
        """
        # 只有公司研报才需要公司比较
        if self.current_report_type != ReportType.COMPANY:
            return "非公司研报类型，跳过对比分析"
        
        def comparison_analysis(data_directory, target_company_name):
            """运行对比分析"""
            company_files = self.get_company_files(data_directory)
            if not company_files or target_company_name not in company_files:
                return {}
            competitors = [company for company in company_files.keys() if company != target_company_name]
            comparison_reports = {}
            for competitor in competitors:
                comparison_key = f"{target_company_name}_vs_{competitor}"
                report = compare_two_companies(
                    company_files[target_company_name],
                    company_files[competitor]
                )
                if report:
                    comparison_reports[comparison_key] = {
                        'company1': target_company_name,
                        'company2': competitor,
                        'report': report
                    }
            return comparison_reports

        def compare_two_companies(company1_files, company2_files):
            """比较两个公司"""
            query = "基于两个公司的表格的数据，分析有共同点的部分，绘制对比分析的表格，并绘制相关图表。最后生成汇报给我。"
            all_files = company1_files + company2_files
            report = self.quick_analysis(
                query=query,
                files=all_files,
            )
            return report
        
        comparison_results = comparison_analysis(
            data_directory=self.m.data_dir,
            target_company_name=self.p.get_config()['company']
        )

        return comparison_results
    
    def merge_reports(self, context):
        """合并报告"""
        individual_reports = context.get("individual_reports", {})
        comparison_reports = context.get("comparison_reports", {})
        merged = {}
        for company, report in individual_reports.items():
            merged[company] = report
        for comp_key, comp_data in comparison_reports.items():
            merged[comp_key] = comp_data['report']
        return merged
    
    def evaluation(self, context):
        def get_sensetime_files(data_dir):
            """获取商汤科技的财务数据文件"""
            abs_data_dir = os.path.abspath(data_dir)
            print(f"获取商汤科技财务数据目录: {abs_data_dir}")
            all_files = glob.glob(f"{abs_data_dir}/*.csv")
            sensetime_files = []
            for file in all_files:
                filename = os.path.basename(file)
                company_name = filename.split("_")[0]
                if "商汤" in company_name or "SenseTime" in company_name:
                    sensetime_files.append(file)
            return sensetime_files
        def analyze_sensetime_valuation(files):
            """分析商汤科技的估值与预测"""
            query = "基于三大表的数据，构建估值与预测模型，模拟关键变量变化对财务结果的影响,并绘制相关图表。最后生成汇报给我。"
            report = self.quick_analysis(query=query, files=files)
            return report

        # 商汤科技估值与预测分析
        sensetime_files = get_sensetime_files(self.m.data_dir)
        sensetime_valuation_report = None
        if sensetime_files:
            sensetime_valuation_report = analyze_sensetime_valuation(sensetime_files)
        return sensetime_valuation_report if sensetime_valuation_report else "商汤科技的估值与预测分析未能完成或无相关数据。"
    
    def get_analysis_report(self, context):
        """
        获取分析报告
        """
        def get_company_infos(data_dir="./data/info"):
            """获取公司信息"""
            abs_data_dir = os.path.abspath(data_dir)
            print(f"获取公司信息目录: {abs_data_dir}")
            all_files = os.listdir(abs_data_dir)
            company_infos = ""
            for file in all_files:
                if file.endswith(".txt"):
                    company_name = file.split(".")[0]
                    with open(os.path.join(data_dir, file), 'r', encoding='utf-8') as f:
                        content = f.read()
                    company_infos += f"【公司信息开始】\n公司名称: {company_name}\n{content}\n【公司信息结束】\n\n"
            return company_infos
        
        def format_final_reports(all_reports):
            """格式化最终报告"""
            formatted_output = []
            for company_name, report in all_reports.items():
                formatted_output.append(f"【{company_name}财务数据分析结果开始】")
                final_report = report.get("final_report", "未生成报告")
                formatted_output.append(final_report)
                formatted_output.append(f"【{company_name}财务数据分析结果结束】")
                formatted_output.append("")
            return "\n".join(formatted_output)
        
        # 整理公司信息
        company_infos = get_company_infos()
        company_infos = self.llm.call(
            f"请整理以下公司信息内容，确保格式清晰易读，并保留关键信息：\n{company_infos}",
            system_prompt="你是一个专业的公司信息整理师。",
            max_tokens=8192,
            temperature=0.5
        )
        
        # 整理股权信息
        info = get_shareholder_info()
        shangtang_shareholder_info = info.get("tables", [])
        table_content = get_table_content(shangtang_shareholder_info)
        shareholder_analysis = self.llm.call(
            "请分析以下股东信息表格内容：\n" + table_content,
            system_prompt="你是一个专业的股东信息分析师。",
            max_tokens=8192,
            temperature=0.5
        )
        
        # 整理行业信息搜索结果
        search_results_file = os.path.join(self.m.industry_dir, "all_search_results.json")
        with open(search_results_file, 'r', encoding='utf-8') as f:
            all_search_results = json.load(f)
        search_res = ""
        for company, results in all_search_results.items():
            search_res += f"【{company}搜索信息开始】\n"
            for result in results:
                search_res += f"标题: {result.get('title', '无标题')}\n"
                search_res += f"链接: {result.get('href', '无链接')}\n"
                search_res += f"摘要: {result.get('body', '无摘要')}\n"
                search_res += "----\n"
            search_res += f"【{company}搜索信息结束】\n\n"
        
        # 保存阶段一结果
        merged_results = context.get("merged_results", {})
        sensetime_valuation_report = context.get("sensetime_valuation_report", None)
        formatted_report = format_final_reports(merged_results)
        
        # 统一保存为markdown
        md_output_file = f"财务研报汇总_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 公司基础信息\n\n## 整理后公司信息\n\n{company_infos}\n\n")
            f.write(f"# 股权信息分析\n\n{shareholder_analysis}\n\n")
            f.write(f"# 行业信息搜索结果\n\n{search_res}\n\n")
            f.write(f"# 财务数据分析与两两对比\n\n{formatted_report}\n\n")
            if sensetime_valuation_report and isinstance(sensetime_valuation_report, dict):
                f.write(f"# 商汤科技估值与预测分析\n\n{sensetime_valuation_report.get('final_report', '未生成报告')}\n\n")
        
        print(f"\n✅ 第一阶段完成！基础分析报告已保存到: {md_output_file}")
        
        # 存储结果供第二阶段使用
        self.analysis_results = {
            'md_file': md_output_file,
            'company_infos': company_infos,
            'shareholder_analysis': shareholder_analysis,
            'search_res': search_res,
            'formatted_report': formatted_report,
            'sensetime_valuation_report': sensetime_valuation_report
        }
        return md_output_file
    


    #### REPORT GENERATION ACTIONS ####
    def deep_report_generation(self, context):
        """第二阶段：深度研报生成"""
        print("\n" + "="*80)
        print("🚀 开始第二阶段：深度研报生成")
        print("="*80)
        
        # 处理图片路径
        print("🖼️ 处理图片路径...")
        md_file_path = context.get("get_analysis_report", self.default_report_path)
        new_md_path = md_file_path.replace('.md', '_images.md')
        images_dir = os.path.join(os.path.dirname(md_file_path), 'images')
        extract_images_from_markdown(md_file_path, images_dir, new_md_path)
        
        # 加载报告内容
        report_content = load_report_content(new_md_path)
        background = get_background()
        
        # 生成大纲
        print("\n📋 生成报告大纲...")
        parts = generate_outline(self.llm, background, report_content)
        
        # 分段生成深度研报
        print("\n✍️ 开始分段生成深度研报...")
        full_report = ['# 商汤科技公司研报\n']
        prev_content = ''
        
        for idx, part in enumerate(parts):
            part_title = part.get('part_title', f'部分{idx+1}')
            print(f"\n  正在生成：{part_title}")
            is_last = (idx == len(parts) - 1)
            section_text = generate_section(
                self.llm, part_title, prev_content, background, report_content, is_last
            )
            full_report.append(section_text)
            print(f"  ✅ 已完成：{part_title}")
            prev_content = '\n'.join(full_report)
        
        # 保存最终报告
        final_report = '\n\n'.join(full_report)
        output_file = f"深度财务研报分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        save_markdown(final_report, output_file)
        
        # 格式化和转换
        print("\n🎨 格式化报告...")
        format_markdown(output_file)
        
        print("\n📄 转换为Word文档...")
        convert_to_docx(output_file)
        
        return {"deep_report_file": output_file, "status": "completed"}

    #### 行业研报数据收集工具 ####
    def get_industry_overview(self, context):
        """获取行业概况"""
        industry_name = self.p.get_config().get("industry", "人工智能")
        print(f"🔍 收集行业概况：{industry_name}")
        return self.industry_collector.get_industry_overview(industry_name)
    
    def get_industry_chain_analysis(self, context):
        """获取产业链分析"""
        industry_name = self.p.get_config().get("industry", "人工智能")
        print(f"🔗 分析产业链：{industry_name}")
        return self.industry_collector.get_industry_chain_analysis(industry_name)
    
    def get_industry_policy_impact(self, context):
        """获取行业政策影响"""
        industry_name = self.p.get_config().get("industry", "人工智能")
        print(f"📜 收集政策影响：{industry_name}")
        return self.industry_collector.get_industry_policy_impact(industry_name)
    
    def get_industry_technology_trends(self, context):
        """获取行业技术发展趋势"""
        industry_name = self.p.get_config().get("industry", "人工智能")
        print(f"🚀 分析技术趋势：{industry_name}")
        return self.industry_collector.get_industry_technology_trends(industry_name)
    
    def get_industry_association_reports(self, context):
        """获取行业协会报告"""
        industry_name = self.p.get_config().get("industry", "人工智能")
        print(f"📊 收集协会报告：{industry_name}")
        return self.industry_collector.get_industry_association_reports(industry_name)
    
    def get_industry_market_scale(self, context):
        """获取行业市场规模"""
        industry_name = self.p.get_config().get("industry", "人工智能")
        print(f"📈 分析市场规模：{industry_name}")
        return self.industry_collector.get_industry_market_scale(industry_name)
    
    def get_leading_companies_data(self, context):
        """获取行业龙头企业数据"""
        industry_name = self.p.get_config().get("industry", "人工智能")
        print(f"🏢 收集龙头企业数据：{industry_name}")
        
        # 搜索行业龙头企业
        search_engine = SearchEngine("sogou")
        search_query = f"{industry_name} 龙头企业 上市公司 排名"
        search_results = list(search_engine.search(search_query, max_results=10))

        # 保存搜索结果
        filename = f"{industry_name}_leading_companies.json"
        filepath = os.path.join(self.m.industry_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(search_results, f, ensure_ascii=False, indent=2)
        
        return search_results

    #### 宏观经济数据收集工具 ####
    def get_gdp_data(self, context):
        """获取GDP数据"""
        country = self.p.get_config().get("country", "中国")
        print(f"📊 收集GDP数据：{country}")
        return self.macro_collector.get_gdp_data(country)
    
    def get_cpi_data(self, context):
        """获取CPI数据"""
        country = self.p.get_config().get("country", "中国")
        print(f"💰 收集CPI数据：{country}")
        return self.macro_collector.get_cpi_data(country)
    
    def get_interest_rate_data(self, context):
        """获取利率数据"""
        country = self.p.get_config().get("country", "中国")
        print(f"📈 收集利率数据：{country}")
        return self.macro_collector.get_interest_rate_data(country)
    
    def get_exchange_rate_data(self, context):
        """获取汇率数据"""
        base_currency = self.p.get_config().get("base_currency", "人民币")
        target_currency = self.p.get_config().get("target_currency", "美元")
        print(f"💱 收集汇率数据：{base_currency}-{target_currency}")
        return self.macro_collector.get_exchange_rate_data(base_currency, target_currency)
    
    def get_federal_reserve_data(self, context):
        """获取美联储数据"""
        print("🏦 收集美联储利率数据")
        return self.macro_collector.get_federal_reserve_data()
    
    def get_policy_reports(self, context):
        """获取政策报告"""
        country = self.p.get_config().get("country", "中国")
        print(f"📜 收集政策报告：{country}")
        return self.macro_collector.get_policy_reports(country)
    
    def get_macro_industry_impact(self, context):
        """获取宏观对行业的影响"""
        industry_name = self.p.get_config().get("industry", "科技行业")
        print(f"🌐 分析宏观对行业影响：{industry_name}")
        return self.macro_collector.get_industry_policy_impact(industry_name)

    def _gather_industry_data(self, context, industry_name):
        """整合之前收集的行业数据"""
        collected_data = {}
        
        # 从context中获取数据
        overview_data = context.get("get_industry_overview", {})
        chain_data = context.get("get_industry_chain_analysis", {})
        leading_companies_data = context.get("get_leading_companies_data", [])
        market_scale_data = context.get("get_industry_market_scale", {})
        policy_data = context.get("get_industry_policy_impact", {})
        tech_trends_data = context.get("get_industry_technology_trends", {})
        association_data = context.get("get_industry_association_reports", {})
        
        # 从文件中加载数据（如果context中没有）
        if not overview_data:
            overview_file = os.path.join(self.m.industry_dir, f"{industry_name}_overview.json")
            if os.path.exists(overview_file):
                with open(overview_file, 'r', encoding='utf-8') as f:
                    overview_data = json.load(f)
        
        if not chain_data:
            chain_file = os.path.join(self.m.industry_dir, f"{industry_name}_chain_analysis.json")
            if os.path.exists(chain_file):
                with open(chain_file, 'r', encoding='utf-8') as f:
                    chain_data = json.load(f)
        
        if not leading_companies_data:
            companies_file = os.path.join(self.m.industry_dir, f"{industry_name}_leading_companies.json")
            if os.path.exists(companies_file):
                with open(companies_file, 'r', encoding='utf-8') as f:
                    leading_companies_data = json.load(f)
        
        if not market_scale_data:
            market_file = os.path.join(self.m.industry_dir, f"{industry_name}_market_scale.json")
            if os.path.exists(market_file):
                with open(market_file, 'r', encoding='utf-8') as f:
                    market_scale_data = json.load(f)
        
        # 整理数据
        if overview_data:
            collected_data['overview'] = self._format_search_results(overview_data, "行业概况")
        
        if chain_data:
            collected_data['chain_analysis'] = self._format_search_results(chain_data, "产业链分析")
        
        if leading_companies_data:
            collected_data['leading_companies'] = self._format_search_results_list(leading_companies_data, "龙头企业")
        
        if market_scale_data:
            collected_data['market_scale'] = self._format_search_results(market_scale_data, "市场规模")
        
        if policy_data:
            collected_data['policy_impact'] = self._format_search_results(policy_data, "政策影响")
        
        if tech_trends_data:
            collected_data['tech_trends'] = self._format_search_results(tech_trends_data, "技术趋势")
            
        if association_data:
            collected_data['association_reports'] = self._format_search_results(association_data, "协会报告")
        
        return collected_data
    
    def _format_search_results(self, data, data_type):
        """格式化搜索结果数据"""
        if not data:
            return f"暂无{data_type}数据"
        
        formatted_text = f"\n=== {data_type} ===\n"
        
        for query, results in data.items():
            formatted_text += f"\n【{query}】\n"
            for i, result in enumerate(results[:3], 1):  # 只取前3个结果
                title = result.get('title', '无标题')
                description = result.get('description', result.get('body', '无描述'))
                url = result.get('url', result.get('href', ''))
                
                formatted_text += f"{i}. {title}\n"
                if description:
                    # 截取描述的前200字符
                    desc_short = description[:200] + "..." if len(description) > 200 else description
                    formatted_text += f"   摘要: {desc_short}\n"
                if url:
                    formatted_text += f"   链接: {url}\n"
                formatted_text += "\n"
        
        return formatted_text
    
    def _format_search_results_list(self, data_list, data_type):
        """格式化搜索结果列表"""
        if not data_list:
            return f"暂无{data_type}数据"
        
        formatted_text = f"\n=== {data_type} ===\n"
        
        for i, result in enumerate(data_list[:5], 1):  # 只取前5个结果
            title = result.get('title', '无标题')
            description = result.get('description', result.get('body', '无描述'))
            url = result.get('url', result.get('href', ''))
            
            formatted_text += f"{i}. {title}\n"
            if description:
                desc_short = description[:200] + "..." if len(description) > 200 else description
                formatted_text += f"   摘要: {desc_short}\n"
            if url:
                formatted_text += f"   链接: {url}\n"
            formatted_text += "\n"
        
        return formatted_text

    #### 分析工具扩展 ####
    def analyze_industry_structure(self, context):
        """分析行业结构"""
        print("🏗️ 分析行业结构")
        industry_name = self.p.get_config().get("industry", "人工智能")
        
        # 整合之前收集的数据
        collected_data = self._gather_industry_data(context, industry_name)
        
        if not collected_data:
            raise ValueError("缺少行业数据，请先执行数据收集步骤")
        
        # 构建包含实际数据的分析prompt
        analysis_prompt = f"""
        基于以下收集到的{industry_name}行业实际数据，请进行深入的行业结构分析：

        === 行业概况数据 ===
        {collected_data.get('overview', '暂无数据')}

        === 产业链数据 ===
        {collected_data.get('chain_analysis', '暂无数据')}

        === 龙头企业数据 ===
        {collected_data.get('leading_companies', '暂无数据')}

        === 市场规模数据 ===
        {collected_data.get('market_scale', '暂无数据')}

        请基于以上真实数据分析：
        1. 行业发展阶段和成熟度（引用具体数据支撑）
        2. 市场集中度和竞争格局（基于龙头企业和市场数据）
        3. 产业链分工和价值分布（基于产业链数据）
        4. 主要参与者和商业模式（基于企业数据）
        
        请确保分析结论有数据支撑，避免空泛描述。
        """
        
        return self.llm.call(analysis_prompt, system_prompt="你是一位专业的行业分析师，请基于提供的真实数据进行分析")
    
    def analyze_industry_trends(self, context):
        """分析行业发展趋势"""
        print("📈 分析行业发展趋势")
        industry_name = self.p.get_config().get("industry", "人工智能")
        
        # 整合之前收集的数据
        collected_data = self._gather_industry_data(context, industry_name)
        
        if not collected_data:
            return "缺少行业数据，请先执行数据收集步骤"
        
        # 构建包含实际数据的分析prompt
        analysis_prompt = f"""
        基于以下收集到的{industry_name}行业实际数据，请进行深入的行业发展趋势分析：

        === 技术趋势数据 ===
        {collected_data.get('tech_trends', '暂无数据')}

        === 市场规模数据 ===
        {collected_data.get('market_scale', '暂无数据')}

        === 政策影响数据 ===
        {collected_data.get('policy_impact', '暂无数据')}

        === 协会报告数据 ===
        {collected_data.get('association_reports', '暂无数据')}

        请基于以上真实数据分析：
        1. 技术发展趋势和创新方向（引用具体技术数据）
        2. 市场规模增长预测（基于真实市场数据）
        3. 政策环境变化影响（基于政策数据分析）
        4. 未来3-5年发展前景（综合各项数据预测）
        
        请确保分析结论有数据支撑，避免空泛描述。
        """
        
        return self.llm.call(analysis_prompt, system_prompt="你是一位资深的行业研究专家，请基于提供的真实数据进行分析")
    
    def _gather_macro_data(self, context, country="中国"):
        """整合之前收集的宏观经济数据"""
        collected_data = {}
        
        # 从context中获取数据
        gdp_data = context.get("get_gdp_data", {})
        cpi_data = context.get("get_cpi_data", {})
        interest_rate_data = context.get("get_interest_rate_data", {})
        exchange_rate_data = context.get("get_exchange_rate_data", {})
        fed_data = context.get("get_federal_reserve_data", {})
        policy_data = context.get("get_policy_reports", {})
        industry_impact_data = context.get("get_macro_industry_impact", {})
        
        # 从文件中加载数据（如果context中没有）
        if not gdp_data:
            gdp_file = os.path.join("./data", "macro", f"{country}_gdp_data.json")
            if os.path.exists(gdp_file):
                with open(gdp_file, 'r', encoding='utf-8') as f:
                    gdp_data = json.load(f)
        
        if not cpi_data:
            cpi_file = os.path.join("./data", "macro", f"{country}_cpi_data.json")
            if os.path.exists(cpi_file):
                with open(cpi_file, 'r', encoding='utf-8') as f:
                    cpi_data = json.load(f)

        if not interest_rate_data:
            interest_rate_file = os.path.join("./data", "macro", f"{country}_interest_rate_data.json")
            if os.path.exists(interest_rate_file):
                with open(interest_rate_file, 'r', encoding='utf-8') as f:
                    interest_rate_data = json.load(f)
        
        if not exchange_rate_data:
            exchange_rate_file = os.path.join("./data", "macro", f"exchange_rate.json")
            if os.path.exists(exchange_rate_file):
                with open(exchange_rate_file, 'r', encoding='utf-8') as f:
                    exchange_rate_data = json.load(f)

        if not fed_data:
            fed_rate_file = os.path.join("./data", "macro", "fed_interest_rate_data.json")
            if os.path.exists(fed_rate_file):
                with open(fed_rate_file, 'r', encoding='utf-8') as f:
                    fed_data = json.load(f)

        if not policy_data:
            policy_file = os.path.join("./data", "macro", f"{country}_policy_reports.json")
            if os.path.exists(policy_file):
                with open(policy_file, 'r', encoding='utf-8') as f:
                    policy_data = json.load(f)
        
        if not industry_impact_data:
            industry_impact_file = os.path.join("./data", "macro", "policy_impact.json")
            if os.path.exists(industry_impact_file):
                with open(industry_impact_file, 'r', encoding='utf-8') as f:
                    industry_impact_data = json.load(f)

        # 整理数据
        if gdp_data:
            collected_data['gdp'] = self._format_search_results(gdp_data, "GDP数据")
        
        if cpi_data:
            collected_data['cpi'] = self._format_search_results(cpi_data, "CPI数据")
        
        if interest_rate_data:
            collected_data['interest_rate'] = self._format_search_results(interest_rate_data, "利率数据")
        
        if exchange_rate_data:
            collected_data['exchange_rate'] = self._format_search_results(exchange_rate_data, "汇率数据")
        
        if fed_data:
            collected_data['federal_reserve'] = self._format_search_results(fed_data, "美联储数据")
        
        if policy_data:
            collected_data['policy'] = self._format_search_results(policy_data, "政策报告")
        
        if industry_impact_data:
            collected_data['industry_impact'] = self._format_search_results(industry_impact_data, "行业影响")
        
        return collected_data

    def analyze_macro_trends(self, context):
        """分析宏观经济趋势"""
        print("🌍 分析宏观经济趋势")
        country = self.p.get_config().get("country", "中国")
        
        # 整合之前收集的数据
        collected_data = self._gather_macro_data(context, country)
        
        if not collected_data:
            return "缺少宏观经济数据，请先执行数据收集步骤"
        
        # 构建包含实际数据的分析prompt
        analysis_prompt = f"""
        基于以下收集到的{country}宏观经济实际数据，请进行深入的宏观经济趋势分析：

        === GDP数据 ===
        {collected_data.get('gdp', '暂无数据')}

        === CPI通胀数据 ===
        {collected_data.get('cpi', '暂无数据')}

        === 利率数据 ===
        {collected_data.get('interest_rate', '暂无数据')}

        === 汇率数据 ===
        {collected_data.get('exchange_rate', '暂无数据')}

        === 美联储政策数据 ===
        {collected_data.get('federal_reserve', '暂无数据')}

        === 政策报告数据 ===
        {collected_data.get('policy', '暂无数据')}

        请基于以上真实数据分析：
        1. GDP增长动力和结构变化（引用具体GDP数据）
        2. 通胀压力和货币政策走向（基于CPI和利率数据）
        3. 汇率环境对经济的影响（基于汇率数据分析）
        4. 国际环境对国内经济的影响（结合美联储政策数据）
        
        请确保分析结论有数据支撑，避免空泛描述。
        """
        
        return self.llm.call(analysis_prompt, system_prompt="你是一位宏观经济分析专家，请基于提供的真实数据进行分析")
    
    def analyze_policy_impact(self, context):
        """分析政策影响"""
        print("📜 分析政策影响")
        country = self.p.get_config().get("country", "中国")
        industry_name = self.p.get_config().get("industry", "")
        
        # 整合宏观政策数据
        macro_data = self._gather_macro_data(context, country)
        
        # 如果是行业研报，还要整合行业政策数据
        industry_data = {}
        if industry_name and self.current_report_type == ReportType.INDUSTRY:
            industry_data = self._gather_industry_data(context, industry_name)
        
        if not macro_data and not industry_data:
            return "缺少政策数据，请先执行数据收集步骤"
        
        # 构建包含实际数据的分析prompt
        analysis_prompt = f"""
        基于以下收集到的政策数据，请分析当前政策环境对经济和相关行业的影响：

        === 宏观政策数据 ===
        {macro_data.get('policy', '暂无宏观政策数据')}

        === GDP相关政策影响 ===
        {macro_data.get('gdp', '暂无GDP数据')}

        === 货币政策数据 ===
        {macro_data.get('interest_rate', '暂无利率政策数据')}
        {macro_data.get('federal_reserve', '暂无美联储政策数据')}
        """
        
        # 如果有行业数据，添加行业政策部分
        if industry_data:
            analysis_prompt += f"""
        === 行业政策数据 ===
        {industry_data.get('policy_impact', '暂无行业政策数据')}
        """
        
        analysis_prompt += """
        请基于以上真实数据分析：
        1. 财政政策的刺激效果和持续性（引用具体政策数据）
        2. 货币政策的传导机制和效果（基于利率和流动性数据）
        3. 行业政策对特定领域的扶持力度（如有行业数据）
        4. 政策协调性和未来政策预期（综合各项政策数据）
        
        请确保分析结论有数据支撑，避免空泛描述。
        """
        
        return self.llm.call(analysis_prompt, system_prompt="你是一位政策分析专家，请基于提供的真实数据进行分析")

    #### 报告生成工具扩展 ####
    def generate_industry_report(self, context):
        """分段生成行业研报"""
        print("📝 分段生成行业研报")
        industry_name = self.p.get_config().get("industry", "人工智能")

        # 提取分析结果和数据
        industry_analysis = context.get("analyze_industry_structure", "")
        trends_analysis = context.get("analyze_industry_trends", "")
        collected_data = self._gather_industry_data(context, industry_name)

        def call_llm_section(title, instruction, content):
            prompt = f"""
你是一位专业的行业研究分析师，请根据以下内容撰写《{industry_name}》行业研报中的【{title}】部分。

【写作要求】
- {instruction}
- 使用专业术语，逻辑严密，语言精炼，篇幅控制在500-800字。

【原始分析数据】
{content}
"""
            return self.llm.call(prompt, system_prompt="你是一位专业的行业研究分析师，擅长撰写深度行业研报。")

        # 每段生成内容
        sections = []

        sections.append(("行业概况", call_llm_section(
            "行业概况", "介绍行业整体情况，包括发展背景、主要应用领域与现状",
            collected_data.get('overview', '暂无数据'))))

        sections.append(("产业链分析", call_llm_section(
            "产业链分析", "从上游、中游、下游三个环节分析行业的产业链结构",
            industry_analysis)))

        sections.append(("市场规模与竞争格局", call_llm_section(
            "市场规模与竞争格局", "说明市场规模、主要企业、竞争态势",
            collected_data.get('market_scale', '') + "\n" + collected_data.get('leading_companies', ''))))

        sections.append(("技术发展趋势", call_llm_section(
            "技术发展趋势", "提炼行业中的核心技术演进路径和创新方向",
            trends_analysis)))

        sections.append(("政策环境分析", call_llm_section(
            "政策环境分析", "梳理政策法规、补贴等对行业的影响",
            collected_data.get('policy', '暂无数据'))))

        sections.append(("投资机会与风险", call_llm_section(
            "投资机会与风险", "综合以上内容，提出投资建议并指出潜在风险",
            "\n".join([s[1] for s in sections[:5]]))))  # 前5段为基础

        # 组装 Markdown 格式研报
        report_content = f"# {industry_name}行业研究报告\n\n"
        for title, content in sections:
            report_content += f"## {title}\n\n{content.strip()}\n\n"

        # 保存文件
        output_file = f"{industry_name}行业研报_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        save_markdown(report_content, output_file)

        return {"industry_report_file": output_file, "content": report_content}
    

    def generate_macro_report(self, context):
        """分段生成宏观经济研报"""
        print("📊 生成宏观经济研报（分段）")
        country = self.p.get_config().get("country", "中国")

        macro_trends = context.get("analyze_macro_trends", "")
        policy_impact = context.get("analyze_policy_impact", "")
        collected_data = self._gather_macro_data(context, country)

        # 限制输入数据长度
        def truncate(txt, maxlen=500):
            return txt[:maxlen] + "..." if len(txt) > maxlen else txt

        # 分段模板
        sections = [
            {
                "title": "1. 宏观经济概况",
                "instruction": f"""你是一位资深宏观分析师，请根据以下中国宏观数据分析整体经济状况：
    - GDP: {truncate(collected_data.get('gdp', '暂无'))}
    - CPI: {truncate(collected_data.get('cpi', '暂无'))}
    请输出一段500字左右的分析。"""
            },
            {
                "title": "2. 货币政策分析",
                "instruction": f"""请分析中国当前货币政策趋势，基于以下信息：
    - 利率情况: {truncate(collected_data.get('interest_rate', '暂无'))}
    - 宏观趋势: {truncate(macro_trends)}
    要求：梳理货币政策变化背景，结合利率或流动性进行分析。"""
            },
            {
                "title": "3. 财政政策分析",
                "instruction": f"""请分析当前财政政策对宏观经济的影响，数据参考：
    - 政策摘要: {truncate(policy_impact)}
    - 政策文件原文: {truncate(collected_data.get('policy', '暂无'))}"""
            },
            {
                "title": "4. 国际环境影响",
                "instruction": f"""请分析国际宏观环境对中国的影响，包括汇率、美联储加息等内容。
    - 汇率走势: {truncate(collected_data.get('exchange_rate', '暂无'))}"""
            },
            {
                "title": "5. 行业影响分析",
                "instruction": f"""结合上面的宏观分析，判断中国哪些行业受益/受挫，并说明原因。"""
            },
            {
                "title": "6. 投资策略建议",
                "instruction": f"""基于上述宏观判断，提出具体的投资建议，标明推荐资产类别及原因。"""
            }
        ]

        def safe_llm_call(prompt, sys_prompt=None, retries=3):
            for i in range(retries):
                try:
                    return self.llm.call(prompt, system_prompt=sys_prompt)
                except Exception as e:
                    print(f"⚠️ LLM调用失败（第{i+1}次）: {e}")
                    time.sleep(1)
            return "【生成失败】连接错误"

        report_parts = []
        for i, sec in enumerate(sections):
            print(f"✍️ 正在生成 {sec['title']}")
            content = safe_llm_call(
                sec["instruction"],
                sys_prompt="你是一位资深宏观经济研究员，请输出结构清晰、专业、简洁的分析内容。"
            )
            section_text = f"## {sec['title']}\n\n{content.strip()}\n"
            report_parts.append(section_text)

        # 拼接完整内容
        full_report = "# 宏观经济研报\n\n" + "\n".join(report_parts)

        # 保存
        output_file = f"{country}宏观经济研报_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        save_markdown(full_report, output_file)

        print(f"✅ 报告生成完毕，保存至 {output_file}")
        return {
            "macro_report_file": output_file,
            "content": full_report
        }
