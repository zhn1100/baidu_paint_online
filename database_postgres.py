import psycopg2
import json
from datetime import datetime, timedelta
import secrets
import os
from urllib.parse import urlparse

class DatabaseManager:
    def __init__(self, db_url=None):
        # 从环境变量获取数据库连接信息
        self.db_url = db_url or os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # 解析数据库URL（适用于DigitalOcean格式）
        self.init_db()
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            # 检查是否有完整的 DATABASE_URL（DigitalOcean 格式）
            database_url = os.environ.get('DATABASE_URL')
            
            if database_url:
                # 如果是 DigitalOcean 的 ${db.DATABASE_URL} 格式，需要解析
                if database_url.startswith('${db.'):
                    # 在 DigitalOcean 中，${db.DATABASE_URL} 会被自动替换为实际连接字符串
                    # 这里我们假设环境变量已经正确设置
                    database_url = os.environ.get('db.DATABASE_URL') or os.environ.get('DATABASE_URL')
                
                if database_url and database_url.startswith('postgres://'):
                    # 解析 PostgreSQL 连接字符串
                    import urllib.parse
                    result = urllib.parse.urlparse(database_url)
                    username = result.username
                    password = result.password
                    database = result.path[1:]  # 去掉开头的 '/'
                    hostname = result.hostname
                    port = result.port or 5432
                    
                    conn = psycopg2.connect(
                        host=hostname,
                        port=port,
                        database=database,
                        user=username,
                        password=password,
                        sslmode='require'
                    )
                    return conn
            
            # 如果没有 DATABASE_URL，使用分开的环境变量
            conn = psycopg2.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                port=int(os.environ.get('DB_PORT', '5432')),
                database=os.environ.get('DB_NAME', 'db'),
                user=os.environ.get('DB_USER', 'db'),
                password=os.environ.get('DB_PASSWORD', ''),
                sslmode=os.environ.get('DB_SSLMODE', 'require')
            )
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            print(f"Available env vars: DB_HOST={os.environ.get('DB_HOST')}, DATABASE_URL={os.environ.get('DATABASE_URL')}")
            raise
    
    def init_db(self):
        """初始化数据库表结构 - PostgreSQL兼容版本"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 空间表 - 存储空间基本信息和像素元数据
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS spaces (
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    space_id INTEGER,
                    username TEXT NOT NULL,
                    role TEXT DEFAULT 'participant',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (space_id) REFERENCES spaces (id) ON DELETE CASCADE,
                    UNIQUE(space_id, username)
                )
            ''')
            
            # 用户完成记录表 - 只记录用户完成了哪些像素
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_completions (
                    id SERIAL PRIMARY KEY,
                    space_id INTEGER,
                    username TEXT NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (space_id) REFERENCES spaces (id) ON DELETE CASCADE,
                    UNIQUE(space_id, username, x, y)  -- 确保每个用户对每个像素只能完成一次
                )
            ''')
            
            # 批量提交记录表 - 记录批量操作（用于审计和性能优化）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_submissions (
                    id SERIAL PRIMARY KEY,
                    space_id INTEGER,
                    username TEXT NOT NULL,
                    completed_pixels TEXT NOT NULL,  -- JSON格式存储完成的像素坐标数组
                    pixel_count INTEGER NOT NULL,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (space_id) REFERENCES spaces (id) ON DELETE CASCADE
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_space_users ON space_users(space_id, username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_completions ON user_completions(space_id, x, y)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_spaces_status ON spaces(status, last_accessed)')
            
            conn.commit()
            print("✅ Database tables initialized successfully")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Database initialization error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def generate_join_key(self):
        """生成唯一的加入密钥"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        while True:
            key = secrets.token_urlsafe(8)
            cursor.execute('SELECT id FROM spaces WHERE join_key = %s', (key,))
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                conn.close()
                return key
    
    def get_space_by_join_key(self, join_key):
        """根据加入密钥获取空间信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, status FROM spaces WHERE join_key = %s', (join_key,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'status': result[2]
            }
        return None
    
    def create_space(self, name, description, creator_username, grid_size, grid_width, grid_height, 
                    original_image_hash, processed_image_base64, pixel_metadata, start_x=0, start_y=0):
        """创建新空间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        join_key = self.generate_join_key()
        
        # 将像素元数据序列化为JSON存储
        pixel_metadata_json = json.dumps(pixel_metadata)
        
        try:
            cursor.execute('''
                INSERT INTO spaces 
                (name, description, join_key, creator_username, grid_size, grid_width, grid_height,
                 original_image_hash, processed_image_base64, pixel_metadata, start_x, start_y)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (name, description, join_key, creator_username, grid_size, grid_width, grid_height,
                  original_image_hash, processed_image_base64, pixel_metadata_json, start_x, start_y))
            
            space_id = cursor.fetchone()[0]
            
            # 添加创建者到用户表
            cursor.execute('''
                INSERT INTO space_users (space_id, username, role)
                VALUES (%s, %s, 'creator')
            ''', (space_id, creator_username))
            
            conn.commit()
            
            return {
                'space_id': space_id,
                'join_key': join_key,
                'name': name,
                'description': description,
                'creator_username': creator_username
            }
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def join_space(self, join_key, username):
        """用户加入空间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取空间信息
            cursor.execute('SELECT id, name, status FROM spaces WHERE join_key = %s', (join_key,))
            space = cursor.fetchone()
            
            if not space:
                return {'error': '空间不存在'}
            
            space_id, space_name, status = space
            
            if status != 'active':
                return {'error': '空间已归档'}
            
            # 检查用户是否已加入
            cursor.execute('SELECT id FROM space_users WHERE space_id = %s AND username = %s', (space_id, username))
            existing_user = cursor.fetchone()
            
            if not existing_user:
                # 添加用户到空间
                cursor.execute('''
                    INSERT INTO space_users (space_id, username, role)
                    VALUES (%s, %s, 'participant')
                ''', (space_id, username))
            
            # 更新最后访问时间
            cursor.execute('UPDATE spaces SET last_accessed = CURRENT_TIMESTAMP WHERE id = %s', (space_id,))
            
            conn.commit()
            
            return {
                'space_id': space_id,
                'space_name': space_name,
                'username': username,
                'role': 'participant' if not existing_user else 'existing'
            }
            
        except Exception as e:
            conn.rollback()
            return {'error': str(e)}
        finally:
            cursor.close()
            conn.close()
    
    def get_space_info(self, space_id):
        """获取空间信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, join_key, creator_username, status, 
                   grid_size, grid_width, grid_height, start_x, start_y,
                   processed_image_base64, pixel_metadata, created_at, last_accessed
            FROM spaces WHERE id = %s
        ''', (space_id,))
        
        space = cursor.fetchone()
        if not space:
            cursor.close()
            conn.close()
            return None
        
        # 获取空间用户列表
        cursor.execute('''
            SELECT username, role, joined_at 
            FROM space_users 
            WHERE space_id = %s 
            ORDER BY joined_at
        ''', (space_id,))
        
        users = cursor.fetchall()
        
        cursor.close()
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
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT role FROM space_users WHERE space_id = %s AND username = %s', (space_id, username))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result[0] if result else None
    
    def mark_pixel_complete(self, space_id, username, x, y):
        """标记像素为已完成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查用户是否在空间中
            role = self.get_user_role(space_id, username)
            if not role:
                return {'error': '用户不在空间中'}
            
            # 插入用户完成记录
            try:
                cursor.execute('''
                    INSERT INTO user_completions (space_id, username, x, y)
                    VALUES (%s, %s, %s, %s)
                ''', (space_id, username, x, y))
            except psycopg2.IntegrityError:
                # 如果已经完成过，忽略重复插入
                return {'success': True, 'message': '像素已完成'}
            
            # 更新空间最后访问时间
            cursor.execute('UPDATE spaces SET last_accessed = CURRENT_TIMESTAMP WHERE id = %s', (space_id,))
            
            conn.commit()
            
            return {'success': True}
            
        except Exception as e:
            conn.rollback()
            return {'error': str(e)}
        finally:
            cursor.close()
            conn.close()
    
    def get_space_pixel_data(self, space_id):
        """获取空间的完整像素数据（元数据 + 用户完成状态）"""
        space_info = self.get_space_info(space_id)
        if not space_info:
            return None
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取所有用户完成记录
        cursor.execute('''
            SELECT x, y, username 
            FROM user_completions 
            WHERE space_id = %s
        ''', (space_id,))
        
        completions = cursor.fetchall()
        cursor.close()
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
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_inactive)
        
        cursor.execute('''
            UPDATE spaces 
            SET status = 'archived' 
            WHERE status = 'active' 
            AND last_accessed < %s
        ''', (cutoff_date,))
        
        archived_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        return archived_count
    
    def batch_mark_pixels_complete(self, space_id, username, pixels):
        """批量标记像素为已完成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查用户是否在空间中
            role = self.get_user_role(space_id, username)
            if not role:
                return {'error': '用户不在空间中'}
            
            # 检查批量大小限制（最多40个）
            if len(pixels) > 40:
                return {'error': '批量提交超过40个像素限制'}
            
            # 使用事务确保原子性
            cursor.execute('BEGIN')
            
            completed_count = 0
            conflict_pixels = []
            
            # 批量插入用户完成记录
            for pixel in pixels:
                x = pixel['x']
                y = pixel['y']
                
                try:
                    cursor.execute('''
                        INSERT INTO user_completions (space_id, username, x, y)
                        VALUES (%s, %s, %s, %s)
                    ''', (space_id, username, x, y))
                    completed_count += 1
                except psycopg2.IntegrityError:
                    # 如果已经完成过，记录冲突但不中断
                    conflict_pixels.append({'x': x, 'y': y})
                    continue
            
            # 记录批量提交（用于审计）
            if completed_count > 0:
                cursor.execute('''
                    INSERT INTO batch_submissions (space_id, username, completed_pixels, pixel_count)
                    VALUES (%s, %s, %s, %s)
                ''', (space_id, username, json.dumps(pixels), completed_count))
            
            # 更新空间最后访问时间
            cursor.execute('UPDATE spaces SET last_accessed = CURRENT_TIMESTAMP WHERE id = %s', (space_id,))
            
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
            cursor.close()
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
