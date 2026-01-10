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
        self.rois = []  # 独立的 ROI 区域列表 (每个包含 contour, bounding_rect, sub_mask)

    def set_mask(self, mask_path):
        """Loads a mask image and converts to binary, then extracts independent ROI regions."""
        if not mask_path:
            self.mask = None
            self.rois = []
            return

        try:
            # Load as grayscale
            mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask_img is None:
                logger.error(f"Failed to load mask: {mask_path}")
                return

            # Threshold to binary (ensure 0 or 255)
            _, self.mask = cv2.threshold(mask_img, 127, 255, cv2.THRESH_BINARY)

            # 解析独立的连通区域
            self.rois = []
            contours, _ = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                # 获取边界框
                x, y, w, h = cv2.boundingRect(contour)
                # 创建该 ROI 的子 mask
                sub_mask = np.zeros_like(self.mask)
                cv2.drawContours(sub_mask, [contour], -1, 255, -1)

                # 存储 ROI 信息
                roi = {
                    'contour': contour,
                    'bounding_rect': (x, y, w, h),
                    'sub_mask': sub_mask
                }
                self.rois.append(roi)

            logger.info(f"遮罩设置成功: {mask_path}, 解析出 {len(self.rois)} 个独立 ROI 区域")
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
                # 重新解析 ROI 区域
                self._reparse_rois()

        # Convert to gray and blur slightly to reduce noise
        # 使用 11x11 核代替 21x21，性能提升约 70%，降噪效果基本相同
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        self.baseline = cv2.GaussianBlur(gray, (11, 11), 0)
        self.baseline_brightness = self.get_current_brightness(small_frame)
        logger.info(f"基准已建立。基准亮度: {self.baseline_brightness:.2f}")

    def _reparse_rois(self):
        """重新解析 ROI 区域（在 mask 尺寸调整后调用）"""
        if self.mask is None:
            self.rois = []
            return

        self.rois = []
        contours, _ = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            sub_mask = np.zeros_like(self.mask)
            cv2.drawContours(sub_mask, [contour], -1, 255, -1)

            roi = {
                'contour': contour,
                'bounding_rect': (x, y, w, h),
                'sub_mask': sub_mask
            }
            self.rois.append(roi)

    def process(self, frame):
        """
        Processes the frame with independent ROI detection:
        1. Downsample frame to 645x360 for processing
        2. Apply mask visualization (dim non-ROI areas)
        3. Calculate diff and detect changes in each ROI independently
        4. Draw static ROI contours on triggered regions
        Returns: (vis_frame, is_triggered, total_diff_count, current_brightness)
        """
        # 降采样到 645x360
        small_frame = cv2.resize(frame, (645, 360))

        # 步骤1：可视化 - 叠加遮罩效果（将非 ROI 区域变暗）
        vis_frame = small_frame.copy()
        if self.mask is not None:
            # 确保 mask 尺寸匹配
            if self.mask.shape != small_frame.shape[:2]:
                self.mask = cv2.resize(self.mask, (645, 360), interpolation=cv2.INTER_NEAREST)
                self._reparse_rois()

            # 创建半透明遮罩层（非 ROI 区域变暗）
            mask_overlay = np.zeros_like(small_frame)
            mask_overlay[self.mask == 0] = [0, 0, 0]  # 非 ROI 区域变黑
            vis_frame = cv2.addWeighted(vis_frame, 0.7, mask_overlay, 0.3, 0)

        # 如果没有基线，只返回可视化图像
        if self.baseline is None:
            current_brightness = self.get_current_brightness(small_frame)
            # 将 vis_frame resize 回原始尺寸用于显示
            h, w = frame.shape[:2]
            display_frame = cv2.resize(vis_frame, (w, h), interpolation=cv2.INTER_LINEAR)
            return display_frame, False, 0, current_brightness

        # 步骤2：检测 - 计算高斯模糊和差分
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (11, 11), 0)
        frame_delta = cv2.absdiff(self.baseline, blur)
        _, thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)

        # 步骤3：ROI 独立判断
        is_triggered = False
        total_diff_count = 0

        if self.rois:
            # 遍历每个 ROI 区域
            for roi in self.rois:
                sub_mask = roi['sub_mask']
                contour = roi['contour']

                # 仅计算该 ROI 区域内的差异像素数量
                roi_diff = cv2.bitwise_and(thresh, thresh, mask=sub_mask)
                diff_count = cv2.countNonZero(roi_diff)
                total_diff_count += diff_count

                # 如果该 ROI 触发阈值
                if diff_count > self.min_area:
                    is_triggered = True
                    # 在 vis_frame 上绘制该 ROI 的静态外轮廓（红色线条）
                    cv2.drawContours(vis_frame, [contour], -1, (0, 0, 255), 2)
        else:
            # 没有 ROI 时的全局检测
            total_diff_count = cv2.countNonZero(thresh)
            is_triggered = total_diff_count > self.min_area

        # 计算当前亮度
        current_brightness = self.get_current_brightness(small_frame)

        # 将 vis_frame resize 回原始尺寸用于显示
        h, w = frame.shape[:2]
        display_frame = cv2.resize(vis_frame, (w, h), interpolation=cv2.INTER_LINEAR)

        return display_frame, is_triggered, total_diff_count, current_brightness

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
    
    
