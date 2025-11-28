import sqlite3
import json
from datetime import datetime, timedelta
import secrets

class DatabaseManager:
    def __init__(self, db_path='spaces.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化数据库表结构 - 优化后的结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 空间表 - 存储空间基本信息和像素元数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                join_key TEXT UNIQUE NOT NULL,
                creator_username TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                grid_size INTEGER,
                grid_width INTEGER,
                grid_height INTEGER,
                start_x INTEGER DEFAULT 0,
                start_y INTEGER DEFAULT 0,
                original_image_hash TEXT,
                processed_image_base64 TEXT,
                pixel_metadata TEXT,  -- JSON格式存储所有像素的颜色和位置信息
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 空间用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS space_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER,
                username TEXT NOT NULL,
                role TEXT DEFAULT 'participant',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (space_id) REFERENCES spaces (id),
                UNIQUE(space_id, username)
            )
        ''')
        
        # 用户完成记录表 - 只记录用户完成了哪些像素
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER,
                username TEXT NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (space_id) REFERENCES spaces (id),
                UNIQUE(space_id, username, x, y)  -- 确保每个用户对每个像素只能完成一次
            )
        ''')
        
        # 批量提交记录表 - 记录批量操作（用于审计和性能优化）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER,
                username TEXT NOT NULL,
                completed_pixels TEXT NOT NULL,  -- JSON格式存储完成的像素坐标数组
                pixel_count INTEGER NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (space_id) REFERENCES spaces (id)
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_space_users ON space_users(space_id, username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_completions ON user_completions(space_id, x, y)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_spaces_status ON spaces(status, last_accessed)')
        
        conn.commit()
        conn.close()
    
    def generate_join_key(self):
        """生成唯一的加入密钥"""
        while True:
            key = secrets.token_urlsafe(8)
            if not self.get_space_by_join_key(key):
                return key
    
    def get_space_by_join_key(self, join_key):
        """根据加入密钥获取空间信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, status FROM spaces WHERE join_key = ?', (join_key,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'status': result[2]
            }
        return None
    
    def _get_connection(self):
        """获取数据库连接（用于内部使用）"""
        return sqlite3.connect(self.db_path)
    
    def create_space(self, name, description, creator_username, grid_size, grid_width, grid_height, 
                    original_image_hash, processed_image_base64, pixel_metadata, start_x=0, start_y=0):
        """创建新空间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        join_key = self.generate_join_key()
        
        # 将像素元数据序列化为JSON存储
        pixel_metadata_json = json.dumps(pixel_metadata)
        
        cursor.execute('''
            INSERT INTO spaces 
            (name, description, join_key, creator_username, grid_size, grid_width, grid_height,
             original_image_hash, processed_image_base64, pixel_metadata, start_x, start_y)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, join_key, creator_username, grid_size, grid_width, grid_height,
              original_image_hash, processed_image_base64, pixel_metadata_json, start_x, start_y))
        
        space_id = cursor.lastrowid
        
        # 添加创建者到用户表
        cursor.execute('''
            INSERT INTO space_users (space_id, username, role)
            VALUES (?, ?, 'creator')
        ''', (space_id, creator_username))
        
        conn.commit()
        conn.close()
        
        return {
            'space_id': space_id,
            'join_key': join_key,
            'name': name,
            'description': description,
            'creator_username': creator_username
        }
    
    def join_space(self, join_key, username):
        """用户加入空间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取空间信息
        cursor.execute('SELECT id, name, status FROM spaces WHERE join_key = ?', (join_key,))
        space = cursor.fetchone()
        
        if not space:
            conn.close()
            return {'error': '空间不存在'}
        
        space_id, space_name, status = space
        
        if status != 'active':
            conn.close()
            return {'error': '空间已归档'}
        
        # 检查用户是否已加入
        cursor.execute('SELECT id FROM space_users WHERE space_id = ? AND username = ?', (space_id, username))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            # 添加用户到空间
            cursor.execute('''
                INSERT INTO space_users (space_id, username, role)
                VALUES (?, ?, 'participant')
            ''', (space_id, username))
        
        # 更新最后访问时间
        cursor.execute('UPDATE spaces SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?', (space_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'space_id': space_id,
            'space_name': space_name,
            'username': username,
            'role': 'participant' if not existing_user else 'existing'
        }
    
    def get_space_info(self, space_id):
        """获取空间信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, join_key, creator_username, status, 
                   grid_size, grid_width, grid_height, start_x, start_y,
                   processed_image_base64, pixel_metadata, created_at, last_accessed
            FROM spaces WHERE id = ?
        ''', (space_id,))
        
        space = cursor.fetchone()
        if not space:
            conn.close()
            return None
        
        # 获取空间用户列表
        cursor.execute('''
            SELECT username, role, joined_at 
            FROM space_users 
            WHERE space_id = ? 
            ORDER BY joined_at
        ''', (space_id,))
        
        users = cursor.fetchall()
        
        conn.close()
        
        return {
            'id': space[0],
            'name': space[1],
            'description': space[2],
            'join_key': space[3],
            'creator_username': space[4],
            'status': space[5],
            'grid_size': space[6],
            'grid_width': space[7],
            'grid_height': space[8],
            'start_x': space[9],
            'start_y': space[10],
            'processed_image_base64': space[11],
            'pixel_metadata': json.loads(space[12]),
            'created_at': space[13],
            'last_accessed': space[14],
            'users': [
                {
                    'username': user[0],
                    'role': user[1],
                    'joined_at': user[2]
                } for user in users
            ]
        }
    
    def get_user_role(self, space_id, username):
        """获取用户在空间中的角色"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT role FROM space_users WHERE space_id = ? AND username = ?', (space_id, username))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else None
    
    def mark_pixel_complete(self, space_id, username, x, y):
        """标记像素为已完成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查用户是否在空间中
        role = self.get_user_role(space_id, username)
        if not role:
            conn.close()
            return {'error': '用户不在空间中'}
        
        # 插入用户完成记录
        try:
            cursor.execute('''
                INSERT INTO user_completions (space_id, username, x, y)
                VALUES (?, ?, ?, ?)
            ''', (space_id, username, x, y))
        except sqlite3.IntegrityError:
            # 如果已经完成过，忽略重复插入
            conn.close()
            return {'success': True, 'message': '像素已完成'}
        
        # 更新空间最后访问时间
        cursor.execute('UPDATE spaces SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?', (space_id,))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
    
    def get_space_pixel_data(self, space_id):
        """获取空间的完整像素数据（元数据 + 用户完成状态）"""
        space_info = self.get_space_info(space_id)
        if not space_info:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有用户完成记录
        cursor.execute('''
            SELECT x, y, username 
            FROM user_completions 
            WHERE space_id = ?
        ''', (space_id,))
        
        completions = cursor.fetchall()
        conn.close()
        
        # 构建用户完成字典以便快速查找
        user_completions = {}
        for completion in completions:
            x, y, username = completion
            user_completions[f"{x},{y}"] = username
        
        # 构建完整的像素数据
        complete_pixels = []
        pixel_metadata = space_info['pixel_metadata']
        
        for pixel_data in pixel_metadata:
            x = pixel_data['x']
            y = pixel_data['y']
            pixel_key = f"{x},{y}"
            
            if pixel_key in user_completions:
                # 像素已完成
                pixel_data['username'] = user_completions[pixel_key]
            else:
                # 像素未完成
                pixel_data['username'] = None
            
            complete_pixels.append(pixel_data)
        
        return {
            'space_info': space_info,
            'pixels': complete_pixels,
            'total_pixels': len(complete_pixels),
            'completed_pixels': len(user_completions)
        }
    
    def archive_old_spaces(self, days_inactive=2):
        """归档长时间未访问的空间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_inactive)
        
        cursor.execute('''
            UPDATE spaces 
            SET status = 'archived' 
            WHERE status = 'active' 
            AND last_accessed < ?
        ''', (cutoff_date,))
        
        archived_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return archived_count
    
    def batch_mark_pixels_complete(self, space_id, username, pixels):
        """批量标记像素为已完成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查用户是否在空间中
        role = self.get_user_role(space_id, username)
        if not role:
            conn.close()
            return {'error': '用户不在空间中'}
        
        # 检查批量大小限制（最多40个）
        if len(pixels) > 40:
            conn.close()
            return {'error': '批量提交超过40个像素限制'}
        
        # 使用事务确保原子性
        conn.execute('BEGIN TRANSACTION')
        
        try:
            completed_count = 0
            conflict_pixels = []
            
            # 批量插入用户完成记录
            for pixel in pixels:
                x = pixel['x']
                y = pixel['y']
                
                try:
                    cursor.execute('''
                        INSERT INTO user_completions (space_id, username, x, y)
                        VALUES (?, ?, ?, ?)
                    ''', (space_id, username, x, y))
                    completed_count += 1
                except sqlite3.IntegrityError:
                    # 如果已经完成过，记录冲突但不中断
                    conflict_pixels.append({'x': x, 'y': y})
                    continue
            
            # 记录批量提交（用于审计）
            if completed_count > 0:
                cursor.execute('''
                    INSERT INTO batch_submissions (space_id, username, completed_pixels, pixel_count)
                    VALUES (?, ?, ?, ?)
                ''', (space_id, username, json.dumps(pixels), completed_count))
            
            # 更新空间最后访问时间
            cursor.execute('UPDATE spaces SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?', (space_id,))
            
            conn.commit()
            
            result = {
                'success': True,
                'completed_count': completed_count,
                'total_requested': len(pixels)
            }
            
            if conflict_pixels:
                result['conflict_pixels'] = conflict_pixels
                result['message'] = f'成功完成{completed_count}个像素，{len(conflict_pixels)}个像素已被其他用户完成'
            else:
                result['message'] = f'成功完成{completed_count}个像素'
            
            return result
            
        except Exception as e:
            conn.rollback()
            return {'error': f'批量提交失败: {str(e)}'}
        finally:
            conn.close()
    
    def export_space_data(self, space_id, format_type='json'):
        """导出空间数据"""
        space_data = self.get_space_pixel_data(space_id)
        if not space_data:
            return None
        
        if format_type == 'json':
            return json.dumps(space_data, ensure_ascii=False, indent=2)
        elif format_type == 'png':
            # 这里可以添加生成PNG图像的逻辑
            # 暂时返回None，后续可以扩展
            return None
        
        return None
