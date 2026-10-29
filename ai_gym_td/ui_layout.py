"""Logical layout and inverse pointer mapping, independent of game rules."""
import pygame


class GameLayout:
    size = (1280, 720)
    map_rect = pygame.Rect(16, 88, 960, 576)
    shop_rect = pygame.Rect(992, 88, 272, 576)

    def __init__(self, columns=20, rows=12):
        self.columns, self.rows = columns, rows
        self.cell = min(self.map_rect.width / columns, self.map_rect.height / rows)
        self.grid_rect = pygame.Rect(self.map_rect.x, self.map_rect.y,
                                     round(columns*self.cell), round(rows*self.cell))

    def viewport(self, window_size):
        width, height = window_size
        scale = min(width/self.size[0], height/self.size[1])
        w, h = round(self.size[0]*scale), round(self.size[1]*scale)
        return pygame.Rect((width-w)//2, (height-h)//2, w, h)

    def to_logical(self, position, window_size):
        viewport = self.viewport(window_size)
        if not viewport.collidepoint(position):
            return None
        return ((position[0]-viewport.x)*self.size[0]/viewport.width,
                (position[1]-viewport.y)*self.size[1]/viewport.height)

    def grid_at(self, logical):
        if logical is None or not self.grid_rect.collidepoint(logical):
            return None
        return (int((logical[0]-self.grid_rect.x)/self.cell),
                int((logical[1]-self.grid_rect.y)/self.cell))

    def center(self, x, y):
        return (round(self.grid_rect.x+(x+0.5)*self.cell),
                round(self.grid_rect.y+(y+0.5)*self.cell))
