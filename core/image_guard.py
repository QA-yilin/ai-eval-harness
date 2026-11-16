import imagehash
from PIL import Image
import os

# ================= 自动获取绝对路径 =================
# 获取当前脚本所在的目录 (core)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (ai-eval-harness)
BASE_DIR = os.path.dirname(CURRENT_DIR)


class AIGCImageGuard:
    def __init__(self, threshold=5):
        self.threshold = threshold

    def verify_image_integrity(self, original_rel_path, target_rel_path):
        # 将传入的相对路径强转为基于根目录的绝对路径
        original_path = os.path.join(BASE_DIR, original_rel_path)
        target_path = os.path.join(BASE_DIR, target_rel_path)

        # 调试打印，如果还报错，你一眼就能看出它到底去哪里找图了
        print(f"正在读取原图: {original_path}")
        print(f"正在读取目标图: {target_path}")

        if not os.path.exists(original_path):
            return {"status": "ERROR", "message": f"找不到原图: {original_path}"}
        if not os.path.exists(target_path):
            return {"status": "ERROR", "message": f"找不到目标图: {target_path}"}

        try:
            hash_original = imagehash.phash(Image.open(original_path))
            hash_target = imagehash.phash(Image.open(target_path))

            diff = hash_original - hash_target

            if diff > self.threshold:
                return {
                    "status": "FAIL",
                    "message": f"🚨 发现篡改！图片汉明距离差异值为 {diff}，超过安全阈值 {self.threshold}。",
                    "diff_score": diff
                }
            else:
                return {
                    "status": "PASS",
                    "message": "✅ 图片指纹一致，未被篡改。",
                    "diff_score": diff
                }
        except Exception as e:
            return {"status": "ERROR", "message": f"解析失败: {e}"}


if __name__ == "__main__":
    guard = AIGCImageGuard()

    print("--- 测试 1：自校验 ---")
    res1 = guard.verify_image_integrity("datasets/images/official_bag.png", "datasets/images/official_bag.png")
    print(res1)

    print("\n--- 测试 2：防篡改校验 ---")
    res2 = guard.verify_image_integrity("datasets/images/official_bag.png", "datasets/images/tampered_bag.png")
    print(res2)