import os
import yaml
import requests
import shutil
from urllib.parse import urlparse
import re

def load_report_content(md_path):
        """加载报告内容"""
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()

def get_background():
    """获取背景信息"""
    return '''
本报告基于自动化采集与分析流程，涵盖如下环节：
- 公司基础信息等数据均通过akshare、公开年报、主流财经数据源自动采集。
- 财务三大报表数据来源：东方财富-港股-财务报表-三大报表 (https://emweb.securities.eastmoney.com/PC_HKF10/FinancialAnalysis/index)
- 主营业务信息来源：同花顺-主营介绍 (https://basic.10jqka.com.cn/new/000066/operate.html)
- 股东结构信息来源：同花顺-股东信息 (https://basic.10jqka.com.cn/HK0020/holder.html) 通过网页爬虫技术自动采集
- 行业信息通过DuckDuckGo等公开搜索引擎自动抓取，引用了权威新闻、研报、公司公告等。
- 财务分析、对比分析、估值与预测均由大模型（如GPT-4）自动生成，结合了行业对标、财务比率、治理结构等多维度内容。
- 相关数据与分析均在脚本自动化流程下完成，确保数据来源可追溯、分析逻辑透明。
- 详细引用与外部链接已在正文中标注。
- 数据接口说明与免责声明见文末。
'''

def generate_outline(llm, background, report_content):
    """生成大纲"""
    outline_prompt = f"""
你是一位顶级金融分析师和研报撰写专家。请基于以下背景和财务研报汇总内容，生成一份详尽的《商汤科技公司研报》分段大纲，要求：
- 以yaml格式输出，务必用```yaml和```包裹整个yaml内容，便于后续自动分割。
- 每一项为一个主要部分，每部分需包含：
- part_title: 章节标题
- part_desc: 本部分内容简介
- 章节需覆盖公司基本面、财务分析、行业对比、估值与预测、治理结构、投资建议、风险提示、数据来源等。
- 只输出yaml格式的分段大纲，不要输出正文内容。

【背景说明开始】
{background}
【背景说明结束】

【财务研报汇总内容开始】
{report_content}
【财务研报汇总内容结束】
"""
    outline_list = llm.call(
        outline_prompt,
        system_prompt="你是一位顶级金融分析师和研报撰写专家，善于结构化、分段规划输出，分段大纲必须用```yaml包裹，便于后续自动分割。",
        max_tokens=4096,
        temperature=0.3
    )
    print("\n===== 生成的分段大纲如下 =====\n")
    print(outline_list)
    try:
        if '```yaml' in outline_list:
            yaml_block = outline_list.split('```yaml')[1].split('```')[0]
        else:
            yaml_block = outline_list
        parts = yaml.safe_load(yaml_block)
        if isinstance(parts, dict):
            parts = list(parts.values())
    except Exception as e:
        print(f"[大纲yaml解析失败] {e}")
        parts = []
    return parts

def generate_section(llm, part_title, prev_content, background, report_content, is_last):
    """生成章节"""
    section_prompt = f"""
你是一位顶级金融分析师和研报撰写专家。请基于以下内容，直接输出\"{part_title}\"这一部分的完整研报内容。

**重要要求：**
1. 直接输出完整可用的研报内容，以\"## {part_title}\"开头
2. 在正文中引用数据、事实、图片等信息时，适当位置插入参考资料符号（如[1][2][3]），符号需与文末引用文献编号一致
3. **图片引用要求（务必严格遵守）：**
- 只允许引用【财务研报汇总内容】中真实存在的图片地址（格式如：./images/图片名字.png），必须与原文完全一致。
- 禁止虚构、杜撰、改编、猜测图片地址，未在【财务研报汇总内容】中出现的图片一律不得引用。
- 如需插入图片，必须先在【财务研报汇总内容】中查找，未找到则不插入图片，绝不编造图片。
- 如引用了不存在的图片，将被判为错误输出。
4. 不要输出任何【xxx开始】【xxx结束】等分隔符
5. 不要输出\"建议补充\"、\"需要添加\"等提示性语言
6. 不要编造图片地址或数据
7. 内容要详实、专业，可直接使用

**数据来源标注：**
- 财务数据标注：（数据来源：东方财富-港股-财务报表[1]）
- 主营业务信息标注：（数据来源：同花顺-主营介绍[2]）
- 股东结构信息标注：（数据来源：同花顺-股东信息网页爬虫[3]）

【本次任务】
{part_title}

【已生成前文】
{prev_content}

【背景说明开始】
{background}
【背景说明结束】

【财务研报汇总内容开始】
{report_content}
【财务研报汇总内容结束】
"""
    if is_last:
        section_prompt += """
请在本节最后以"引用文献"格式，列出所有正文中用到的参考资料，格式如下：
[1] 东方财富-港股-财务报表: https://emweb.securities.eastmoney.com/PC_HKF10/FinancialAnalysis/index
[2] 同花顺-主营介绍: https://basic.10jqka.com.cn/new/000066/operate.html
[3] 同花顺-股东信息: https://basic.10jqka.com.cn/HK0020/holder.html
"""
    section_text = llm.call(
        section_prompt,
        system_prompt="你是顶级金融分析师，专门生成完整可用的研报内容。输出必须是完整的研报正文，无需用户修改。严格禁止输出分隔符、建议性语言或虚构内容。只允许引用真实存在于【财务研报汇总内容】中的图片地址，严禁虚构、猜测、改编图片路径。如引用了不存在的图片，将被判为错误输出。",
        max_tokens=8192,
        temperature=0.5
    )
    return section_text

def save_markdown(content, output_file):
    """保存markdown文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n📁 深度研报分析已保存到: {output_file}")

def format_markdown(output_file):
    """格式化markdown文件"""
    try:
        import subprocess
        format_cmd = ["mdformat", output_file]
        subprocess.run(format_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"✅ 已用 mdformat 格式化 Markdown 文件: {output_file}")
    except Exception as e:
        print(f"[提示] mdformat 格式化失败: {e}\n请确保已安装 mdformat (pip install mdformat)")

def convert_to_docx(output_file, docx_output=None):
    """转换为Word文档"""
    if docx_output is None:
        docx_output = output_file.replace('.md', '.docx')
    try:
        import subprocess
        import os
        pandoc_cmd = [
            "pandoc",
            output_file,
            "-o",
            docx_output,
            "--standalone",
            "--resource-path=.",
            "--extract-media=."
        ]
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True, encoding='utf-8', env=env)
        print(f"\n📄 Word版报告已生成: {docx_output}")
    except subprocess.CalledProcessError as e:
        print(f"[提示] pandoc转换失败。错误信息: {e.stderr}")
        print("[建议] 检查图片路径是否正确，或使用 --extract-media 选项")
    except Exception as e:
        print(f"[提示] 若需生成Word文档，请确保已安装pandoc。当前转换失败: {e}")

# ========== 图片处理相关方法 ==========

def ensure_dir(path):
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path)

def is_url(path):
    """判断是否为URL"""
    return path.startswith('http://') or path.startswith('https://')

def download_image(url, save_path):
    """下载图片"""
    try:
        resp = requests.get(url, stream=True, timeout=10)
        resp.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in resp.iter_content(1024):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[下载失败] {url}: {e}")
        return False

def copy_image(src, dst):
    """复制图片"""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"[复制失败] {src}: {e}")
        return False

def extract_images_from_markdown(md_path, images_dir, new_md_path):
    """从markdown中提取图片，并自动发现session目录中的图片"""
    ensure_dir(images_dir)
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 首先处理已存在的图片引用
    pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    matches = pattern.findall(content)
    used_names = set()
    replace_map = {}
    not_exist_set = set()

    for img_path in matches:
        img_path = img_path.strip()
        # 取文件名
        if is_url(img_path):
            filename = os.path.basename(urlparse(img_path).path)
        else:
            filename = os.path.basename(img_path)
        # 防止重名
        base, ext = os.path.splitext(filename)
        i = 1
        new_filename = filename
        while new_filename in used_names:
            new_filename = f"{base}_{i}{ext}"
            i += 1
        used_names.add(new_filename)
        new_img_path = os.path.join(images_dir, new_filename)
        # 下载或复制
        img_exists = True
        
        if is_url(img_path):
            # 下载网络图片
            try:
                response = requests.get(img_path, stream=True)
                response.raise_for_status()
                with open(new_img_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            except Exception as e:
                img_exists = False
                not_exist_set.add(img_path)
                print(f"下载图片失败 {img_path}: {e}")
        else:
            # 复制本地图片 - 使用绝对路径处理
            original_path = img_path
            if not os.path.isabs(img_path):
                # 如果是相对路径，相对于markdown文件所在目录
                original_path = os.path.join(os.path.dirname(md_path), img_path)
            
            if os.path.exists(original_path):
                try:
                    shutil.copy2(original_path, new_img_path)
                except Exception as e:
                    img_exists = False
                    not_exist_set.add(img_path)
                    print(f"复制图片失败 {original_path}: {e}")
            else:
                img_exists = False
                not_exist_set.add(img_path)
        
        if img_exists:
            replace_map[img_path] = f"images/{new_filename}"

    # 自动发现并添加session目录中的图片
    print("🔍 自动发现财务分析图表...")
    # 直接使用当前工作目录下的data/financials
    data_financials_dir = os.path.join(os.getcwd(), "data", "financials")
    if data_financials_dir and os.path.exists(data_financials_dir):
        # 找到最新的session目录
        session_dirs = [d for d in os.listdir(data_financials_dir) if d.startswith('session_')]
        if session_dirs:
            # 按修改时间排序，选择最新的
            session_dirs.sort(key=lambda x: os.path.getmtime(os.path.join(data_financials_dir, x)), reverse=True)
            latest_session = session_dirs[0]
            session_path = os.path.join(data_financials_dir, latest_session)
            
            # 查找所有图片文件
            image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg']:
                import glob
                image_files.extend(glob.glob(os.path.join(session_path, ext)))
            
            if image_files:
                print(f"📊 发现 {len(image_files)} 个财务分析图表")
                
                # 在内容中添加图表展示部分
                chart_section = "\n\n## 财务分析图表\n\n"
                chart_section += "以下是系统自动生成的财务分析图表：\n\n"
                
                for img_file in image_files:
                    # 复制图片到images目录
                    filename = os.path.basename(img_file)
                    base, ext = os.path.splitext(filename)
                    i = 1
                    new_filename = filename
                    while new_filename in used_names:
                        new_filename = f"{base}_{i}{ext}"
                        i += 1
                    used_names.add(new_filename)
                    
                    new_img_path = os.path.join(images_dir, new_filename)
                    try:
                        shutil.copy2(img_file, new_img_path)
                        # 添加图片引用到内容中
                        chart_name = base.replace('_', ' ').replace('-', ' ').title()
                        chart_section += f"### {chart_name}\n\n"
                        chart_section += f"![{chart_name}](images/{new_filename})\n\n"
                        print(f"✅ 已添加图表: {chart_name}")
                    except Exception as e:
                        print(f"❌ 复制图表失败 {img_file}: {e}")
                
                # 将图表部分插入到内容中（在结尾或合适位置）
                if "## 总结" in content:
                    content = content.replace("## 总结", chart_section + "## 总结")
                else:
                    content += chart_section
            else:
                print("⚠️ 未发现财务分析图表文件")
        else:
            print("⚠️ 未找到session目录")
    else:
        print("⚠️ 未找到data/financials目录")

    # 替换原有的图片路径
    for old_path, new_path in replace_map.items():
        content = content.replace(f"]({old_path})", f"]({new_path})")

    # 保存新文件
    with open(new_md_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 图片处理完成，保存到: {new_md_path}")
    if not_exist_set:
        print(f"⚠️ 以下图片未找到: {not_exist_set}")
    
    return new_md_path

if __name__ == "__main__":
    import tempfile
    
    def test_extract_images_functionality():
        """测试图片提取功能"""
        print("🧪 开始测试图片提取功能...")
        
        # 创建测试用的markdown内容
        test_content = """# 测试报告

## 财务分析

这是一个测试报告，包含以下内容：

![示例图片](收入利润趋势.png)

## 总结

测试完成。
"""
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            test_md_path = f.name
        
        print(f"📄 创建测试文件: {test_md_path}")
        
        # 创建临时图片目录
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = os.path.join(temp_dir, 'images')
            new_md_path = test_md_path.replace('.md', '_images.md')
            
            try:
                # 测试图片提取功能
                print("🔍 测试路径搜索功能...")
                result_path = extract_images_from_markdown(test_md_path, images_dir, new_md_path)
                
                print(f"✅ 功能测试完成！")
                print(f"📁 输出文件: {result_path}")
                
                # 检查输出文件内容
                if os.path.exists(result_path):
                    with open(result_path, 'r', encoding='utf-8') as f:
                        new_content = f.read()
                    print("📖 处理后的内容预览:")
                    print(new_content[:500] + "..." if len(new_content) > 500 else new_content)
                
            except Exception as e:
                print(f"❌ 测试失败: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # 清理临时文件
                try:
                    os.unlink(test_md_path)
                    if os.path.exists(new_md_path):
                        os.unlink(new_md_path)
                except:
                    pass
        
        print("🏁 测试完成！")
    
    # 运行测试
    test_extract_images_functionality()