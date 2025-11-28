from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from PIL import Image
import numpy as np
import io
import os
import colorsys
import sqlite3
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化SQLite数据库
def init_db():
    conn = sqlite3.connect('coloring_progress.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coloring_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_hash TEXT UNIQUE,
            grid_size INTEGER,
            grid_width INTEGER,
            grid_height INTEGER,
            processed_image TEXT,
            coloring_list TEXT,
            palette TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 初始化数据库
init_db()

def save_progress(image_hash, grid_size, grid_width, grid_height, processed_image, coloring_list, palette):
    """保存进度到数据库"""
    conn = sqlite3.connect('coloring_progress.db')
    cursor = conn.cursor()
    
    coloring_list_json = json.dumps(coloring_list)
    palette_json = json.dumps(palette)
    
    cursor.execute('''
        INSERT OR REPLACE INTO coloring_progress 
        (image_hash, grid_size, grid_width, grid_height, processed_image, coloring_list, palette, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (image_hash, grid_size, grid_width, grid_height, processed_image, coloring_list_json, palette_json))
    
    conn.commit()
    conn.close()

def load_progress(image_hash):
    """从数据库加载进度"""
    conn = sqlite3.connect('coloring_progress.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT grid_size, grid_width, grid_height, processed_image, coloring_list, palette
        FROM coloring_progress WHERE image_hash = ?
    ''', (image_hash,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'grid_size': result[0],
            'grid_width': result[1],
            'grid_height': result[2],
            'processed_image': result[3],
            'coloring_list': json.loads(result[4]),
            'palette': json.loads(result[5])
        }
    return None

def get_latest_progress():
    """获取最新的进度记录"""
    conn = sqlite3.connect('coloring_progress.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT image_hash, grid_size, grid_width, grid_height, processed_image, coloring_list, palette
        FROM coloring_progress 
        ORDER BY updated_at DESC 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'image_hash': result[0],
            'grid_size': result[1],
            'grid_width': result[2],
            'grid_height': result[3],
            'processed_image': result[4],
            'coloring_list': json.loads(result[5]),
            'palette': json.loads(result[6])
        }
    return None

def generate_image_hash(file_content):
    """生成图像内容的哈希值"""
    import hashlib
    return hashlib.md5(file_content).hexdigest()

def pixelate_image(image, grid_size):
    """将图像像素化处理"""
    # 获取原始尺寸
    original_width, original_height = image.size
    
    # 计算新的像素化尺寸
    if original_width >= original_height:
        new_width = grid_size
        new_height = int((original_height / original_width) * grid_size)
    else:
        new_height = grid_size
        new_width = int((original_width / original_height) * grid_size)
    
    # 确保最小尺寸为1
    new_width = max(1, new_width)
    new_height = max(1, new_height)
    
    # 缩小到像素化尺寸（使用最近邻插值保持像素感）
    pixelated = image.resize((new_width, new_height), Image.NEAREST)
    
    # 转换为RGB模式
    pixelated_rgb = pixelated.convert('RGB')
    
    # 使用固定的32种颜色调色板重新映射颜色
    fixed_palette = get_color_palette()
    pixels = np.array(pixelated_rgb)
    
    # 对每个像素找到最接近的固定颜色
    for x in range(pixels.shape[0]):
        for y in range(pixels.shape[1]):
            original_color = tuple(int(c) for c in pixels[x, y])
            closest_color, _ = find_closest_color(original_color, fixed_palette)
            pixels[x, y] = closest_color
    
    # 从NumPy数组重新创建图像
    processed_image = Image.fromarray(pixels.astype('uint8'), 'RGB')
    
    return processed_image, new_width, new_height

def rgb_to_hex(rgb):
    """将RGB转换为十六进制颜色代码"""
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

# 固定的32种颜色调色板
FIXED_PALETTE = [
    # 第一排 (10种颜色)
    '#fc1b19', '#ff7f00', '#ffdb53', '#00aa01', '#00e0be',
    '#006fff', '#a000b8', '#000000', '#808080', '#ffffff',
    # 第二排 (11种颜色)
    '#f9e1df', '#fce8cd', '#feca91', '#b0d9f7', '#acf59c',
    '#4fe2ec', '#c5a3fa', '#ff5555', '#b35a00', '#9dc854',
    '#f9ac8e',
    # 第三排 (11种颜色)
    '#c7c7c7', '#1d9bff', '#ffbb00', '#1245a1', '#2a642a',
    '#014670', '#b73f27', '#ff45b8', '#795547', '#640063',
    '#760000'
]

def hex_to_rgb(hex_color):
    """将十六进制颜色转换为RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_color_palette():
    """返回固定的32种颜色调色板"""
    return [hex_to_rgb(color) for color in FIXED_PALETTE]

def find_closest_color(target_color, palette):
    """在调色板中找到最接近的颜色"""
    target_r, target_g, target_b = target_color
    
    # 使用简单的欧几里得距离
    min_distance = float('inf')
    closest_color = None
    closest_index = -1
    
    for i, color in enumerate(palette):
        r, g, b = color
        
        # 计算欧几里得距离
        distance = ((target_r - r) ** 2 + (target_g - g) ** 2 + (target_b - b) ** 2) ** 0.5
        
        if distance < min_distance:
            min_distance = distance
            closest_color = color
            closest_index = i
    
    return closest_color, closest_index

def get_color_position(index):
    """根据颜色索引获取颜色位置信息"""
    if index < 10:
        # 第一排
        return f"第一排第{index + 1}个"
    elif index < 21:
        # 第二排
        return f"第二排第{index - 9}个"
    else:
        # 第三排
        return f"第三排第{index - 20}个"

def generate_coloring_list(pixelated_image, grid_width, grid_height):
    """生成所有像素点的填色列表"""
    rgb_image = pixelated_image.convert('RGB')
    pixels = np.array(rgb_image)
    
    coloring_list = []
    fixed_palette = get_color_palette()
    
    # 遍历所有像素点
    for x in range(grid_height):
        for y in range(grid_width):
            original_color = tuple(int(c) for c in pixels[x, y])
            
            # 在固定调色板中找到最接近的颜色
            closest_color, color_index = find_closest_color(original_color, fixed_palette)
            closest_color_hex = rgb_to_hex(closest_color)
            color_position = get_color_position(color_index)
            
            coloring_list.append({
                'x': x,
                'y': y,
                'color': closest_color_hex,
                'color_rgb': closest_color,
                'color_index': color_index,
                'color_position': color_position,
                'completed': False  # 标记是否已完成填色
            })
    
    return coloring_list, fixed_palette

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 获取参数
        grid_size = int(request.form.get('grid_size', 128))
        start_x = int(request.form.get('start_x', 0))
        start_y = int(request.form.get('start_y', 0))
        
        # 读取文件内容用于生成哈希
        file_content = file.read()
        file.seek(0)  # 重置文件指针
        
        # 生成图像哈希
        image_hash = generate_image_hash(file_content)
        
        # 检查是否有保存的进度，并且网格大小没有改变
        saved_progress = load_progress(image_hash)
        
        if saved_progress and saved_progress['grid_size'] == grid_size:
            # 使用保存的进度（网格大小相同）
            # 为保存的进度添加display_x和display_y字段
            coloring_list = saved_progress['coloring_list']
            for item in coloring_list:
                item['display_x'] = item.get('display_x', item['x'] + start_x)
                item['display_y'] = item.get('display_y', item['y'] + start_y)
            
            response_data = {
                'grid_width': saved_progress['grid_width'],
                'grid_height': saved_progress['grid_height'],
                'coloring_list': coloring_list,
                'palette': saved_progress['palette'],
                'image_size': (saved_progress['grid_width'], saved_progress['grid_height']),
                'processed_image': saved_progress['processed_image'],
                'total_pixels': len(coloring_list),
                'from_saved': True,
                'image_hash': image_hash  # 返回图像哈希给前端
            }
        else:
            # 处理新图像
            image = Image.open(file.stream)
            
            # 像素化处理
            pixelated_image, grid_width, grid_height = pixelate_image(image, grid_size)
            
            # 生成填色列表
            coloring_list, palette = generate_coloring_list(
                pixelated_image, grid_width, grid_height
            )
            
            # 根据起始坐标调整填色列表中的坐标显示
            # 应用内部仍然使用相对坐标，但显示给用户的是绝对坐标
            for item in coloring_list:
                # 将相对坐标转换为绝对坐标
                item['display_x'] = item['x'] + start_x
                item['display_y'] = item['y'] + start_y
                # 保留原始相对坐标用于内部处理
                item['relative_x'] = item['x']
                item['relative_y'] = item['y']
            
            # 保存处理后的图像到内存
            output_buffer = io.BytesIO()
            pixelated_image.save(output_buffer, format='PNG')
            output_buffer.seek(0)
            
            # 将图像转换为base64用于前端预览
            import base64
            image_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            
            # 保存进度到数据库
            save_progress(image_hash, grid_size, grid_width, grid_height, image_base64, coloring_list, palette)
            
            # 准备响应数据
            response_data = {
                'grid_width': grid_width,
                'grid_height': grid_height,
                'coloring_list': coloring_list,
                'palette': [rgb_to_hex(color) for color in palette],
                'image_size': pixelated_image.size,
                'processed_image': image_base64,
                'total_pixels': len(coloring_list),
                'from_saved': False
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_progress', methods=['POST'])
def save_coloring_progress():
    """保存填色进度"""
    try:
        data = request.json
        image_hash = data.get('image_hash')
        coloring_list = data.get('coloring_list')
        
        if not image_hash or not coloring_list:
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 从数据库加载当前数据
        saved_progress = load_progress(image_hash)
        if saved_progress:
            # 更新填色列表
            saved_progress['coloring_list'] = coloring_list
            # 重新保存到数据库
            save_progress(
                image_hash,
                saved_progress['grid_size'],
                saved_progress['grid_width'],
                saved_progress['grid_height'],
                saved_progress['processed_image'],
                coloring_list,
                saved_progress['palette']
            )
            return jsonify({'message': '进度保存成功'})
        else:
            return jsonify({'error': '未找到对应的图像数据'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_image(filename):
    """下载处理后的图像"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/latest_progress')
def get_latest_progress_route():
    """获取最新的进度"""
    try:
        latest_progress = get_latest_progress()
        if latest_progress:
            response_data = {
                'grid_width': latest_progress['grid_width'],
                'grid_height': latest_progress['grid_height'],
                'coloring_list': latest_progress['coloring_list'],
                'palette': latest_progress['palette'],
                'image_size': (latest_progress['grid_width'], latest_progress['grid_height']),
                'processed_image': latest_progress['processed_image'],
                'total_pixels': len(latest_progress['coloring_list']),
                'image_hash': latest_progress['image_hash']
            }
            return jsonify(response_data)
        else:
            return jsonify({'error': '没有找到保存的进度'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/processed_image')
def get_processed_image():
    """返回处理后的图像（用于演示）"""
    # 这里可以返回一个示例图像或保存的处理结果
    # 在实际应用中，应该保存处理后的图像并返回其URL
    return send_file('static/sample_output.png', mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
