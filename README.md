# 基于多智能体的金融分析系统 (Multi-Agent Financial Analysis System)

## 项目简介

这是一个基于多智能体架构的智能金融分析系统，能够自动化生成多种类型的专业研报。系统通过协调多个专业化的智能体，实现从数据收集、分析处理到报告生成的全流程自动化。

### 核心特性

- 🤖 **多智能体协作架构**: 采用专业化分工的多Agent系统
- 📊 **多类型研报支持**: 支持公司研报、行业研报、宏观经济研报
- 🔍 **全自动数据收集**: 自动获取财务数据、公司信息、行业数据等
- 📈 **智能分析与可视化**: 生成专业图表和深度分析报告  
- 📋 **质量评价体系**: 内置评价Agent确保研报质量
- 🎯 **灵活配置系统**: 支持多种LLM和配置方案

## 系统架构

### Agent分类

1. **数据收集Agent (DataAgent)**
   - 收集财务三大报表数据
   - 获取公司基本信息和股东结构
   - 收集行业数据和宏观经济数据
   - 识别竞争对手信息

2. **分析Agent (AnalysisAgent)**
   - 财务数据分析和建模
   - 生成可视化图表
   - 对比分析和趋势预测
   - 编写分析报告

3. **评价Agent (EvaluationAgent)**
   - 评估研报质量和完整性
   - 提供专业评分和改进建议
   - 确保报告符合行业标准

4. **协调Agent (CoordinatorAgent)**
   - 管理多Agent工作流程
   - 监控执行进展
   - 提供全局记忆管理
   - 生成执行摘要

## 支持的研报类型

### 1. 公司研报 (Company Report)
- **数据要求**: 财务三大表、竞争对手数据、公司信息
- **分析内容**: 财务分析、估值建模、竞争力分析
- **输出格式**: Markdown报告 + 可视化图表

### 2. 行业研报 (Industry Report)  
- **数据要求**: 行业规模、技术趋势、政策影响、头部企业
- **分析内容**: 行业现状、发展趋势、投资机会
- **输出格式**: 行业分析报告 + 数据图表

### 3. 宏观研报 (Macro Report)
- **数据要求**: GDP、CPI、利率、汇率、政策数据
- **分析内容**: 宏观经济分析、政策影响、市场预测
- **输出格式**: 宏观分析报告 + 经济指标图表

## 安装与配置

### 环境要求

```
Python 3.8+
pandas
numpy
matplotlib
requests
openai
python-dotenv
```

### 安装步骤

1. **克隆项目**
```bash
git clone [repository-url]
cd Financial-System-based-On-Multi-agent
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**

创建 `.env` 文件:
```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4-turbo-preview
```

### 配置说明

系统支持多种LLM配置，主要配置文件：

- `config/llm_config.py`: LLM模型配置
- `config/embedding_config.py`: 向量嵌入模型配置
- `prompts/`: 各类prompt模板和配置

## 使用方法

### 基础使用

#### 1. 生成单一公司研报
```bash
python main.py
```

#### 2. 生成多类型研报
```bash
# 公司研报
python main_multi_report.py "生成商汤科技的公司研报"

# 行业研报  
python main_multi_report.py "生成人工智能行业研报"

# 宏观研报
python main_multi_report.py "生成宏观经济研报"
```

#### 3. 集成测试
```bash
python test_integration.py
```

### 高级配置

#### 修改目标公司
在 `main.py` 或 `main_multi_report.py` 中修改配置:

```python
config = {
    "company": "目标公司名称",
    "code": "股票代码", 
    "market": "交易所代码"  # HK, SH, SZ等
}
```

#### 自定义研报模板
修改 `prompts/template/` 下的YAML模板文件:
- `company_report_template.yaml`: 公司研报模板
- `industry_report_template.yaml`: 行业研报模板
- `macro_report_template.yaml`: 宏观研报模板

## 项目结构

```
Financial-System-based-On-Multi-agent/
├── BaseAgent/                    # Agent基础框架
│   ├── base_agent.py            # Agent基类
│   ├── coordinator_agent.py     # 协调Agent
│   ├── evaluation_agent.py      # 评价Agent
│   ├── memory.py               # 记忆管理
│   ├── planner.py              # 任务规划
│   └── profile.py              # Agent配置
├── config/                      # 配置管理
│   ├── llm_config.py           # LLM配置
│   └── embedding_config.py     # 嵌入模型配置
├── data/                       # 数据存储
│   ├── financials/             # 财务数据
│   ├── industry/               # 行业数据
│   ├── macro/                  # 宏观数据
│   └── info/                   # 公司信息
├── prompts/                    # Prompt模板
│   ├── planner/               # 规划模板
│   └── template/              # 研报模板
├── toolset/                    # 工具集
│   ├── action_financial.py    # 金融分析工具
│   └── utils/                 # 工具函数
├── utils/                      # 辅助工具
├── main.py                     # 单一研报主程序
├── main_multi_report.py        # 多类型研报主程序
└── test_integration.py         # 集成测试
```

## 输出示例

### 生成的文件类型

1. **分析报告** (`.md`文件)
   - 包含完整的财务分析
   - 图表引用和说明
   - 投资建议和风险提示

2. **可视化图表** (`.png`文件)
   - 财务指标趋势图
   - 同业对比图表
   - 估值分析图表

3. **数据文件** (`.csv`文件)  
   - 原始财务数据
   - 计算的财务比率
   - 分析结果数据

4. **评价报告**
   - 研报质量评分
   - 改进建议
   - 专业标准检查

### 报告存储位置

- **公司研报**: `data/financials/session_[session_id]/`
- **行业研报**: `人工智能行业研报_[timestamp].md`
- **宏观研报**: 根据配置存储在相应目录

## 核心功能模块

### 1. 数据收集模块
- **财务数据**: 从东方财富等源获取三大报表
- **公司信息**: 自动获取公司介绍、股东信息
- **行业数据**: 收集行业规模、趋势、政策等信息
- **竞争对手**: AI识别和分析主要竞争对手

### 2. 分析处理模块  
- **财务建模**: 计算各类财务比率和指标
- **趋势分析**: 时间序列分析和预测
- **对比分析**: 同业对比和基准分析
- **估值模型**: DCF、PE等估值方法

### 3. 可视化模块
- **趋势图表**: 收入、利润、现金流趋势
- **对比图表**: 多公司财务指标对比
- **结构分析**: 资产负债结构分析
- **比率分析**: 财务比率变化趋势

### 4. 报告生成模块
- **结构化撰写**: 基于模板的报告结构
- **内容生成**: AI驱动的分析内容撰写  
- **格式化输出**: Markdown格式规范化
- **多语言支持**: 中英文报告生成

## 扩展与定制

### 添加新的数据源
1. 在 `toolset/utils/` 下创建新的数据收集器
2. 在 `action_financial.py` 中注册新的方法
3. 更新相应的Agent工具集配置

### 定制分析方法
1. 修改 `toolset/utils/analyzer.py` 
2. 添加新的分析指标和算法
3. 更新可视化方法

### 创建新的研报类型
1. 在 `ReportTypeConfig` 中添加新类型
2. 创建对应的prompt模板
3. 配置相应的数据收集和分析工具

## 技术特点

### 多Agent协作
- **去中心化设计**: 每个Agent专注特定任务
- **依赖关系管理**: 自动处理Agent间依赖
- **状态同步**: 全局记忆管理确保信息共享
- **容错机制**: 失败处理和重试机制

### 智能调度
- **动态规划**: 根据任务完成情况动态调整
- **并行处理**: 支持Agent并行执行
- **进度监控**: 实时跟踪执行进展
- **资源管理**: 优化系统资源使用

### 可扩展架构
- **插件化设计**: 易于添加新功能模块  
- **配置驱动**: 通过配置文件控制行为
- **模板系统**: 支持自定义报告模板
- **API集成**: 易于集成外部数据源

## 注意事项

### 数据源限制
- 财务数据主要来源于公开信息
- 部分数据可能存在延迟
- 需要网络连接获取实时数据

### API使用
- 需要有效的OpenAI API Key
- 建议使用GPT-4等高性能模型
- 注意API调用频率限制

### 准确性声明
- 本系统生成的分析仅供参考
- 投资决策请结合专业意见
- 系统输出不构成投资建议

## 故障排除

### 常见问题

1. **API Key错误**
   - 检查 `.env` 文件配置
   - 确认API Key有效性

2. **数据获取失败**
   - 检查网络连接
   - 验证数据源可用性
   - 查看错误日志信息

3. **Agent执行异常**
   - 查看控制台错误信息
   - 检查依赖关系配置
   - 验证工具函数完整性

### 日志与调试
- 系统会在控制台输出详细执行日志
- 错误信息包含具体失败原因
- 可通过调整日志级别获取更多信息

## 贡献与支持

### 开发贡献
欢迎提交Issue和Pull Request来改进项目。

### 技术支持  
如遇技术问题，请查看项目文档或提交Issue。

### 许可证
本项目采用开源许可证，详见LICENSE文件。

---

*这个多智能体金融分析系统代表了AI在金融领域应用的前沿探索，通过智能化的协作机制，为金融分析提供了全新的解决方案。*