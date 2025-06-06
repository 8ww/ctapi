from flask import Flask, request, jsonify
import json
import logging
import os
import re
from typing import Dict, Union, List
import glob
from datetime import datetime

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 题型映射
TYPE_MAP = {'1': '单选题', '2': '多选题', '3': '判断题', '4': '填空题'}

# JSON文件存储目录
DATA_DIR = "./data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def get_question_type(type_id: str) -> str:
    """根据类型ID返回题目类型，默认填空题"""
    return TYPE_MAP.get(str(type_id), '填空题')


def clean_image_src(text: str) -> str:
    """清理图片src中的反斜杠"""
    if not isinstance(text, str):
        return str(text)
    if '<img' in text:
        return re.sub(r'\\+', '', text)
    return text


def clean_question_text(text: str) -> str:
    """清理题目文本，去除多余空格和换行"""
    if not isinstance(text, str):
        return str(text).strip()
    # 保留基本格式，只去除首尾空格和多余的空白字符
    return re.sub(r'\s+', ' ', text.strip())


def normalize_option_texts(options: Union[str, List, None]) -> str:
    """标准化选项数据为JSON字符串"""
    if not options:
        return '[]'

    if isinstance(options, str):
        # 如果已经是有效的JSON字符串，直接返回
        try:
            json.loads(options)
            return options
        except json.JSONDecodeError:
            # 否则包装成数组
            return json.dumps([options], ensure_ascii=False)

    if isinstance(options, list):
        return json.dumps(options, ensure_ascii=False)

    return json.dumps([str(options)], ensure_ascii=False)


def load_json_files() -> List[Dict]:
    """加载所有 tk_data_chunk_*.json 文件"""
    all_data = []
    try:
        pattern = os.path.join(DATA_DIR, "tk_data_chunk_*.json")
        json_files = glob.glob(pattern)

        if not json_files:
            logger.info("未找到任何JSON数据文件")
            return []

        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
                    else:
                        logger.warning(f"文件 {file_path} 格式不正确，期望列表格式")
            except json.JSONDecodeError as e:
                logger.error(f"解析JSON文件 {file_path} 失败: {e}")
            except Exception as e:
                logger.error(f"读取文件 {file_path} 失败: {e}")

        logger.info(f"成功加载 {len(all_data)} 条题目数据")
        return all_data

    except Exception as e:
        logger.error(f"加载JSON文件失败: {e}")
        return []


def save_all_data(all_data: List[Dict]) -> bool:
    """保存所有数据，覆盖现有文件或创建新文件"""
    try:
        # 删除旧的chunk文件
        old_files = glob.glob(os.path.join(DATA_DIR, "tk_data_chunk_*.json"))
        for old_file in old_files:
            try:
                os.remove(old_file)
            except Exception as e:
                logger.warning(f"删除旧文件 {old_file} 失败: {e}")

        # 按每个文件最多5000条数据分割保存
        chunk_size = 5000
        for i, start_idx in enumerate(range(0, len(all_data), chunk_size)):
            chunk_data = all_data[start_idx:start_idx + chunk_size]
            file_path = os.path.join(DATA_DIR, f"tk_data_chunk_{i + 1}.json")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)

            logger.info(f"保存文件 {file_path}，包含 {len(chunk_data)} 条数据")

        return True

    except Exception as e:
        logger.error(f"保存数据失败: {e}")
        return False


def find_question_match(all_data: List[Dict], question: str, question_type: str = None) -> Dict:
    """查找题目匹配项"""
    question_clean = clean_question_text(question)

    # 首先尝试精确匹配（题目+类型）
    if question_type:
        for item in all_data:
            if (clean_question_text(item.get('tm', '')) == question_clean and
                    item.get('type') == question_type):
                return item

    # 如果没有精确匹配，尝试仅匹配题目
    for item in all_data:
        if clean_question_text(item.get('tm', '')) == question_clean:
            if question_type:
                logger.info(f"仅匹配题目文本，类型不匹配: 期望{question_type}, 实际{item.get('type')}")
            return item

    return None


@app.route('/cx', methods=['POST'])
def cx_query():
    """查询题目答案"""
    try:
        # 获取请求参数
        if request.is_json:
            params = request.get_json()
        else:
            params = request.form.to_dict()

        if not params:
            return jsonify({'code': -1, 'msg': '缺少参数', 'data': None})

        question = params.get('question', '').strip()
        type_id = str(params.get('type', '0'))

        if not question:
            return jsonify({'code': -1, 'msg': '题目不能为空', 'data': None})

        question_type = get_question_type(type_id) if type_id != '0' else None
        logger.info(f"查询题目: {question[:50]}... (类型: {question_type or '未指定'})")

        # 加载数据并查找匹配项
        all_data = load_json_files()
        if not all_data:
            return jsonify({'code': -1, 'msg': '题库数据为空', 'data': None})

        matched_item = find_question_match(all_data, question, question_type)

        if matched_item:
            answer = clean_image_src(matched_item.get('da', ''))
            logger.info(f"找到匹配答案: {answer[:50]}...")
            return jsonify({'code': 1, 'msg': '查询成功', 'data': answer})
        else:
            logger.warning(f"未找到匹配项: {question[:50]}...")
            return jsonify({'code': -1, 'msg': '未找到答案', 'data': None})

    except json.JSONDecodeError:
        logger.error("JSON解析错误")
        return jsonify({'code': -1, 'msg': '无效的JSON格式', 'data': None})
    except Exception as e:
        logger.error(f"查询服务器错误: {str(e)}")
        return jsonify({'code': -1, 'msg': f'服务器错误: {str(e)}', 'data': None})


@app.route('/cx_update', methods=['POST'])
def cx_update():
    """更新或插入题目数据"""
    try:
        # 获取请求参数
        if request.is_json:
            params = request.get_json()
        else:
            params = request.form.to_dict()
            # 尝试解析form中的data字段
            if 'data' in params and isinstance(params['data'], str):
                try:
                    params['data'] = json.loads(params['data'])
                except json.JSONDecodeError:
                    return jsonify({'code': -1, 'msg': 'data字段JSON格式错误', 'data': None})

        if not params:
            return jsonify({'code': -1, 'msg': '缺少参数', 'data': None})

        data_list = params.get('data', [])
        if not isinstance(data_list, list):
            return jsonify({'code': -1, 'msg': 'data必须是列表格式', 'data': None})

        if not data_list:
            return jsonify({'code': -1, 'msg': '数据列表不能为空', 'data': None})

        # 加载现有数据
        all_data = load_json_files()
        updated_count = 0
        added_count = 0

        for item in data_list:
            try:
                question = clean_question_text(item.get('question', ''))
                answer = item.get('option', '')
                type_id = str(item.get('type', '4'))  # 默认填空题
                options = normalize_option_texts(item.get('optionTexts'))

                if not question:
                    logger.warning("跳过空题目")
                    continue

                question_type = get_question_type(type_id)

                # 查找是否存在相同题目
                found_item = find_question_match(all_data, question, question_type)

                if found_item:
                    # 更新现有题目
                    found_item['da'] = answer
                    found_item['optionTexts'] = options
                    updated_count += 1
                    logger.info(f"更新题目: {question[:30]}...")
                else:
                    # 添加新题目
                    new_item = {
                        'type': question_type,
                        'tm': question,
                        'da': answer,
                        'optionTexts': options
                    }
                    all_data.append(new_item)
                    added_count += 1
                    logger.info(f"添加新题目: {question[:30]}...")

            except Exception as e:
                logger.error(f"处理单条数据失败: {e}")
                continue

        # 保存所有数据
        if updated_count > 0 or added_count > 0:
            if save_all_data(all_data):
                total_processed = updated_count + added_count
                msg = f'成功处理{total_processed}条数据（更新{updated_count}条，新增{added_count}条）'
                logger.info(msg)
                return jsonify({'code': 1, 'msg': msg, 'data': total_processed})
            else:
                return jsonify({'code': -1, 'msg': '保存数据失败', 'data': None})
        else:
            return jsonify({'code': 0, 'msg': '没有有效数据需要处理', 'data': 0})

    except json.JSONDecodeError:
        logger.error("JSON解析错误")
        return jsonify({'code': -1, 'msg': '无效的JSON格式', 'data': None})
    except Exception as e:
        logger.error(f"更新服务器错误: {str(e)}")
        return jsonify({'code': -1, 'msg': f'服务器错误: {str(e)}', 'data': None})


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    try:
        all_data = load_json_files()
        return jsonify({
            'code': 1,
            'msg': '服务正常',
            'data': {
                'total_questions': len(all_data),
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'code': -1, 'msg': f'服务异常: {str(e)}', 'data': None})


@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': -1, 'msg': '接口不存在', 'data': None}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'code': -1, 'msg': '内部服务器错误', 'data': None}), 500


if __name__ == '__main__':
    logger.info("启动题库API服务...")
    app.run(debug=True, host='127.0.0.1', port=5000)