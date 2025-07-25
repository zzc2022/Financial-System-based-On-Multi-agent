# main_multi_report.py - 支持多种研报类型的主程序
from BaseAgent.base_agent import BaseAgent
from BaseAgent.profile import AgentProfile
from BaseAgent.memory import AgentMemory
from BaseAgent.planner import AgentPlanner
from BaseAgent.coordinator_agent import CoordinatorAgent
from toolset.action_financial import FinancialActionToolset
from toolset.utils.report_type_config import ReportTypeConfig, ReportType
from config.llm_config import LLMConfig
from config.embedding_config import create_embedding_config
from utils.llm_helper import LLMHelper
import os
from dotenv import load_dotenv
import sys

load_dotenv()

def create_multi_report_system(instruction: str):
    """创建支持多研报类型的系统"""
    
    # 初始化组件
    llm_config = LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    )
    
    # 初始化嵌入模型
    embedding_config = create_embedding_config("qwen")
    embedding_model = embedding_config.get_model()
    
    # 识别研报类型
    report_config = ReportTypeConfig()
    report_type = report_config.identify_report_type(instruction)
    report_type_name = report_config.get_config(report_type)["name"]
    
    print(f"🎯 检测到研报类型: {report_type_name}")
    print(f"📝 指令内容: {instruction}")
    
    # 根据研报类型设置不同的配置
    if report_type == ReportType.COMPANY:
        config = {
            "company": "商汤科技",
            "code": "00020", 
            "market": "HK",
            "report_type": "company",
            "instruction": instruction
        }
    elif report_type == ReportType.INDUSTRY:
        config = {
            "industry": "人工智能",
            "report_type": "industry", 
            "instruction": instruction
        }
    elif report_type == ReportType.MACRO:
        config = {
            "country": "中国",
            "report_type": "macro",
            "instruction": instruction
        }
    
    ##### 数据提取Agent #####
    data_agent_profile = AgentProfile(
        name="DataAgent",
        role=f"负责{report_type_name}相关数据的采集与清洗",
        objectives=report_config.get_config(report_type)["data_requirements"],
        tools=report_config.get_data_tools(report_type),
        knowledge=f"具备{report_type_name}数据收集的专业知识",
        interaction={
            "input": "研报类型和目标参数",
            "output": "结构化的数据文件"
        },
        memory_type="short-term",
        config=config
    )
    
    memory = AgentMemory("./data/financials", "./data/info", "./data/industry", embedding_model)
    llm = LLMHelper(llm_config)
    planner = AgentPlanner(data_agent_profile, llm)
    action = FinancialActionToolset(data_agent_profile, memory, llm, llm_config)
    
    # 创建数据提取agent
    agent_d = BaseAgent(data_agent_profile, memory, planner, action, 
                       report_config.get_data_tools(report_type))
    
    ##### 分析Agent #####
    analysis_agent_profile = AgentProfile(
        name="AnalysisAgent", 
        role=f"负责{report_type_name}数据分析与报告生成",
        objectives=[f"对{report_type_name}数据进行深度分析", "生成专业的分析报告"],
        tools=report_config.get_analysis_tools(report_type),
        knowledge=f"熟悉{report_type_name}分析方法和报告撰写",
        interaction={"input": "采集到的数据", "output": "分析报告"},
        memory_type="short-term",
        config=config
    )
    
    # 创建分析agent
    agent_a = BaseAgent(
        profile=analysis_agent_profile,
        memory=memory,
        planner=AgentPlanner(analysis_agent_profile, llm, 
                           prompt_path="prompts/planner/toolset_illustration.yaml"),
        action=FinancialActionToolset(analysis_agent_profile, memory, llm, llm_config),
        toolset=report_config.get_analysis_tools(report_type)
    )
    
    ##### Coordinator Agent #####
    coordinator_profile = AgentProfile(
        name="CoordinatorAgent",
        role=f"负责{report_type_name}生成的多agent系统调度",
        objectives=[
            f"管理{report_type_name}生成流程",
            "协调各agent执行顺序", 
            "监控生成进展",
            "提供全局记忆管理"
        ],
        tools=["analyze_global_progress", "decide_next_action", "execute_next_agent",
               "check_dependencies", "search_knowledge", "generate_status_report"],
        knowledge=f"具备{report_type_name}生成流程的全局把控能力",
        interaction={"input": "系统状态", "output": "调度决策和进展报告"},
        memory_type="global",
        config=config
    )
    
    # 创建coordinator agent
    coordinator = CoordinatorAgent(
        profile=coordinator_profile,
        memory=memory,
        planner=AgentPlanner(coordinator_profile, llm),
        llm=llm,
        llm_config=llm_config
    )
    
    return coordinator, agent_d, agent_a, report_type

def main():
    """主函数"""
    # 从命令行参数或用户输入获取指令 
    if len(sys.argv) > 1:
        instruction = " ".join(sys.argv[1:])
    else:
        print("请输入研报生成指令:")
        print("例如:")
        print("  - 生成商汤科技的公司研报")  
        print("  - 生成人工智能行业研报")
        print("  - 生成宏观经济研报")
        instruction = input("指令: ").strip()
    
    if not instruction:
        print("❌ 未提供有效指令")
        return
        
    try:
        # 创建多研报类型系统
        coordinator, agent_d, agent_a, report_type = create_multi_report_system(instruction)
        
        # 注册agent到coordinator，设置依赖关系
        coordinator.register_agent(agent_d, dependencies=[])  # 数据agent没有依赖
        coordinator.register_agent(agent_a, dependencies=["DataAgent"])  # 分析agent依赖数据agent
        
        report_type_name = coordinator.report_config.get_config(report_type)["name"]
        
        print(f"\n🎯 启动{report_type_name}生成系统...")
        print("📊 Agent依赖关系: DataAgent -> AnalysisAgent")
        print("🚀 开始执行工作流程...\n")
        
        # 执行工作流程
        workflow_results = coordinator.execute_workflow()
        
        print("\n" + "="*60)
        print(f"📋 {report_type_name}生成完成")
        print("="*60)
        
        # 显示各个agent的执行结果
        for agent_name, result in workflow_results.items():
            print(f"\n🔍 {agent_name} 执行结果:")
            if isinstance(result, dict):
                for k, v in result.items():
                    if isinstance(v, str) and len(v) > 200:
                        print(f"  [{k}] {v[:200]}...")
                    else:
                        print(f"  [{k}] {v if isinstance(v, str) else '[结构化数据]'}")
            else:
                print(f"  {result}")
        
        # 生成全局摘要报告
        print("\n" + "="*60)
        print(f"📊 {report_type_name}系统执行摘要")
        print("="*60)
        global_summary = coordinator.get_global_summary()
        print(global_summary)
        
    except Exception as e:
        print(f"❌ 系统执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()