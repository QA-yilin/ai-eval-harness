# datasets/aigc_assets.py  动态生成一张非常逼真的“电商主图”以及它的篡改版本
from PIL import Image, ImageDraw, ImageFont
import os


def generate_ecommerce_assets():
    os.makedirs("datasets/images", exist_ok=True)

    # 1. 模拟 AI 生成的高质量电商主图 (白底，带一个蓝色的商品包，带价格标签)
    img = Image.new('RGB', (600, 600), color='white')
    d = ImageDraw.Draw(img)
    # 画一个商品
    d.rounded_rectangle([150, 150, 450, 450], radius=20, fill='navy', outline='black', width=3)
    d.text((280, 280), "Premium Bag", fill="white")
    # 画一个官方正品标签
    d.rectangle([400, 400, 550, 480], fill='gold')
    d.text((420, 420), "OFFICIAL", fill="black")

    original_path = "images/official_bag.png"
    img.save(original_path)

    # 2. 模拟被黑产篡改的图片 (把官方标签抹去，或者加上虚假水印)
    img_tampered = img.copy()
    d2 = ImageDraw.Draw(img_tampered)
    # 抹掉官方标签，盖上假水印
    d2.rectangle([400, 400, 550, 480], fill='white')
    d2.text((420, 420), "FAKE COPY", fill="red")

    tampered_path = "images/tampered_bag.png"
    img_tampered.save(tampered_path)

    print(f"✅ 已生成真实业务资产：\n1. 原图: {original_path}\n2. 篡改图: {tampered_path}")


if __name__ == "__main__":
    generate_ecommerce_assets()