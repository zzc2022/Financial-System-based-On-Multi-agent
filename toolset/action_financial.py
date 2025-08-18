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
from pathlib import Path

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
        
        # 🎯 新增：报告路径存储属性
        self.generated_report_paths = {
            "company_report": None,      # 公司研报路径
            "industry_report": None,     # 行业研报路径  
            "macro_report": None,        # 宏观研报路径
            "deep_report": None,         # 深度研报路径
            "analysis_report": None,     # 分析报告路径
            "latest_report": None        # 最新生成的报告路径
        }
        
        # 确保报告目录存在
        os.makedirs(self.reports_dir, exist_ok=True)
        
    def _update_report_path(self, report_type: str, file_path: str):
        """更新报告路径到类属性中"""
        self.generated_report_paths[report_type] = file_path
        self.generated_report_paths["latest_report"] = file_path
        print(f"📄 已保存{report_type}路径: {file_path}")
    
    def get_latest_report_path(self) -> str:
        """获取最新生成的报告路径"""
        return self.generated_report_paths.get("latest_report")
        
    def get_report_path(self, report_type: str) -> str:
        """获取指定类型的报告路径"""
        return self.generated_report_paths.get(report_type)
    
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
        
        # 🔍 查找并添加session目录中的图表
        charts_section = self._find_and_add_session_charts()
        
        # 统一保存为markdown
        md_output_file = f"财务研报汇总_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 公司基础信息\n\n## 整理后公司信息\n\n{company_infos}\n\n")
            f.write(f"# 股权信息分析\n\n{shareholder_analysis}\n\n")
            f.write(f"# 行业信息搜索结果\n\n{search_res}\n\n")
            f.write(f"# 财务数据分析与两两对比\n\n{formatted_report}\n\n")
            if sensetime_valuation_report and isinstance(sensetime_valuation_report, dict):
                f.write(f"# 商汤科技估值与预测分析\n\n{sensetime_valuation_report.get('final_report', '未生成报告')}\n\n")
            # 添加图表部分
            if charts_section:
                f.write(charts_section)
        
        print(f"\n✅ 第一阶段完成！基础分析报告已保存到: {md_output_file}")
        
        # 🎯 保存报告路径到类属性
        self._update_report_path("analysis_report", md_output_file)
        
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
    
    def _find_and_add_session_charts(self):
        """查找session目录中的图表并生成markdown引用"""
        import glob
        
        print("🔍 搜索session目录中的分析图表...")
        data_financials_dir = os.path.join(os.getcwd(), "data", "financials")
        
        if not os.path.exists(data_financials_dir):
            print("⚠️ 未找到data/financials目录")
            return ""
        
        # 找到所有session目录
        session_dirs = [d for d in os.listdir(data_financials_dir) if d.startswith('session_')]
        if not session_dirs:
            print("⚠️ 未找到session目录")
            return ""
        
        # 按修改时间排序，选择最新的session
        session_dirs.sort(key=lambda x: os.path.getmtime(os.path.join(data_financials_dir, x)), reverse=True)
        latest_session = session_dirs[0]
        session_path = os.path.join(data_financials_dir, latest_session)
        
        print(f"📊 使用最新session目录: {latest_session}")
        
        # 查找所有图片文件
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg']:
            image_files.extend(glob.glob(os.path.join(session_path, ext)))
        
        if not image_files:
            print("⚠️ session目录中未发现图表文件")
            return ""
        
        print(f"📈 发现 {len(image_files)} 个分析图表")
        
        # 生成图表展示部分
        charts_section = "\n\n# 财务分析图表\n\n"
        charts_section += "以下是系统自动生成的财务分析图表：\n\n"
        
        for img_file in image_files:
            filename = os.path.basename(img_file)
            # 使用相对路径引用，方便后续处理
            relative_path = f"./data/financials/{latest_session}/{filename}"
            
            # 生成更友好的图表名称
            chart_name = filename.replace('_', ' ').replace('-', ' ').replace('.png', '').replace('.jpg', '').replace('.jpeg', '').title()
            
            charts_section += f"## {chart_name}\n\n"
            charts_section += f"![{chart_name}]({relative_path})\n\n"
            print(f"✅ 已添加图表引用: {chart_name}")
        
        return charts_section
    


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
        
        # 🎯 保存报告路径到类属性
        self._update_report_path("deep_report", output_file)
        self._update_report_path("company_report", output_file)  # 公司研报也指向深度报告
        
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
        output_file = f"行业研报_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        save_markdown(report_content, output_file)

        # 🎯 保存报告路径到类属性
        self._update_report_path("industry_report", output_file)

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

        # 🎯 保存报告路径到类属性
        self._update_report_path("macro_report", output_file)

        print(f"✅ 报告生成完毕，保存至 {output_file}")
        return {
            "macro_report_file": output_file,
            "content": full_report
        }

    #### 研报评价工具 ####
    def load_report_content(self, context):
        """加载研报内容进行评价"""
        # 1.获取报告内容
        base_path = Path(".")
        files = []
        if self.current_report_type == ReportType.COMPANY:
            files = base_path.glob("深度财务研报分析*.md")
        elif self.current_report_type == ReportType.INDUSTRY:
            files = base_path.glob("行业研报*.md")
        elif self.current_report_type == ReportType.MACRO:
            files = base_path.glob("中国宏观经济研报*.md")
        else:
            print(f"未知的报告类型: {self.current_report_type}")
            return

        content = ""
        for file_path in files:
            content = file_path.read_text(encoding="utf-8")
            print(f"===== {file_path} =====")
            print(content[:200])

        # 2.保存到context
        if content:
            self.m.context_set("report_content", content)
        else:
            print("未找到匹配的报告文件")

    def identify_report_type_for_evaluation(self, context):
        """识别研报类型以选择合适的评价标准"""
        report_content = self.m.context_get("report_content")
        if not report_content:
            return "请先加载研报内容"
        
        # 使用现有的报告类型配置识别
        report_type = self.report_config.identify_report_type(report_content)
        
        self.m.context_set("evaluation_report_type", report_type)
        self.m.context_set("report_type_identified", True)
        
        type_name = self.report_config.get_config(report_type)['name']
        return f"识别研报类型为: {type_name}"
    
    def evaluate_content_completeness(self, context):
        """评价内容完整性"""
        return self._evaluate_report_dimension(context, "content_completeness", "内容完整性")
    
    def evaluate_data_accuracy(self, context):
        """评价数据准确性"""
        return self._evaluate_report_dimension(context, "data_accuracy", "数据准确性")
    
    def evaluate_analysis_depth(self, context):
        """评价分析深度"""
        return self._evaluate_report_dimension(context, "analysis_depth", "分析深度")
    
    def evaluate_logical_coherence(self, context):
        """评价逻辑一致性"""
        return self._evaluate_report_dimension(context, "logical_coherence", "逻辑一致性")
    
    def evaluate_professional_quality(self, context):
        """评价专业性"""
        return self._evaluate_report_dimension(context, "professional_quality", "专业性")
    
    def evaluate_market_insight(self, context):
        """评价市场洞察力（行业研报专用）"""
        return self._evaluate_report_dimension(context, "market_insight", "市场洞察力")
    
    def evaluate_macroeconomic_insight(self, context):
        """评价宏观洞察力（宏观研报专用）"""
        return self._evaluate_report_dimension(context, "macroeconomic_insight", "宏观洞察力")
    
    def calculate_overall_evaluation_score(self, context):
        """计算综合评分"""
        report_type = self.m.context_get("evaluation_report_type")
        if not report_type:
            return {"error": "请先识别研报类型"}
        
        # 评价标准权重配置
        criteria_weights = self._get_evaluation_criteria(report_type)
        
        overall_score = 0.0
        detailed_scores = {}
        
        # 汇总各维度评分
        for dimension_name, weight in criteria_weights.items():
            score_data = self.m.context_get(f"{dimension_name}_evaluation")
            if score_data and isinstance(score_data, dict):
                dimension_score = score_data.get("score", 0)
                weighted_score = dimension_score * weight
                overall_score += weighted_score
                
                detailed_scores[dimension_name] = {
                    "score": dimension_score,
                    "weight": weight,
                    "weighted_score": weighted_score,
                    "feedback": score_data.get("feedback", "")
                }
        
        # 评分等级
        grade = self._get_evaluation_grade(overall_score)
        
        final_result = {
            "overall_score": round(overall_score, 2),
            "grade": grade,
            "detailed_scores": detailed_scores,
            "evaluation_time": datetime.now().isoformat(),
            "report_type": self.report_config.get_config(report_type)["name"]
        }
        
        self.m.context_set("final_evaluation", final_result)
        return final_result
    
    def generate_evaluation_report(self, context):
        """生成评价报告"""
        final_evaluation = self.m.context_get("final_evaluation")
        if not final_evaluation:
            return "请先完成综合评分计算"
        
        report_template = f"""
# 研报质量评价报告

## 基本信息
- **研报类型**: {final_evaluation['report_type']}
- **评价时间**: {final_evaluation['evaluation_time']}
- **综合评分**: {final_evaluation['overall_score']}/100
- **评价等级**: {final_evaluation['grade']}

## 详细评分

{self._format_detailed_scores(final_evaluation['detailed_scores'])}

## 评价总结

{self._generate_evaluation_summary(final_evaluation)}

## 评分说明
- A级 (90-100分): 优秀，达到行业领先水平
- B级 (80-89分): 良好，符合专业标准  
- C级 (70-79分): 合格，基本满足要求
- D级 (60-69分): 需要改进
- F级 (0-59分): 不合格，需要重新撰写
        """
        
        self.m.context_set("evaluation_report", report_template.strip())
        return "评价报告生成完成"
    
    def save_evaluation_result(self, context):
        """保存评价结果"""
        evaluation_report = self.m.context_get("evaluation_report")
        final_evaluation = self.m.context_get("final_evaluation")
        
        if not evaluation_report or not final_evaluation:
            return "请先生成评价报告"
        
        # 确定保存路径
        report_path = "./"
        if report_path:
            base_dir = os.path.dirname(report_path)
            base_name = os.path.splitext(os.path.basename(report_path))[0]
        else:
            base_dir = os.path.join(self.m.data_dir, "evaluation")
            base_name = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        os.makedirs(base_dir, exist_ok=True)
        
        # 保存评价报告
        report_file = os.path.join(base_dir, f"{base_name}_evaluation.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(evaluation_report)
        
        # 保存评分数据
        json_file = os.path.join(base_dir, f"{base_name}_scores.json") 
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(final_evaluation, f, ensure_ascii=False, indent=2)
        
        return f"评价结果已保存:\n- 报告: {report_file}\n- 数据: {json_file}"
    
    def _evaluate_report_dimension(self, context, dimension, dimension_name):
        """通用维度评价方法"""
        report_content = self.m.context_get("report_content")
        report_type = self.m.context_get("evaluation_report_type")
        
        if not report_content or not report_type:
            return {"error": "请先加载研报内容并识别类型"}
        
        # 获取评价标准
        criteria = self._get_dimension_criteria(report_type, dimension)
        if not criteria:
            return {"error": f"该研报类型不支持{dimension_name}评价"}
        
        # 构建评价prompt
        evaluation_prompt = self._build_evaluation_prompt(
            report_content, dimension_name, criteria, report_type
        )
        
        try:
            # 调用LLM进行评价
            response = self.llm.call(
                evaluation_prompt,
                system_prompt="你是专业的金融研报评价专家，请客观公正地进行评价。",
                temperature=0.3
            )
            
            # 解析评分结果
            result = self._parse_evaluation_result(response, dimension_name)
            self.m.context_set(f"{dimension}_evaluation", result)
            
            return result
            
        except Exception as e:
            return {"error": f"{dimension_name}评价失败: {str(e)}"}
    
    def _get_evaluation_criteria(self, report_type):
        """获取评价标准权重"""
        criteria_mapping = {
            ReportType.COMPANY: {
                "content_completeness": 0.25,
                "data_accuracy": 0.20,
                "analysis_depth": 0.25,
                "logical_coherence": 0.15,
                "professional_quality": 0.15
            },
            ReportType.INDUSTRY: {
                "content_completeness": 0.25,
                "market_insight": 0.25,
                "data_accuracy": 0.20,
                "analysis_depth": 0.15,
                "professional_quality": 0.15
            },
            ReportType.MACRO: {
                "macroeconomic_insight": 0.30,
                "data_accuracy": 0.20,
                "analysis_depth": 0.20,
                "logical_coherence": 0.15,
                "professional_quality": 0.15
            }
        }
        return criteria_mapping.get(report_type, criteria_mapping[ReportType.COMPANY])
    
    def _get_dimension_criteria(self, report_type, dimension):
        """获取具体维度的评价细则"""
        criteria_details = {
            ReportType.COMPANY: {
                "content_completeness": ["公司概况描述是否全面", "财务分析是否深入", "竞争对手分析是否到位", "投资建议是否明确", "风险提示是否充分"],
                "data_accuracy": ["财务数据引用是否准确", "数据计算是否正确", "数据来源是否可靠", "数据时效性是否合适"],
                "analysis_depth": ["财务分析是否深入透彻", "业务模式分析是否清晰", "行业地位分析是否准确", "估值分析是否合理"],
                "logical_coherence": ["论证逻辑是否清晰", "结论与分析是否一致", "章节间逻辑是否连贯"],
                "professional_quality": ["专业术语使用是否准确", "分析方法是否科学", "表达是否专业规范"]
            },
            ReportType.INDUSTRY: {
                "content_completeness": ["行业概况是否全面", "产业链分析是否完整", "市场规模分析是否准确", "技术趋势分析是否到位", "政策分析是否充分"],
                "market_insight": ["行业发展趋势判断是否准确", "竞争格局分析是否深入", "市场机会识别是否精准", "行业痛点分析是否到位"],
                "data_accuracy": ["数据覆盖范围是否广泛", "数据维度是否全面", "历史数据是否充分", "预测数据是否合理"],
                "analysis_depth": ["分析框架是否科学", "分析方法是否合适", "分析层次是否清晰"],
                "professional_quality": ["投资建议是否具体", "风险提示是否实用", "结论是否有指导意义"]
            },
            ReportType.MACRO: {
                "macroeconomic_insight": ["宏观趋势判断是否准确", "政策解读是否深入", "国际影响分析是否到位", "经济周期判断是否合理"],
                "data_accuracy": ["数据来源是否权威", "数据处理是否科学", "数据解读是否准确", "预测数据是否合理"],
                "analysis_depth": ["货币政策分析是否深入", "财政政策影响是否准确", "政策传导机制是否清晰", "政策效果预判是否合理"],
                "logical_coherence": ["趋势预测是否合理", "风险预警是否及时", "机会识别是否准确", "时间窗口判断是否合适"],
                "professional_quality": ["投资策略是否具体", "资产配置建议是否合理", "时机把握是否准确", "风险控制建议是否有效"]
            }
        }
        
        type_criteria = criteria_details.get(report_type, criteria_details[ReportType.COMPANY])
        return type_criteria.get(dimension, [])
    
    def _build_evaluation_prompt(self, report_content, dimension_name, criteria, report_type):
        """构建评价prompt"""
        type_name = self.report_config.get_config(report_type)['name']
        
        prompt = f"""
你是一位专业的金融研报评价专家，请对以下{type_name}在"{dimension_name}"维度进行客观评价。

## 评价标准
{dimension_name}主要包括以下方面：
"""
        
        for i, criterion in enumerate(criteria, 1):
            prompt += f"{i}. {criterion}\n"
        
        # 截取报告内容（避免过长）
        content_preview = report_content[:4000] + "..." if len(report_content) > 4000 else report_content
        
        prompt += f"""

## 研报内容
{content_preview}

## 评价要求
请仔细阅读研报内容，根据上述评价标准进行评价：
1. 逐项检查是否满足评价标准
2. 给出0-100分的评分（分数越高表示质量越好）
3. 提供具体的评价反馈，包括优点和不足
4. 评价要客观公正，有理有据

## 输出格式
请严格按照以下JSON格式输出（不要添加其他内容）：
{{
    "score": 评分数字(0-100的整数),
    "feedback": "具体的评价反馈，包括优点和不足，200-300字"
}}
"""
        
        return prompt
    
    def _parse_evaluation_result(self, response, dimension_name):
        """解析LLM评价结果"""
        try:
            # 尝试从响应中提取JSON
            import re
            json_pattern = r'\{[^{}]*"score"[^{}]*"feedback"[^{}]*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # 验证必要字段
                if "score" in result and "feedback" in result:
                    # 确保分数在有效范围内
                    result["score"] = max(0, min(100, int(result["score"])))
                    return result
            
            # 如果JSON解析失败，尝试简单解析
            score_match = re.search(r'(\d+)', response)
            score = int(score_match.group(1)) if score_match else 70
            
            return {
                "score": max(0, min(100, score)),
                "feedback": f"{dimension_name}评价：" + response[:300],
            }
            
        except Exception as e:
            return {
                "score": 70,
                "feedback": f"评价解析失败: {str(e)}，原始回复：{response[:200]}",
            }
    
    def _get_evaluation_grade(self, score):
        """根据分数获取等级"""
        if score >= 90:
            return "A级 (优秀)"
        elif score >= 80:
            return "B级 (良好)"
        elif score >= 70:
            return "C级 (合格)"
        elif score >= 60:
            return "D级 (需要改进)"
        else:
            return "F级 (不合格)"
    
    def _format_detailed_scores(self, detailed_scores):
        """格式化详细评分"""
        formatted = ""
        for dimension, scores in detailed_scores.items():
            dimension_name = {
                "content_completeness": "内容完整性",
                "data_accuracy": "数据准确性", 
                "analysis_depth": "分析深度",
                "logical_coherence": "逻辑一致性",
                "professional_quality": "专业性",
                "market_insight": "市场洞察力",
                "macroeconomic_insight": "宏观洞察力"
            }.get(dimension, dimension)
            
            formatted += f"""
### {dimension_name}
- **得分**: {scores['score']}/100 (权重: {scores['weight']})
- **加权得分**: {scores['weighted_score']:.2f}
- **反馈**: {scores['feedback']}
"""
        return formatted
    
    def _generate_evaluation_summary(self, final_evaluation):
        """生成评价总结"""
        detailed_scores = final_evaluation['detailed_scores']
        overall_score = final_evaluation['overall_score']
        
        strengths = []
        improvements = []
        
        for dimension, scores in detailed_scores.items():
            if scores['score'] >= 85:
                strengths.append(f"- {dimension}: 表现优秀")
            elif scores['score'] < 70:
                improvements.append(f"- {dimension}: 需要改进")
        
        strengths_text = "\n".join(strengths) if strengths else "- 各维度表现均衡"
        improvements_text = "\n".join(improvements) if improvements else "- 整体质量良好，继续保持"
        
        summary = f"""
**优势分析:**
{strengths_text}

**改进建议:**
{improvements_text}

**总体评价:**
该研报综合评分为{overall_score}分，{final_evaluation['grade']}。
"""
        if overall_score >= 80:
            summary += "整体质量较好，符合专业标准。"
        elif overall_score >= 70:
            summary += "基本满足要求，但仍有提升空间。"
        else:
            summary += "质量有待提高，建议重点改进薄弱环节。"
            
        return summary
