import logging

import pynput
from PIL import ImageGrab, ImageDraw, ImageFont
from PIL.ImageQt import ImageQt
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QLabel


class PapergamesManager:
    def __init__(
            self,
            logger: logging.Logger,
            left_top_corner_mouse: tuple,
            right_bottom_corner_mouse: tuple
    ):
        self.logger = logger

        self.left_top_corner_mouse = left_top_corner_mouse
        self.right_bottom_corner_mouse = right_bottom_corner_mouse
        self.square_size_mouse = (right_bottom_corner_mouse[0] - left_top_corner_mouse[0]) / 16

        self.mouse = pynput.mouse.Controller()
        self.original_mouse_position = self.mouse.position

    def move(self, x: int, y: int):
        self.mouse.position = (
            self.left_top_corner_mouse[0] + (x + 1) * self.square_size_mouse,
            self.left_top_corner_mouse[1] + (y + 1) * self.square_size_mouse
        )

        # noinspection PyTypeChecker
        self.mouse.click(pynput.mouse.Button.left)
        self.logger.debug(f"Click: {self.mouse.position}")

    def mouse_to_original_position(self):
        self.mouse.position = self.original_mouse_position
        self.logger.debug("Mouse to original position.")

    def get_last_move(self, label: QLabel = None) -> tuple[int, int]:
        try:
            image = ImageGrab.grab(bbox=(
                self.left_top_corner_mouse[0],
                self.left_top_corner_mouse[1],
                self.right_bottom_corner_mouse[0],
                self.right_bottom_corner_mouse[1]
            )).convert('L').point(lambda p: 255 if p > 200 else 0)
        except ValueError as e:
            self.logger.error(f"ValueError: {e}")
            self.logger.debug("No move found.")
            return -1, -1

        if label is not None:
            label.setPixmap(QtGui.QPixmap.fromImage(ImageQt(image)).scaledToWidth(
                350, mode=QtCore.Qt.SmoothTransformation
            ))

        try:
            for x in range(15):
                for y in range(15):
                    if image.getpixel(
                            ((x + 1) * self.square_size_mouse, (y + 1) * self.square_size_mouse)
                    ) == 255 and image.getpixel(
                        ((x + 1.2) * self.square_size_mouse, (y + 1.2) * self.square_size_mouse)
                    ) == 0:
                        self.logger.debug(f"Found last move: {x}, {y}")

                        if label is not None:
                            image_draw = ImageDraw.Draw(image)
                            font = ImageFont.truetype('NotoSans-Regular.ttf', 64)
                            image_draw.text((0, 0), f"{x},{y}", fill=0, font=font)

                            label.setPixmap(QtGui.QPixmap.fromImage(ImageQt(image)).scaledToWidth(
                                350, mode=QtCore.Qt.SmoothTransformation
                            ))

                        return x, y
        except IndexError as e:
            self.logger.error(f"IndexError: {e}")

        self.logger.debug("No move found.")
        return -1, -1
