#!/usr/bin/env python3
"""
Click-to-blur tool for anonymizing faces in images.

Usage:
    python blur_faces.py <image_path>

Controls:
    Left-click  : Apply blur at cursor position
    +/=         : Increase blur radius
    -           : Decrease blur radius
    ]           : Increase blur strength
    [           : Decrease blur strength
    u           : Undo last blur
    q           : Save result and quit
    Esc         : Quit without saving
"""

import argparse
import os
import sys

import cv2
import numpy as np


class BlurTool:
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.original = cv2.imread(image_path)
        if self.original is None:
            print(f"Error: Could not load image '{image_path}'", file=sys.stderr)
            sys.exit(1)

        self.image = self.original.copy()
        self.history: list[np.ndarray] = []
        self.radius = 50
        self.blur_strength = 51  # Must be odd; adjustable with [ and ]
        self.mouse_pos = (-1, -1)
        self.window_name = "Blur Tool  |  click: blur  +/-: radius  u: undo  q: save & quit"

    # ------------------------------------------------------------------ #
    #  Drawing helpers                                                     #
    # ------------------------------------------------------------------ #
    def _display_frame(self) -> np.ndarray:
        """Return the current image with a preview circle overlay."""
        frame = self.image.copy()
        mx, my = self.mouse_pos
        if mx >= 0 and my >= 0:
            cv2.circle(frame, (mx, my), self.radius, (0, 255, 0), 2)
            # Show current radius in top-left corner
        cv2.putText(
            frame,
            f"Radius: {self.radius}  Blur: {self.blur_strength}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        return frame

    # ------------------------------------------------------------------ #
    #  Blur logic                                                          #
    # ------------------------------------------------------------------ #
    def _apply_blur(self, cx: int, cy: int) -> None:
        """Apply a circular Gaussian blur centred at (cx, cy)."""
        h, w = self.image.shape[:2]
        r = self.radius

        # Bounding box clamped to image bounds
        x1 = max(cx - r, 0)
        y1 = max(cy - r, 0)
        x2 = min(cx + r, w)
        y2 = min(cy + r, h)

        if x2 <= x1 or y2 <= y1:
            return

        # Save state for undo
        self.history.append(self.image.copy())

        # Extract ROI and blur it
        roi = self.image[y1:y2, x1:x2]
        ksize = self.blur_strength | 1  # ensure odd
        sigma = ksize / 3.0
        blurred_roi = cv2.GaussianBlur(roi, (ksize, ksize), sigma)

        # Create a circular mask so the blur blends naturally
        mask = np.zeros(roi.shape[:2], dtype=np.uint8)
        # Circle centre relative to ROI
        cv2.circle(mask, (cx - x1, cy - y1), r, 255, -1)
        mask_3ch = cv2.merge([mask, mask, mask])

        # Blend: keep original where mask==0, use blurred where mask==255
        roi_out = np.where(mask_3ch == 255, blurred_roi, roi)
        self.image[y1:y2, x1:x2] = roi_out

    # ------------------------------------------------------------------ #
    #  Mouse callback                                                      #
    # ------------------------------------------------------------------ #
    def _mouse_callback(self, event: int, x: int, y: int, flags: int, param) -> None:
        if event == cv2.EVENT_MOUSEMOVE:
            self.mouse_pos = (x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            self._apply_blur(x, y)

    # ------------------------------------------------------------------ #
    #  Output path                                                         #
    # ------------------------------------------------------------------ #
    def _output_path(self) -> str:
        base, ext = os.path.splitext(self.image_path)
        return f"{base}_blurred{ext}"

    # ------------------------------------------------------------------ #
    #  Main loop                                                           #
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        # Fit large images to screen while keeping aspect ratio
        h, w = self.image.shape[:2]
        screen_w, screen_h = 1920, 1080
        if w > screen_w or h > screen_h:
            scale = min(screen_w / w, screen_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            cv2.resizeWindow(self.window_name, new_w, new_h)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        while True:
            cv2.imshow(self.window_name, self._display_frame())
            key = cv2.waitKey(30) & 0xFF

            if key == ord("q"):
                out = self._output_path()
                cv2.imwrite(out, self.image)
                print(f"Saved blurred image to: {out}")
                break

            elif key == 27:  # Esc — quit without saving
                print("Exited without saving.")
                break

            elif key in (ord("+"), ord("=")):
                self.radius = min(self.radius + 10, 300)
                print(f"Radius: {self.radius}")

            elif key == ord("-"):
                self.radius = max(self.radius - 10, 10)
                print(f"Radius: {self.radius}")

            elif key == ord("]"):
                self.blur_strength = min(self.blur_strength + 10, 199)
                print(f"Blur strength: {self.blur_strength}")

            elif key == ord("["):
                self.blur_strength = max(self.blur_strength - 10, 11)
                print(f"Blur strength: {self.blur_strength}")

            elif key == ord("u"):
                if self.history:
                    self.image = self.history.pop()
                    print("Undo.")
                else:
                    print("Nothing to undo.")

        cv2.destroyAllWindows()


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Click on faces in an image to blur them."
    )
    parser.add_argument("image", help="Path to the input image")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print(f"Error: File '{args.image}' not found.", file=sys.stderr)
        sys.exit(1)

    tool = BlurTool(args.image)
    tool.run()


if __name__ == "__main__":
    main()
