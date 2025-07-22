from BaseAgent.base_agent import BaseAgent
from BaseAgent.profile import AgentProfile
from BaseAgent.memory import AgentMemory
from BaseAgent.planner import AgentPlanner
from toolset.action_financial import FinancialActionToolset
from config.llm_config import LLMConfig
from config.embedding_config import create_embedding_config
from utils.llm_helper import LLMHelper
import os
from dotenv import load_dotenv

load_dotenv()

# 初始化组件
llm_config = LLMConfig(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
)

# 初始化嵌入模型
embedding_config = create_embedding_config("qwen")
embedding_model = embedding_config.get_model()

##### 数据提取Agent #####
data_agent_profile = AgentProfile(
    name="DataAgent",
    role="负责数据采集与清洗，涵盖财务报表、公司信息、行业情报等",
    objectives=[
        "采集目标公司财务三大表数据",
        "收集主要竞争对手名单及其财务数据",
        "获取公司基本介绍和行业信息"
    ],
    tools=["get_financials", "get_stock_info", "web_search"],
    knowledge="具备港股和A股市场结构与财报格式知识，理解基本财务术语",
    interaction={
        "input": "公司名称与代码",
        "output": "结构化的数据表（CSV）、文本信息（TXT/JSON）"
    },
    memory_type="short-term",
    config={
        "company": "商汤科技",
        "code": "00020",
        "market": "HK"
    }
)

memory = AgentMemory("./data/financials", "./data/info", "./data/industry", embedding_model)
llm = LLMHelper(llm_config)
planner = AgentPlanner(data_agent_profile, llm)
action = FinancialActionToolset(data_agent_profile, memory, llm, llm_config)

toolset = [fn for fn in dir(action) if not fn.startswith("__") and callable(getattr(action, fn))]

agent_d = BaseAgent(data_agent_profile, memory, planner, action, toolset)

result = agent_d.run()

for k, v in result.items():
    print(f"[{k}]\n{v if isinstance(v, str) else '[结构化数据]'}")

analysis_agent_profile = AgentProfile(
    name="AnalysisAgent",
    role="负责数据分析、图表生成、公司估值",
    objectives=[
        "对公司财务数据进行分析，生成图表和报告",
        "完成公司之间的对比分析",
        "完成目标公司估值建模与预测"
    ],
    tools=["analyze_companies_in_directory", "run_comparison_analysis", "merge_reports", "evaluation", "get_analysis_report", "deep_report_generation"],
    knowledge="熟悉财务指标、图表分析、估值方法（DCF、PE等）",
    interaction={"input": "CSV 文件", "output": "报告/图表/估值模型"},
    memory_type="short-term",
    config={"company": "商汤科技", "code": "00020", "market": "HK"}
)

agent_a = BaseAgent(
    profile=analysis_agent_profile,
    memory=memory,
    planner=AgentPlanner(analysis_agent_profile, llm, prompt_path="prompts/planner/toolset_illustration.yaml"),
    action=FinancialActionToolset(analysis_agent_profile, memory, llm, llm_config),
    toolset=["analyze_companies_in_directory", "run_comparison_analysis", "merge_reports", "evaluation", "get_analysis_report", "deep_report_generation"]
)

result_a = agent_a.run()
for k, v in result_a.items():
    print(f"[{k}]\n{v if isinstance(v, str) else '[结构化数据]'}")

# context_generator_profile = AgentProfile(
#     name="ReportGenerationAgent",
#     role="负责撰写深度研报、组织章节内容、格式化报告并导出文档",
#     objectives=[
#         "加载分析阶段生成的初步报告内容",
#         "提取图片并生成完整研报章节结构",
#         "逐节生成研报内容并汇总为完整报告",
#         "将 Markdown 报告格式化并导出为 Word 文档"
#     ],
#     tools=[
#         "load_raw_report",
#         "prepare_images",
#         "generate_outline",
#         "generate_section",
#         "assemble_report",
#         "format_report",
#         "export_to_docx"
#     ],
#     knowledge="具备投资分析报告的结构设计能力，熟悉 Markdown 报告撰写，了解如何结合财务分析内容和图表组织成文，能生成规范的研究文档",
#     interaction={
#         "input": "基础分析 Markdown 报告路径（md 文件）",
#         "output": "完整的 Markdown 研报及 Word 文档"
#     },
#     memory_type="short-term",
#     config={
#         "company": "商汤科技",
#         "report_type": "深度研报",
#         "doc_style": "财务研究格式",
#         "background": '''
# 本报告基于自动化采集与分析流程，涵盖如下环节：
# - 公司基础信息来源于年报、公开接口
# - 财务数据来自东方财富
# - 估值模型由大语言模型生成
# - 所有内容由多智能体协作完成
# '''
#     }
# )

# agent_c = BaseAgent(
#     profile=context_generator_profile,
#     memory=memory,
#     planner=AgentPlanner(context_generator_profile, llm),
#     action=FinancialActionToolset(context_generator_profile, memory, llm, llm_config),
#     toolset=["load_raw_report", "prepare_images", "generate_outline", "generate_section", "assemble_report", "format_report", "export_to_docx"]
# )
# result_c = agent_c.run()
# for k, v in result_c.items():
#     print(f"[{k}]\n{v if isinstance(v, str) else '[结构化数据]'}")