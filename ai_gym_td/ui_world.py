"""Read-only world rendering: sprites never participate in simulation."""
import math
import pygame

from ai_gym_td.config import TILE_GRASS, TILE_BLOCKED, TILE_SPAWN, TILE_BASE

TOWER_COLORS = {"archer": (115, 208, 151), "cannon": (240, 154, 105),
                "ice": (110, 204, 242), "tesla": (236, 211, 113)}


class WorldRenderer:
    def __init__(self, layout, assets):
        self.layout, self.assets = layout, assets
        self._grid = None
        self.terrain = None

    def _terrain(self, game):
        layout, bank = self.layout, self.assets
        cell = round(layout.cell)
        self.terrain = pygame.Surface(layout.grid_rect.size)
        grass = bank.image("grass",cell).copy()
        grass.fill((155,185,160,255),special_flags=pygame.BLEND_RGBA_MULT)
        road = bank.image("road",cell)
        for y,row in enumerate(game.grid):
            for x,tile in enumerate(row):
                rect = pygame.Rect(x*cell,y*cell,cell,cell)
                self.terrain.blit(grass,rect)
                if tile not in (TILE_GRASS,TILE_BLOCKED):
                    self.terrain.blit(road,rect)
                    for dx,dy,p1,p2 in [
                        (0,-1,rect.topleft,rect.topright),(0,1,rect.bottomleft,rect.bottomright),
                        (-1,0,rect.topleft,rect.bottomleft),(1,0,rect.topright,rect.bottomright)]:
                        nx,ny=x+dx,y+dy
                        if not (0<=nx<game.cfg.width and 0<=ny<game.cfg.height) or game.grid[ny][nx] in (TILE_GRASS,TILE_BLOCKED):
                            pygame.draw.line(self.terrain,(220,178,117),p1,p2,3)
                elif tile==TILE_BLOCKED:
                    sprite=bank.image("rock",cell-7)
                    self.terrain.blit(sprite,sprite.get_rect(center=rect.center))
                # Tiny grass seams make the build grid legible without large boxes.
                elif (x+y)%2==0:
                    pygame.draw.line(self.terrain,(35,124,66),rect.topleft,(rect.left+8,rect.top),1)
                if tile in (TILE_SPAWN,TILE_BASE):
                    color=(228,122,92) if tile==TILE_SPAWN else (119,217,232)
                    pygame.draw.rect(self.terrain,color,rect.inflate(-10,-12),2,border_radius=6)
                    label=bank.font(16).render("入口" if tile==TILE_SPAWN else "基地",True,(250,247,226))
                    self.terrain.blit(label,label.get_rect(center=rect.center))
        self._grid=game.grid

    def draw(self, surface, game):
        layout,bank=self.layout,self.assets
        if self._grid is not game.grid:
            self._terrain(game)
        pygame.draw.rect(surface,(8,18,24),layout.grid_rect.inflate(8,8),border_radius=6)
        surface.blit(self.terrain,layout.grid_rect)
        old_clip=surface.get_clip()
        surface.set_clip(layout.grid_rect)
        cell=round(layout.cell)
        # Empty foundations are the only buildable sites in the live ruleset.
        occupied = {(tower.x, tower.y) for tower in game.towers.values()}
        for x, y in sorted(getattr(game, "build_sites", ())):
            if (x, y) in occupied:
                continue
            cx, cy = layout.center(x, y)
            pygame.draw.circle(surface, (37, 64, 54), (cx, cy+2), cell//2-5)
            pygame.draw.circle(surface, (145, 151, 116), (cx, cy), cell//2-6)
            pygame.draw.circle(surface, (235, 215, 147), (cx, cy), cell//2-6, 2)
            pygame.draw.line(surface, (249, 237, 182), (cx-6, cy), (cx+6, cy), 2)
            pygame.draw.line(surface, (249, 237, 182), (cx, cy-6), (cx, cy+6), 2)
        for tower in game.towers.values():
            center=layout.center(tower.x,tower.y)
            base=bank.image("base",cell-6)
            surface.blit(base,base.get_rect(center=(center[0],center[1]+2)))
            pygame.draw.circle(surface,TOWER_COLORS[tower.spec.name],center,cell//2-5,2)
            angle=0
            target=game.enemies.get(tower.target_eid)
            if target:
                angle=-math.degrees(math.atan2(target.y-tower.y,target.x-tower.x))-90
            sprite=bank.image(tower.spec.name,cell-3,angle)
            surface.blit(sprite,sprite.get_rect(center=center))
            # Persistent type marker remains readable when turret silhouettes rotate.
            marker=(center[0]+cell//2-8,center[1]+cell//2-8)
            pygame.draw.circle(surface,TOWER_COLORS[tower.spec.name],marker,6)
            if tower.spec.name=="tesla":
                pygame.draw.lines(surface,(248,229,150),False,[(center[0]-2,center[1]-9),(center[0]+4,center[1]-2),(center[0]-3,center[1]+2),(center[0]+3,center[1]+9)],2)
            if hasattr(game, "tower_level"):
                badge = pygame.Rect(center[0]-21, center[1]-23, 19, 17)
                pygame.draw.rect(surface, (21,40,50), badge, border_radius=4)
                label = bank.font(18).render(str(game.tower_level(tower.tid)), True, (252,226,145))
                surface.blit(label, label.get_rect(center=badge.center))
        sizes={"scout":24,"grunt":29,"brute":38,"swarm":18}
        for enemy in game.enemies.values():
            center=layout.center(enemy.x,enemy.y)
            next_index=min(enemy.path_index+1,len(game.path)-1)
            tx,ty=game.path[next_index]
            angle=-math.degrees(math.atan2(ty-enemy.y,tx-enemy.x))
            if enemy.spec.name!="brute":angle-=90
            size=round(sizes[enemy.spec.name]*cell/48)
            sprite=bank.image(enemy.spec.name,size,angle)
            pygame.draw.ellipse(surface,(78,80,54),(center[0]-size//2,center[1]+size//4,size,size//3))
            surface.blit(sprite,sprite.get_rect(center=center))
            bar=pygame.Rect(center[0]-15,center[1]-size//2-6,30,4)
            pygame.draw.rect(surface,(49,47,38),bar,border_radius=2)
            fraction=max(0,min(1,enemy.hp/enemy.max_hp))
            pygame.draw.rect(surface,(239,137,113),(bar.x,bar.y,round(bar.width*fraction),bar.height),border_radius=2)
            if enemy.slow_mult<1:
                pygame.draw.circle(surface,(136,223,250),center,size//2,1)
        for projectile in game.projectiles.values():
            center=(round(layout.grid_rect.x+projectile.x*cell),round(layout.grid_rect.y+projectile.y*cell))
            color=TOWER_COLORS.get(projectile.kind,(252,222,139))
            pygame.draw.circle(surface,(45,57,47),center,4)
            pygame.draw.circle(surface,color,center,3)
        surface.set_clip(old_clip)
