# action_financial.py
from toolset.utils.get_financial_statements import get_all_financial_statements, save_financial_statements_to_csv
from toolset.utils.get_stock_intro import get_stock_intro, save_stock_intro_to_txt
from toolset.utils.get_shareholder_info import get_shareholder_info, get_table_content
from toolset.utils.search_engine import SearchEngine
from toolset.utils.identify_competitors import identify_competitors_with_ai
from toolset.utils.markdown_utils import extract_images_from_markdown, save_markdown, format_markdown, convert_to_docx
from toolset.utils.analyzer import Analyzer
from typing import List
from toolset.utils.report_generation_helper import extract_images_from_markdown, load_report_content, get_background, generate_outline, generate_section
from duckduckgo_search import DDGS
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

    #### DATA COLLECTION ACTIONS ####
    def get_competitor_listed_companies(self, context):

        result = identify_competitors_with_ai(
            api_key=self.cfg.api_key,
            base_url=self.cfg.base_url,
            model_name=self.cfg.model,
            company_name=self.p.get_config()['company']
        )
        result = [c for c in result if c.get('market') != "未上市"]
        return result

    def get_all_financial_data(self, context):
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
        
        print(f"\n✅ 第二阶段完成！深度研报已保存到: {output_file}")
        return output_file