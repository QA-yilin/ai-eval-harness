from PIL import Image, ImageDraw, ImageFont

# 创建一张 500x500 的浅灰色图片
img = Image.new('RGB', (500, 500), color=(230, 230, 230))
draw = ImageDraw.Draw(img)

# 画一些几何图形代表“被测物体”（模拟一个柴犬的轮廓）
draw.rectangle([150, 200, 350, 400], fill=(139, 69, 19)) # 身体
draw.ellipse([200, 100, 300, 200], fill=(160, 82, 45))   # 头
draw.ellipse([220, 140, 240, 160], fill=(0, 0, 0))       # 左眼
draw.ellipse([260, 140, 280, 160], fill=(0, 0, 0))       # 右眼

# 写上说明文字
draw.text((150, 450), "Multimodal Test Image (Dog Mock)", fill=(0, 0, 0))

# 保存
img.save('images/test_dog.jpg')
print("✅ 专业测试图 test_dog.jpg 已生成！")