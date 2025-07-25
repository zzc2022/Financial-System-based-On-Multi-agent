# 多Agent财务研报系统 - 支持三种研报类型

## 系统概述

本系统是一个基于多Agent架构的智能研报生成系统，支持三种不同类型的研报生成：

1. **公司研报** - 针对特定上市公司的深度分析
2. **行业研报** - 针对特定行业的全面分析 
3. **宏观经济研报** - 宏观经济形势分析与投资策略

## 系统架构

### 核心组件

- **CoordinatorAgent**: 总调度器，具有最高记忆权限，负责管理整个研报生成流程
- **DataAgent**: 数据收集器，根据研报类型智能选择相应的数据收集工具
- **AnalysisAgent**: 数据分析器，根据研报类型执行对应的分析任务

### 新增功能

1. **智能研报类型识别**: 系统可以根据用户输入自动识别需要生成的研报类型
2. **动态工具集配置**: 根据研报类型自动配置agent的工具集
3. **全局记忆管理**: Coordinator拥有访问所有agent记忆的权限
4.图片自动插入**: 修复了图片插入问题，系统生成的图表会自动插入到研报中

## 使用方法

### 基本用法

```bash
# 使用新的多研报系统
python main_multi_report.py "生成商汤科技的公司研报"
python main_multi_report.py "生成人工智能行业研报" 
python main_multi_report.py "生成宏观经济研报"
```

### 支持的指令示例

#### 公司研报
- "生成商汤科技的公司研报"
- "企业分析报告"
- "个股研报"

#### 行业研报  
- "生成人工智能行业研报"
- "行业分析报告"
- "产业分析"

#### 宏观经济研报
- "生成宏观经济研报"
- "宏观分析报告"
- "经济形势分析"

## 研报类型对比

### 公司研报
**数据需求**: 
- 目标企业财务三大报表
- 同行企业财务数据  
- 股权结构信息
- 公司基本信息
- 竞争对手分析

**主要工具**:
```
数据收集: get_competitor_listed_companies, get_all_financial_data, get_all_company_info
分析工具: analyze_companies_in_directory, run_comparison_analysis, evaluation
```

### 行业研报
**数据需求**:
- 行业发展现状与规模
- 产业链上下游分析
- 行业协会年报数据
- 相关政策影响
- 技术发展趋势

**主要工具**:
```
数据收集: get_industry_overview, get_industry_chain_analysis, get_industry_policy_impact
分析工具: analyze_industry_structure, analyze_industry_trends, generate_industry_report
```

### 宏观经济研报
**数据需求**:
- GDP、CPI、利率、汇率数据
- 政府政策报告
- 美联储利率政策
- 行业政策影响

**主要工具**:
```  
数据收集: get_gdp_data, get_cpi_data, get_interest_rate_data, get_federal_reserve_data
分析工具: analyze_macro_trends, analyze_policy_impact, generate_macro_report
```

## 文件结构

```
├── main_multi_report.py              # 新的多研报类型主程序
├── BaseAgent/
│   ├── coordinator_agent.py          # 增强的协调器Agent
│   └── ...
├── toolset/
│   ├── action_financial.py           # 扩展的工具集
│   └── utils/
│       ├── industry_data_collector.py # 行业数据收集器
│       ├── macro_data_collector.py    # 宏观数据收集器
│       ├── report_type_config.py      # 研报类型配置
│       └── ...
└── prompts/
    └── template/
        ├── company_report_template.yaml   # 公司研报模板
        ├── industry_report_template.yaml  # 行业研报模板
        └── macro_report_template.yaml     # 宏观研报模板
```

## 特色功能

### 1. 智能类型识别
系统通过关键词匹配自动识别研报类型：
- 包含"公司"、"企业" → 公司研报
- 包含"行业"、"产业" → 行业研报  
- 包含"宏观"、"经济" → 宏观研报

### 2. 动态工具配置
不同研报类型的agent会自动获得相应的工具集，无需手动配置。

### 3. 全局记忆管理
CoordinatorAgent拥有最高记忆权限，可以：
- 访问所有agent的长短期记忆
- 进行跨agent的语义搜索
- 跟踪项目整体进展
- 生成全局摘要报告

### 4. 图片自动插入
修复了之前图片无法插入的问题：
- 自动发现分析过程中生成的图表
- 智能插入到markdown报告中
- 支持图片文件管理和路径优化

## 输出文件

根据研报类型，系统会生成不同的输出文件：

- **公司研报**: `深度财务研报分析_YYYYMMDD_HHMMSS.md`
- **行业研报**: `{行业名}行业研报_YYYYMMDD_HHMMSS.md`  
- **宏观研报**: `宏观经济研报_YYYYMMDD_HHMMSS.md`

同时生成对应的images目录存放图表文件。

## 系统优势

1. **统一架构**: 三种研报类型共享同一套agent架构，便于维护和扩展
2. **智能识别**: 自动识别研报类型，用户体验友好
3. **专业模板**: 每种研报类型都有专业的分析框架和模板
4. **全面数据**: 覆盖公司、行业、宏观三个层面的数据收集
5. **高度可扩展**: 易于添加新的研报类型和分析工具

## 注意事项

1. 确保已正确配置OpenAI API密钥
2. 网络搜索需要稳定的网络连接
3. 首次运行可能需要较长时间进行数据收集
4. 建议根据实际需求调整配置参数

通过这个升级版系统，您现在可以轻松生成三种不同类型的专业研报，满足不同层面的分析需求！