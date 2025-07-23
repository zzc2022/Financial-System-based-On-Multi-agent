# coordinator_agent.py
from typing import Dict, List, Any, Optional, Tuple
import json
import time
import os
from datetime import datetime
from .base_agent import BaseAgent
from .memory import AgentMemory
from .profile import AgentProfile


class GlobalMemoryManager:
    """
    全局记忆管理器 - 拥有最高记忆权限
    可以访问和管理所有agent的记忆数据
    """
    
    def __init__(self, base_memory: AgentMemory):
        self.base_memory = base_memory
        self.agent_memories: Dict[str, AgentMemory] = {}
        self.global_context = {}
        
    def register_agent_memory(self, agent_name: str, memory: AgentMemory):
        """注册agent的记忆模块"""
        self.agent_memories[agent_name] = memory
        
    def get_global_memory_snapshot(self) -> Dict[str, Any]:
        """获取全局记忆快照"""
        snapshot = {
            "global_context": self.global_context,
            "base_memory_stats": self.base_memory.get_memory_stats(),
            "agent_memories": {}
        }
        
        for agent_name, memory in self.agent_memories.items():
            snapshot["agent_memories"][agent_name] = {
                "stats": memory.get_memory_stats(),
                "context": memory.context_all(),
                "persistent_keys": memory.list_persistent_keys()
            }
            
        return snapshot
    
    def cross_agent_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """跨agent语义搜索"""
        all_results = []
        
        # 搜索基础记忆
        base_results = self.base_memory.semantic_search(query, top_k, threshold=0.6)
        for result in base_results:
            result["source"] = "base_memory"
            all_results.append(result)
            
        # 搜索各个agent的记忆
        for agent_name, memory in self.agent_memories.items():
            agent_results = memory.semantic_search(query, top_k, threshold=0.6)
            for result in agent_results:
                result["source"] = f"agent_{agent_name}"
                all_results.append(result)
        
        # 按相似度排序并返回top_k
        all_results.sort(key=lambda x: x["similarity"], reverse=True)
        return all_results[:top_k]
    
    def get_agent_progress(self, agent_name: str) -> Dict[str, Any]:
        """获取特定agent的进展"""
        if agent_name not in self.agent_memories:
            return {}
            
        memory = self.agent_memories[agent_name]
        return {
            "context": memory.context_all(),
            "completed_tasks": memory.context_get("completed_tasks") or [],
            "failed_tasks": memory.context_get("failed_tasks") or [],
            "current_status": memory.context_get("status") or "unknown",
            "last_result": memory.context_get("last_result")
        }
    
    def update_global_context(self, key: str, value: Any):
        """更新全局上下文"""
        self.global_context[key] = value
        self.base_memory.context_set(f"global_{key}", value)


class ProgressTracker:
    """
    项目进展跟踪器
    跟踪整个多agent系统的执行进展
    """
    
    def __init__(self, memory_manager: GlobalMemoryManager):
        self.memory_manager = memory_manager
        self.project_state = {
            "start_time": datetime.now().isoformat(),
            "current_phase": "初始化",
            "completed_phases": [],
            "agent_status": {},
            "overall_progress": 0.0,
            "task_dependencies": {},
            "execution_history": []
        }
        
    def update_agent_status(self, agent_name: str, status: str, details: Dict[str, Any] = None):
        """更新agent状态"""
        self.project_state["agent_status"][agent_name] = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        # 记录执行历史
        self.project_state["execution_history"].append({
            "agent": agent_name,
            "action": status,
            "timestamp": datetime.now().isoformat(),
            "details": details
        })
        
        self.memory_manager.update_global_context("project_state", self.project_state)
    
    def complete_phase(self, phase_name: str):
        """完成一个阶段"""
        if phase_name not in self.project_state["completed_phases"]:
            self.project_state["completed_phases"].append(phase_name)
            
        # 更新总体进度
        total_phases = len(self.project_state["completed_phases"]) + 1  # +1 for current phase
        self.project_state["overall_progress"] = len(self.project_state["completed_phases"]) / total_phases
        
        self.memory_manager.update_global_context("project_state", self.project_state)
    
    def set_current_phase(self, phase_name: str):
        """设置当前阶段"""
        self.project_state["current_phase"] = phase_name
        self.memory_manager.update_global_context("project_state", self.project_state)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进展摘要"""
        return {
            "current_phase": self.project_state["current_phase"],
            "overall_progress": self.project_state["overall_progress"],
            "completed_phases": self.project_state["completed_phases"],
            "active_agents": [
                name for name, info in self.project_state["agent_status"].items()
                if info["status"] in ["running", "active"]
            ],
            "completed_agents": [
                name for name, info in self.project_state["agent_status"].items()
                if info["status"] == "completed"
            ],
            "failed_agents": [
                name for name, info in self.project_state["agent_status"].items()
                if info["status"] == "failed"
            ]
        }


class AgentScheduler:
    """
    Agent调度器
    负责决定agent的执行顺序和依赖关系
    """
    
    def __init__(self, memory_manager: GlobalMemoryManager, progress_tracker: ProgressTracker):
        self.memory_manager = memory_manager
        self.progress_tracker = progress_tracker
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.agent_dependencies: Dict[str, List[str]] = {}
        self.execution_queue: List[str] = []
        
    def register_agent(self, agent: BaseAgent, dependencies: List[str] = None):
        """注册agent及其依赖关系"""
        agent_name = agent.profile.name
        self.agent_registry[agent_name] = agent
        self.agent_dependencies[agent_name] = dependencies or []
        
        # 注册agent的记忆到全局管理器
        self.memory_manager.register_agent_memory(agent_name, agent.memory)
        
    def can_execute_agent(self, agent_name: str) -> bool:
        """检查agent是否可以执行（依赖是否满足）"""
        dependencies = self.agent_dependencies.get(agent_name, [])
        completed_agents = self.progress_tracker.get_progress_summary()["completed_agents"]
        
        return all(dep in completed_agents for dep in dependencies)
    
    def get_next_agent(self) -> Optional[str]:
        """获取下一个应该执行的agent"""
        progress = self.progress_tracker.get_progress_summary()
        completed = set(progress["completed_agents"])
        failed = set(progress["failed_agents"])
        active = set(progress["active_agents"])
        
        for agent_name in self.agent_registry.keys():
            if (agent_name not in completed and 
                agent_name not in failed and 
                agent_name not in active and
                self.can_execute_agent(agent_name)):
                return agent_name
                
        return None
    
    def execute_agent(self, agent_name: str) -> Dict[str, Any]:
        """执行指定的agent"""
        if agent_name not in self.agent_registry:
            return {"error": f"Agent {agent_name} not found"}
            
        agent = self.agent_registry[agent_name]
        
        # 更新状态为运行中
        self.progress_tracker.update_agent_status(agent_name, "running", {
            "start_time": datetime.now().isoformat()
        })
        
        try:
            # 执行agent
            result = agent.run()
            
            # 更新状态为完成
            self.progress_tracker.update_agent_status(agent_name, "completed", {
                "end_time": datetime.now().isoformat(),
                "result_keys": list(result.keys()) if isinstance(result, dict) else []
            })
            
            # 保存结果到全局记忆
            self.memory_manager.update_global_context(f"{agent_name}_result", result)
            
            return result
            
        except Exception as e:
            # 更新状态为失败
            self.progress_tracker.update_agent_status(agent_name, "failed", {
                "end_time": datetime.now().isoformat(),
                "error": str(e)
            })
            return {"error": str(e)}


class CoordinatorActionToolset:
    """
    Coordinator Agent的工具集
    提供调度、监控、决策等功能
    """
    
    def __init__(self, profile: AgentProfile, memory: AgentMemory, llm, llm_config,
                 scheduler: AgentScheduler, progress_tracker: ProgressTracker, 
                 memory_manager: GlobalMemoryManager):
        self.profile = profile
        self.memory = memory
        self.llm = llm
        self.llm_config = llm_config
        self.scheduler = scheduler
        self.progress_tracker = progress_tracker
        self.memory_manager = memory_manager
    
    def analyze_global_progress(self, context: Dict[str, Any]) -> str:
        """分析全局进展"""
        progress = self.progress_tracker.get_progress_summary()
        memory_snapshot = self.memory_manager.get_global_memory_snapshot()
        
        analysis = f"""
## 项目进展分析

**当前阶段**: {progress['current_phase']}
**总体进度**: {progress['overall_progress']:.1%}
**已完成阶段**: {', '.join(progress['completed_phases'])}

### Agent状态
- **已完成**: {', '.join(progress['completed_agents'])}
- **运行中**: {', '.join(progress['active_agents'])}
- **失败**: {', '.join(progress['failed_agents'])}

### 记忆统计
- **基础记忆**: {memory_snapshot['base_memory_stats']}
- **Agent记忆数量**: {len(memory_snapshot['agent_memories'])}
        """
        
        return analysis
    
    def decide_next_action(self, context: Dict[str, Any]) -> str:
        """决定下一步行动"""
        next_agent = self.scheduler.get_next_agent()
        if next_agent:
            return f"execute_agent_{next_agent}"
        
        progress = self.progress_tracker.get_progress_summary()
        if progress['active_agents']:
            return "wait_for_completion"
        elif progress['failed_agents']:
            return "handle_failures"
        else:
            return "complete_project"
    
    def execute_next_agent(self, context: Dict[str, Any]) -> str:
        """执行下一个agent"""
        next_agent = self.scheduler.get_next_agent()
        if not next_agent:
            return "没有可执行的agent"
            
        result = self.scheduler.execute_agent(next_agent)
        return f"已执行 {next_agent}, 结果: {type(result).__name__}"
    
    def check_dependencies(self, context: Dict[str, Any]) -> str:
        """检查依赖关系"""
        dependency_status = {}
        for agent_name, deps in self.scheduler.agent_dependencies.items():
            dependency_status[agent_name] = {
                "dependencies": deps,
                "can_execute": self.scheduler.can_execute_agent(agent_name)
            }
        
        return json.dumps(dependency_status, indent=2, ensure_ascii=False)
    
    def search_knowledge(self, context: Dict[str, Any]) -> str:
        """搜索知识库"""
        query = context.get("search_query", "财务分析进展")
        results = self.memory_manager.cross_agent_search(query, top_k=5)
        
        summary = "## 知识搜索结果\n\n"
        for i, result in enumerate(results, 1):
            summary += f"**{i}. [{result['source']}] (相似度: {result['similarity']:.3f})**\n"
            summary += f"{result['text'][:200]}...\n\n"
            
        return summary
    
    def generate_status_report(self, context: Dict[str, Any]) -> str:
        """生成状态报告"""
        progress = self.progress_tracker.get_progress_summary()
        memory_stats = self.memory_manager.get_global_memory_snapshot()
        
        report = f"""
# 多Agent系统状态报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 执行进展
- 当前阶段: {progress['current_phase']}
- 总体进度: {progress['overall_progress']:.1%}
- 已完成: {len(progress['completed_agents'])} agents
- 失败: {len(progress['failed_agents'])} agents

## 记忆使用情况
- 全局上下文项目: {len(memory_stats['global_context'])}
- 基础记忆大小: {memory_stats['base_memory_stats']['context_size']}
- 注册Agent数量: {len(memory_stats['agent_memories'])}

## 下一步建议
{self.decide_next_action(context)}
        """
        
        return report


class CoordinatorAgent(BaseAgent):
    """
    协调器Agent - 负责管理和调度其他Agent
    具有最高的记忆权限和全局视图
    """
    
    def __init__(self, profile: AgentProfile, memory: AgentMemory, planner, llm, llm_config):
        # 初始化全局记忆管理器
        self.memory_manager = GlobalMemoryManager(memory)
        
        # 初始化进展跟踪器
        self.progress_tracker = ProgressTracker(self.memory_manager)
        
        # 初始化调度器
        self.scheduler = AgentScheduler(self.memory_manager, self.progress_tracker)
        
        # 创建专用的action工具集
        action = CoordinatorActionToolset(
            profile, memory, llm, llm_config,
            self.scheduler, self.progress_tracker, self.memory_manager
        )
        
        # 定义coordinator专用工具
        toolset = [
            "analyze_global_progress",
            "decide_next_action", 
            "execute_next_agent",
            "check_dependencies",
            "search_knowledge",
            "generate_status_report"
        ]
        
        # 调用父类初始化
        super().__init__(profile, memory, planner, action, toolset)
        
        # 设置初始阶段
        self.progress_tracker.set_current_phase("系统初始化")
    
    def register_agent(self, agent: BaseAgent, dependencies: List[str] = None):
        """注册要管理的agent"""
        self.scheduler.register_agent(agent, dependencies)
    
    def execute_workflow(self) -> Dict[str, Any]:
        """执行完整的工作流程"""
        self.progress_tracker.set_current_phase("工作流程执行")
        
        workflow_results = {}
        
        while True:
            next_agent = self.scheduler.get_next_agent()
            if not next_agent:
                # 检查是否还有agent在运行
                active_agents = self.progress_tracker.get_progress_summary()["active_agents"]
                if not active_agents:
                    break
                    
                # 等待运行中的agent完成
                time.sleep(1)
                continue
            
            # 执行下一个agent
            print(f"🎯 Coordinator: 执行 {next_agent}")
            result = self.scheduler.execute_agent(next_agent)
            workflow_results[next_agent] = result
            
            # 生成阶段报告
            if next_agent in ["DataAgent", "AnalysisAgent"]:
                self.progress_tracker.complete_phase(f"{next_agent}完成")
        
        self.progress_tracker.set_current_phase("工作流程完成")
        return workflow_results
    
    def get_global_summary(self) -> str:
        """获取全局摘要"""
        return self.action.generate_status_report({})
    
    def run(self) -> Dict[str, Any]:
        """运行coordinator（可以用于单独的coordinator任务）"""
        return super().run()