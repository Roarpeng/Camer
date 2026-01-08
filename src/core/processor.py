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
        
        # Convert to gray and blur slightly to reduce noise
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.baseline = cv2.GaussianBlur(gray, (21, 21), 0)
        self.baseline_brightness = self.get_current_brightness(frame)
        logger.info(f"基准已建立。基准亮度: {self.baseline_brightness:.2f}")

    def process(self, frame):
        """
        Processes the frame:
        1. Diff against baseline.
        2. Apply Mask.
        3. Check threshold.
        Returns: (processed_vis_frame, is_triggered, diff_count)
        """
        if self.baseline is None:
            self.set_baseline(frame)
            # If baseline is still None (e.g. empty frame), return original
            if self.baseline is None:
                return frame, False, 0
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # 1. Absolute Difference
        frame_delta = cv2.absdiff(self.baseline, blur)
        
        # 2. Thresholding
        _, thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)
        
        # 3. Apply Mask (if exists)
        vis_frame = frame.copy()
        if self.mask is not None:
            # Ensure mask size matches frame size
            if self.mask.shape != thresh.shape:
               self.mask = cv2.resize(self.mask, (thresh.shape[1], thresh.shape[0]))
            
            thresh = cv2.bitwise_and(thresh, thresh, mask=self.mask)
            # Visualization: also mask the original frame for display
            vis_frame = cv2.bitwise_and(vis_frame, vis_frame, mask=self.mask)

        # 4. Count non-zero pixels
        diff_count = cv2.countNonZero(thresh)
        is_triggered = diff_count > self.min_area
        
        # Visualization: Draw contours on the (potentially masked) vis_frame
        if is_triggered:
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                if cv2.contourArea(contour) < self.min_area:
                    continue
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(vis_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(vis_frame, "报警提示", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return vis_frame, is_triggered, diff_count

    def get_current_brightness(self, frame):
        """Calculates mean brightness within the masked region."""
        if frame is None:
            return 0
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.mask is not None:
            # Ensure mask size matches frame size
            if self.mask.shape != gray.shape:
                self.mask = cv2.resize(self.mask, (gray.shape[1], gray.shape[0]))
            mean_val = cv2.mean(gray, mask=self.mask)[0]
        else:
            mean_val = cv2.mean(gray)[0]
            
        return mean_val
