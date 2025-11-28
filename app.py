from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from database import DatabaseManager
from image_processor import ImageProcessor
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生产环境中应该使用安全的密钥

# 初始化管理器
db_manager = DatabaseManager()
image_processor = ImageProcessor()

@app.route('/')
def index():
    """首页 - 空间创建和加入"""
    return render_template('index.html')

@app.route('/space/<int:space_id>')
def space_detail(space_id):
    """空间详情页面"""
    space_info = db_manager.get_space_info(space_id)
    if not space_info:
        return render_template('error.html', message='空间不存在')
    
    # 检查用户是否在空间中
    username = session.get('username')
    user_role = db_manager.get_user_role(space_id, username) if username else None
    
    if not user_role:
        # 用户未加入空间，重定向到加入页面
        return redirect(url_for('join_space_page', join_key=space_info['join_key']))
    
    return render_template('space.html', space_info=space_info, user_role=user_role, username=username)

@app.route('/join/<join_key>')
def join_space_page(join_key):
    """加入空间页面"""
    space_info = db_manager.get_space_by_join_key(join_key)
    if not space_info:
        return render_template('error.html', message='无效的加入密钥')
    return render_template('join.html', join_key=join_key, space_name=space_info['name'])

@app.route('/api/create_space', methods=['POST'])
def create_space():
    """创建新空间"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 获取参数
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        creator_username = request.form.get('username', '').strip()
        grid_size = int(request.form.get('grid_size', 128))
        start_x = int(request.form.get('start_x', 0))
        start_y = int(request.form.get('start_y', 0))
        
        if not name or not creator_username:
            return jsonify({'error': '空间名称和用户名不能为空'}), 400
        
        # 处理图像
        process_result = image_processor.process_image_for_space(file, grid_size, start_x, start_y)
        
        # 创建空间
        space_data = db_manager.create_space(
            name=name,
            description=description,
            creator_username=creator_username,
            grid_size=process_result['grid_size'],
            grid_width=process_result['grid_width'],
            grid_height=process_result['grid_height'],
            original_image_hash=process_result['original_image_hash'],
            processed_image_base64=process_result['processed_image_base64'],
            pixel_metadata=process_result['pixel_metadata'],
            start_x=start_x,
            start_y=start_y
        )
        
        # 设置用户会话
        session['username'] = creator_username
        session['space_id'] = space_data['space_id']
        
        return jsonify({
            'success': True,
            'space_id': space_data['space_id'],
            'join_key': space_data['join_key']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/join_space', methods=['POST'])
def join_space():
    """加入空间"""
    try:
        join_key = request.json.get('join_key', '').strip()
        username = request.json.get('username', '').strip()
        
        if not join_key or not username:
            return jsonify({'error': '加入密钥和用户名不能为空'}), 400
        
        result = db_manager.join_space(join_key, username)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
        
        # 设置用户会话
        session['username'] = username
        session['space_id'] = result['space_id']
        
        return jsonify({
            'success': True,
            'space_id': result['space_id'],
            'space_name': result['space_name']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/space/<int:space_id>/data')
def get_space_data(space_id):
    """获取空间数据"""
    try:
        username = session.get('username')
        if not username:
            return jsonify({'error': '未登录'}), 401
        
        user_role = db_manager.get_user_role(space_id, username)
        if not user_role:
            return jsonify({'error': '无权访问此空间'}), 403
        
        space_data = db_manager.get_space_pixel_data(space_id)
        if not space_data:
            return jsonify({'error': '空间不存在'}), 404
        
        # 直接使用数据库返回的像素数据
        response_data = {
            'space_info': space_data['space_info'],
            'pixels': space_data['pixels'],
            'user_role': user_role,
            'total_pixels': space_data['total_pixels'],
            'completed_pixels': space_data['completed_pixels']
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/space/<int:space_id>/mark_complete', methods=['POST'])
def mark_pixel_complete(space_id):
    """标记像素为已完成"""
    try:
        username = session.get('username')
        if not username:
            return jsonify({'error': '未登录'}), 401
        
        data = request.json
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            return jsonify({'error': '缺少必要参数'}), 400
        
        result = db_manager.mark_pixel_complete(space_id, username, x, y)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/space/<int:space_id>/stats')
def get_space_stats(space_id):
    """获取空间统计信息"""
    try:
        username = session.get('username')
        if not username:
            return jsonify({'error': '未登录'}), 401
        
        user_role = db_manager.get_user_role(space_id, username)
        if not user_role:
            return jsonify({'error': '无权访问此空间'}), 403
        
        space_info = db_manager.get_space_info(space_id)
        if not space_info:
            return jsonify({'error': '空间不存在'}), 404
        
        # 获取用户完成统计
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, COUNT(*) as pixel_count 
            FROM user_completions 
            WHERE space_id = ? 
            GROUP BY username
        ''', (space_id,))
        
        user_stats = cursor.fetchall()
        conn.close()
        
        stats = {
            'total_users': len(space_info['users']),
            'total_pixels': len(space_info['pixel_metadata']),
            'completed_pixels': sum(stat[1] for stat in user_stats),
            'completion_percentage': 0,
            'user_contributions': [
                {'username': stat[0], 'pixel_count': stat[1]} for stat in user_stats
            ]
        }
        
        if stats['total_pixels'] > 0:
            stats['completion_percentage'] = round((stats['completed_pixels'] / stats['total_pixels']) * 100, 1)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/space/<int:space_id>/export')
def export_space(space_id):
    """导出空间数据"""
    try:
        username = session.get('username')
        if not username:
            return jsonify({'error': '未登录'}), 401
        
        user_role = db_manager.get_user_role(space_id, username)
        if user_role != 'creator':
            return jsonify({'error': '只有创建者可以导出数据'}), 403
        
        format_type = request.args.get('format', 'json')
        export_data = db_manager.export_space_data(space_id, format_type)
        
        if not export_data:
            return jsonify({'error': '导出失败'}), 500
        
        return jsonify({'data': export_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/maintenance/archive_old_spaces')
def archive_old_spaces():
    """维护任务：归档旧空间"""
    try:
        # 在生产环境中应该添加认证
        archived_count = db_manager.archive_old_spaces()
        return jsonify({'archived_count': archived_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
