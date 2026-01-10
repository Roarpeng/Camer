import cv2
import numpy as np
import logging

logger = logging.getLogger("CamerApp")

class ImageProcessor:
    def __init__(self):
        self.mask = None
        self.baseline = None
        self.threshold = 50   # Difference threshold per pixel
        self.min_area = 500   # Minimum number of pixels to trigger (noise filter)
        self.baseline_brightness = None

    def set_mask(self, mask_path):
        """Loads a mask image and converts to binary."""
        if not mask_path:
            self.mask = None
            return

        try:
            # Load as grayscale
            mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask_img is None:
                logger.error(f"Failed to load mask: {mask_path}")
                return

            # Threshold to binary (ensure 0 or 255)
            _, self.mask = cv2.threshold(mask_img, 127, 255, cv2.THRESH_BINARY)
            logger.info(f"遮罩设置成功: {mask_path}")
        except Exception as e:
            logger.error(f"Error setting mask: {e}")

    def set_baseline(self, frame):
        """Sets the current frame as the baseline reference."""
        if frame is None:
            return

        # 降采样到 645x360 进行处理
        small_frame = cv2.resize(frame, (645, 360))

        # Mask 安全检查 - 确保 mask 尺寸匹配 small_frame
        if self.mask is not None:
            if self.mask.shape != small_frame.shape[:2]:
                self.mask = cv2.resize(self.mask, (645, 360), interpolation=cv2.INTER_NEAREST)

        # Convert to gray and blur slightly to reduce noise
        # 使用 11x11 核代替 21x21，性能提升约 70%，降噪效果基本相同
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        self.baseline = cv2.GaussianBlur(gray, (11, 11), 0)
        self.baseline_brightness = self.get_current_brightness(small_frame)
        logger.info(f"基准已建立。基准亮度: {self.baseline_brightness:.2f}")

    def process(self, frame):
        """
        Processes the frame with downsampling for performance:
        1. Downsample frame to 645x360 for processing
        2. Check and resize mask to match small frame
        3. Diff against baseline (if baseline exists)
        4. Apply mask and threshold
        Returns: (original_frame, is_triggered, diff_count, current_brightness)
        """
        # Only process if baseline has been established
        if self.baseline is None:
            # Return original frame without processing if no baseline
            # 同时计算亮度用于后续扫描
            small_frame = cv2.resize(frame, (645, 360))
            current_brightness = self.get_current_brightness(small_frame)
            return frame, False, 0, current_brightness

        # 第一步：降采样到 645x360
        small_frame = cv2.resize(frame, (645, 360))

        # 第二步：Mask 安全检查 - 每帧检查 shape 确保绝对稳定
        if self.mask is not None:
            if self.mask.shape != small_frame.shape[:2]:
                self.mask = cv2.resize(self.mask, (645, 360), interpolation=cv2.INTER_NEAREST)

        # 第三步：使用 small_frame 进行计算
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        # 使用 11x11 核代替 21x21，性能提升约 70%
        blur = cv2.GaussianBlur(gray, (11, 11), 0)

        # 1. Absolute Difference
        frame_delta = cv2.absdiff(self.baseline, blur)

        # 2. Thresholding
        _, thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)

        # 3. Apply Mask (if exists)
        if self.mask is not None:
            thresh = cv2.bitwise_and(thresh, thresh, mask=self.mask)

        # 4. Count non-zero pixels
        diff_count = cv2.countNonZero(thresh)
        is_triggered = diff_count > self.min_area

        # 5. 计算当前亮度（使用 small_frame）
        current_brightness = self.get_current_brightness(small_frame)

        # 返回原始大图 frame（用于 UI 清晰显示），而不是 small_frame
        return frame, is_triggered, diff_count, current_brightness

    def get_current_brightness(self, frame):
        """Calculates mean brightness within the masked region."""
        if frame is None:
            return 0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.mask is not None:
            # Mask 应该已经在外部调整为正确尺寸
            mean_val = cv2.mean(gray, mask=self.mask)[0]
        else:
            mean_val = cv2.mean(gray)[0]

        return mean_val
    
    
