from PIL import Image
import numpy as np
import io
import base64
import hashlib

class ImageProcessor:
    def __init__(self):
        # 固定的32种颜色调色板
        self.FIXED_PALETTE = [
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
    
    def rgb_to_hex(self, rgb):
        """将RGB转换为十六进制颜色代码"""
        return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
    
    def hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def get_color_palette(self):
        """返回固定的32种颜色调色板"""
        return [self.hex_to_rgb(color) for color in self.FIXED_PALETTE]
    
    def find_closest_color(self, target_color, palette):
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
    
    def get_color_position(self, index):
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
    
    def pixelate_image(self, image, grid_size):
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
        fixed_palette = self.get_color_palette()
        pixels = np.array(pixelated_rgb)
        
        # 对每个像素找到最接近的固定颜色
        for x in range(pixels.shape[0]):
            for y in range(pixels.shape[1]):
                original_color = tuple(int(c) for c in pixels[x, y])
                closest_color, _ = self.find_closest_color(original_color, fixed_palette)
                pixels[x, y] = closest_color
        
        # 从NumPy数组重新创建图像
        processed_image = Image.fromarray(pixels.astype('uint8'), 'RGB')
        
        return processed_image, new_width, new_height
    
    def generate_coloring_list(self, pixelated_image, grid_width, grid_height, start_x=0, start_y=0):
        """生成所有像素点的填色列表（元数据）"""
        rgb_image = pixelated_image.convert('RGB')
        pixels = np.array(rgb_image)
        
        coloring_metadata = []
        fixed_palette = self.get_color_palette()
        
        # 遍历所有像素点
        for x in range(grid_height):
            for y in range(grid_width):
                original_color = tuple(int(c) for c in pixels[x, y])
                
                # 在固定调色板中找到最接近的颜色
                closest_color, color_index = self.find_closest_color(original_color, fixed_palette)
                closest_color_hex = self.rgb_to_hex(closest_color)
                color_position = self.get_color_position(color_index)
                
                coloring_metadata.append({
                    'x': x,
                    'y': y,
                    'color': closest_color_hex,
                    'color_rgb': closest_color,
                    'color_index': color_index,
                    'color_position': color_position,
                    'display_x': x + start_x,
                    'display_y': y + start_y
                })
        
        return coloring_metadata, fixed_palette
    
    def process_image_for_space(self, image_file, grid_size, start_x=0, start_y=0):
        """为空间处理图像，返回所有必要信息"""
        # 读取文件内容用于生成哈希
        file_content = image_file.read()
        image_file.seek(0)  # 重置文件指针
        
        # 生成图像哈希
        image_hash = self.generate_image_hash(file_content)
        
        # 处理图像
        image = Image.open(image_file)
        pixelated_image, grid_width, grid_height = self.pixelate_image(image, grid_size)
        
        # 生成填色元数据
        coloring_metadata, palette = self.generate_coloring_list(
            pixelated_image, grid_width, grid_height, start_x, start_y
        )
        
        # 将处理后的图像转换为base64
        output_buffer = io.BytesIO()
        pixelated_image.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        image_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        return {
            'original_image_hash': image_hash,
            'processed_image_base64': image_base64,
            'grid_size': grid_size,
            'grid_width': grid_width,
            'grid_height': grid_height,
            'pixel_metadata': coloring_metadata,  # 改为pixel_metadata
            'color_palette': [self.rgb_to_hex(color) for color in palette],
            'image_size': pixelated_image.size
        }
    
    def generate_image_hash(self, file_content):
        """生成图像内容的哈希值"""
        return hashlib.md5(file_content).hexdigest()
    
    def image_to_base64(self, image):
        """将PIL图像转换为base64字符串"""
        output_buffer = io.BytesIO()
        image.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        return base64.b64encode(output_buffer.getvalue()).decode('utf-8')
