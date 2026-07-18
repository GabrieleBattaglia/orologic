import io
import os
import threading
import xml.etree.ElementTree as ET
import copy

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import chess
from .image_exporter import generate_custom_svg, get_image_settings


def flatten_svg(svg_data):
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring(svg_data)
    defs = root.find(".//{http://www.w3.org/2000/svg}defs")
    if defs is None:
        return svg_data
    pieces = {}
    for g in defs.findall("{http://www.w3.org/2000/svg}g"):
        g_id = g.get("id")
        if g_id:
            pieces[g_id] = g
    uses = root.findall(".//{http://www.w3.org/2000/svg}use")
    parent_map = {c: p for p in root.iter() for c in p}
    for use in uses:
        href = use.get("href") or use.get("{http://www.w3.org/1999/xlink}href")
        if not href:
            continue
        piece_id = href.lstrip("#")
        if piece_id in pieces:
            new_g = ET.Element("{http://www.w3.org/2000/svg}g")
            for key, val in use.items():
                if key not in ["href", "{http://www.w3.org/1999/xlink}href"]:
                    new_g.set(key, val)
            referenced_g = pieces[piece_id]
            for k, v in referenced_g.items():
                if k != "id" and not new_g.get(k):
                    new_g.set(k, v)
            for child in referenced_g:
                new_g.append(copy.deepcopy(child))
            parent = parent_map.get(use)
            if parent is not None:
                idx = list(parent).index(use)
                parent.insert(idx, new_g)
                parent.remove(use)
                parent_map[new_g] = parent
                for c in new_g:
                    parent_map[c] = new_g
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def wrap_text(text, font, max_width):
    lines = []
    paragraphs = text.split("\n")
    for paragraph in paragraphs:
        words = paragraph.split(" ")
        current_line = []
        for word in words:
            if not word:
                continue
            test_line = " ".join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
    return lines


class PygameBoardWindow:
    def __init__(self, version):
        self.board = None
        self.node = None
        self.running = False
        self.thread = None
        self.update_event = threading.Event()
        self.lock = threading.Lock()
        self.version = version
        self.orientation_mode = "turn"
        self.width = 600
        self.height = 600
        self.config_size = 600
        self.show_text_mode = False
        self.last_text = ""

    def start(self, board, node=None):
        self.board = board.copy()
        self.node = node
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            self.thread = None

    def update_board(self, board, node=None):
        with self.lock:
            self.board = board.copy()
            self.node = node
        self.update_event.set()

    def trigger_update(self):
        self.update_event.set()

    def is_active(self):
        return self.running and self.thread and self.thread.is_alive()

    def set_orientation(self, mode):
        with self.lock:
            self.orientation_mode = mode
        self.update_event.set()

    def set_show_text_mode(self, enabled):
        with self.lock:
            self.show_text_mode = enabled
            if not enabled:
                self.last_text = ""
        self.update_event.set()

    def update_text(self, text):
        with self.lock:
            self.last_text = text
        self.update_event.set()

    def _run(self):
        pygame.init()
        settings = get_image_settings()
        self.config_size = settings.get("size", 600)
        self.width = self.config_size
        self.height = self.config_size
        screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        try:
            from .easyfish_app import show_output_on_board

            self.show_text_mode = show_output_on_board
        except Exception:
            pass
        try:
            from pygame._sdl2 import Window

            win = Window.from_display_module()
            win.maximize()
            pygame.event.pump()
            self.width, self.height = screen.get_size()
        except Exception:
            pass
        title = f"Orologic V{self.version} SCACCHIERA DIDATTICA"
        pygame.display.set_caption(title)
        clock = pygame.time.Clock()
        self._render(screen)
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    with self.lock:
                        self.width, self.height = event.w, event.h
                        screen = pygame.display.set_mode(
                            (self.width, self.height), pygame.RESIZABLE
                        )
                    self.update_event.set()
            if self.update_event.is_set():
                settings = get_image_settings()
                new_config_size = settings.get("size", 600)
                if new_config_size != self.config_size:
                    self.config_size = new_config_size
                    with self.lock:
                        self.width = new_config_size
                        self.height = new_config_size
                        screen = pygame.display.set_mode(
                            (self.width, self.height), pygame.RESIZABLE
                        )
                self._render(screen)
                self.update_event.clear()
            clock.tick(30)
        pygame.quit()

    def _render(self, screen):
        with self.lock:
            if self.board is None:
                return
            board_to_render = self.board.copy()
            node_to_render = self.node
            mode = self.orientation_mode
            width = self.width
            height = self.height
            show_text = self.show_text_mode
            text_val = self.last_text
        if mode == "white":
            orientation = chess.WHITE
        elif mode == "black":
            orientation = chess.BLACK
        else:
            orientation = board_to_render.turn
        try:
            reserved_height = min(int(height * 0.15), 140) if show_text else 0
            size = min(width, height - reserved_height)
            if size < 100:
                size = 100
            svg_data = generate_custom_svg(
                board_to_render,
                node_to_render,
                orientation=orientation,
                override_size=size,
            )
            flattened_svg = flatten_svg(svg_data)
            f = io.BytesIO(flattened_svg.encode("utf-8"))
            surf = pygame.image.load(f, "board.svg")
            if surf.get_width() != size or surf.get_height() != size:
                surf = pygame.transform.smoothscale(surf, (size, size))
            x_offset = (width - size) // 2
            y_offset = (height - reserved_height - size) // 2
            if y_offset < 0:
                y_offset = 0
            screen.fill((30, 30, 30))
            screen.blit(surf, (x_offset, y_offset))
            if show_text and reserved_height > 30:
                padding = max(4, reserved_height // 14)
                rect = pygame.Rect(
                    padding,
                    height - reserved_height + padding,
                    width - padding * 2,
                    reserved_height - padding * 2,
                )
                pygame.draw.rect(screen, (15, 15, 15), rect)
                pygame.draw.rect(screen, (90, 85, 71), rect, 2)
                font_size = max(16, min(24, reserved_height // 5))
                font = pygame.font.Font(None, font_size)
                line_spacing = font_size + 2
                lines = wrap_text(text_val, font, rect.width - padding * 4)
                max_lines = max(1, (rect.height - padding * 2) // line_spacing)
                y_start = rect.y + padding
                for line in lines[:max_lines]:
                    text_surf = font.render(line, True, (240, 235, 220))
                    screen.blit(text_surf, (rect.x + padding * 2, y_start))
                    y_start += line_spacing
            pygame.display.flip()
        except Exception:
            pass
