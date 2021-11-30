import os
import json
import math
import time
from queue import PriorityQueue
import sys
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "true"
import pygame as pg
SCALE = 64
WIDTH = 1250
HEIGHT = 775
SCALED = False
FPS = 60
pg.font.init()
FONT = pg.font.SysFont("Comic Sans MS", 16)
START_TIME = time.time()


class Path(pg.sprite.Sprite):
    def __init__(self, a, b, image_surface):
        self.image = image_surface
        pg.draw.polygon(
            image_surface,
            pg.Color(0, 0, 255),
            (a.topleft, a.topright, a.bottomleft, a.bottomleft, b.topleft, b.topright, b.bottomleft, b.bottomleft),
        )
        self.rect = self.image.get_rect()
        self.mask = pg.mask.from_surface(self.image)



def h(start, end):
    s_x, s_y = start
    e_x, e_y = end
    return ((s_x - e_x)**2 + (s_y - e_y)**2)**0.5


class Node(pg.sprite.Sprite):
    def __init__(self, location, col, row, width, state="none", f=float("inf"), g=float("inf"), h=float("inf")):
        super(Node, self).__init__()
        self.width = width
        self.location = location
        self.path = []
        self.state = state
        self.f = f
        self.g = g
        self.h = h
        self.col = col
        self.row = row
        self.neighbors = []
        self.image = pg.Surface((width, width))
        self.image.fill(pg.Color(0, 255, 0))
        self.rect = self.image.get_rect()
        self.rect.center = location
        self.mask = pg.mask.from_surface(self.image)

    def __lt__(self, other):
        if self.f != other.f:
            return self.f < other.f
        else:
            return False

    def get_neighbors(self, nodes, barriers):
        self.neighbors = []
        unchecked_neighbors = []
        try:
            unchecked_neighbors.append(nodes[self.row-1][self.col])
        except IndexError:
            pass

        try:
            unchecked_neighbors.append(nodes[self.row+1][self.col])
        except IndexError:
            pass

        try:
            unchecked_neighbors.append(nodes[self.row][self.col-1])
        except IndexError:
            pass

        try:
            unchecked_neighbors.append(nodes[self.row][self.col+1])

        except IndexError:
            pass

        for neighbor in unchecked_neighbors:
            if not check_collision_group(neighbor, pg.sprite.Group(barriers)):
                neighbor.path = list(self.path)
                neighbor.path.append(neighbor.location)
                self.neighbors.append(neighbor)

        return self.neighbors

    def __repr__(self):
        return f"(col: {self.col}, row: {self.row})"


def a_star(start_location, end_location, vertices_length, object_width, barriers, search_distance, acceptable_distance=0, other_conditions=None):
    # generate all of the nodes

    nodes = []
    row = 0

    start_x, start_y = start_location

    for x in range(
            start_x - (vertices_length*search_distance),
            start_x + (vertices_length*search_distance) + 1,
            vertices_length,
    ):
        nodes.append([])
        col = 0
        for y in range(
                start_y - (vertices_length*search_distance),
                start_y + (vertices_length*search_distance) + 1,
                vertices_length,
        ):
            location = (x, y)
            if location == start_location:
                start_node = node = Node(location, col, row, width=object_width, state="start", g=0)
                node.path = node.location
                start_node.path = start_node.location
            elif location == end_location:
                node = Node(location, col, row, width=object_width, state="end")
            else:
                node = Node(location, col, row, width=vertices_length, state="none")

            nodes[row].append(node)

            col += 1
        row += 1

    # actual algorithm

    open_set = PriorityQueue()
    open_set_list = []
    closed_list = []

    open_set.put(start_node)
    open_set_list.append(start_node)
    start_time = time.time()

    while not open_set.empty():
        current_node = open_set.get()
        open_set_list.remove(current_node)
        closed_list.append(current_node)

        if other_conditions is None:
            condition = True
        else:
            condition = other_conditions()

        if (current_node.state == "end" or h(current_node.location, end_location) <= acceptable_distance) and condition:
            path = list(current_node.path)
            path[0] = (path[0], path.pop(1))
            return path

        neighbors = current_node.get_neighbors(nodes, barriers)
        for neighbor in neighbors:
            if neighbor in closed_list:
                continue
            if neighbor in open_set_list:
                continue
            if neighbor.state == "start":
                continue

            neighbor.g = current_node.g + vertices_length
            neighbor.h = h(neighbor.location, end_location)
            neighbor.f = neighbor.g + neighbor.h

            open_set.put(neighbor)
            open_set_list.append(neighbor)


def get_data(data_id):
    with open(f"data/{data_id.replace(':', '/')}/data.json") as data_file:
        return json.load(data_file)


def check_collision_group(sprite, colliding):
    if issubclass(type(sprite), pg.sprite.GroupSingle):
        sprite = sprite.sprite
    collision = pg.sprite.spritecollide(sprite, colliding, False, pg.sprite.collide_mask)
    if collision:
        return collision
    else:
        return False


def relative_mouse():
    x, y = pg.mouse.get_pos()
    v_x, v_y, v_w, v_h = VIEWPORT
    return x + v_x, y + v_y


def trajectory(sprite, end_point, relative=False):
    try:
        if relative:
            s_x, s_y = pg.Rect(sprite.relative_x, sprite.relative_y, SCALE, SCALE).center
        else:
            s_x, s_y = sprite.rect.center

        x, y = sprite.rect.center

        m_x, m_y = end_point
        reference = 180 * math.atan(abs((m_y - s_y) / (m_x - s_x))) / math.pi
        if m_y < s_y:
            if m_x > s_x:
                new_angle = 360 - reference
            else:
                new_angle = 180 + reference
        else:
            if m_x > s_x:
                new_angle = reference
            else:
                new_angle = 180 - reference

        sprite.angle = new_angle
        sprite.image = pg.transform.rotate(sprite.image, 360 - new_angle)
        sprite.rect = sprite.image.get_rect()
        sprite.rect.center = (x, y)
    except ZeroDivisionError:
        pass


class Bullet(pg.sprite.Sprite):
    def __init__(self, bullet_id, location, target, target_group):
        super(Bullet, self).__init__()
        self.initial_location = location
        self.data = get_data(bullet_id)
        self.speed = self.data['speed']
        self.damage = self.data['damage']
        self.sprite_list = []
        self.target_group = target_group
        self.angle = 0
        if type(self.data['sprite']) == list:
            for sprite in self.health['sprite']:
                image = pg.image.load(sprite)
                image.convert_alpha()
                self.sprite_list.append(image)
        else:
            image = pg.image.load(self.data['sprite'])
            image.convert_alpha()
            self.sprite_list.append(image)
        self.image = self.sprite_list[0]
        self.rect = self.image.get_rect()
        self.rect.topleft = location
        trajectory(self, target)
        x, y = self.rect.center
        self.image = pg.transform.rotate(self.image, 270)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.change_y = math.sin((self.angle * math.pi / 180)) * self.speed
        self.change_x = math.cos((self.angle * math.pi / 180)) * self.speed
        self.mask = pg.mask.from_surface(self.image)
        self.relative_x = 0
        self.relative_y = 0

    def update(self, frame_number, level, enemies, player, projectiles):
        self.mask = pg.mask.from_surface(self.image)
        x, y, w, h = self.rect
        self.rect = pg.Rect(x + self.change_x, y + self.change_y, w, h)
        x, y = self.rect.topleft
        i_x, i_y = self.initial_location
        if abs(x - i_x) > 2500 or abs(x - i_x) > 2500:
            self.kill()
        collision = check_collision_group(self, self.target_group)
        if collision:
            try:
                for item in collision:
                    item.health -= self.damage
                self.kill()
            except AttributeError:
                pass

    def draw(self, surface):
        if self.rect.colliderect(pg.Rect(VIEWPORT)):
            x, y = self.rect.topleft
            v_x, v_y, v_w, v_h = VIEWPORT
            self.relative_x = x - v_x
            self.relative_y = y - v_y
            surface.blit(self.image, (self.relative_x, self.relative_y))

    def normal_draw(self, surface):
        surface.blit(self.image, self.rect)


class Level(pg.sprite.Sprite):
    def __init__(self, level_id):
        super(Level, self).__init__()
        self.data = get_data(level_id)
        self.sprite_list = []
        if type(self.data['sprite']) == list:
            for sprite in self.data['sprite']:
                image = pg.image.load(sprite)
                image.convert_alpha()
                self.sprite_list.append(image)
        else:
            image = pg.image.load(self.data['sprite'])
            image.convert_alpha()
            self.sprite_list.append(image)
        self.image = self.sprite_list[0]
        self.rect = self.image.get_rect()
        self.rect.topleft = (0, 0)
        self.mask = pg.mask.from_surface(self.image)
        self.relative_x = 0
        self.relative_y = 0

    def update(self, frame, level, enemies, player, projectiles):
        self.mask = pg.mask.from_surface(self.image)
        collision = check_collision_group(self, projectiles)
        if collision:
            try:
                for item in collision:
                    item.kill()
            except AttributeError:
                pass

    def draw(self, surface):
        x, y = self.rect.topleft
        v_x, v_y, v_w, v_h = VIEWPORT
        self.relative_x = x - v_x
        self.relative_y = y - v_y
        surface.blit(self.image, (self.relative_x, self.relative_y))

    def normal_draw(self, surface):
        surface.blit(self.image, self.rect)


class Character(pg.sprite.Sprite):
    def __init__(self, character_id, location):
        super(Character, self).__init__()
        self.data = get_data(character_id)
        self.health = self.data['health']
        self.speed = self.data['speed']
        self.sprite_list = []
        self.id = self.data['id']
        self.angle = 0
        if type(self.data['sprite']) == list:
            for sprite in self.health['sprite']:
                image = pg.image.load(sprite)
                image.convert_alpha()
                self.sprite_list.append(image)
        else:
            image = pg.image.load(self.data['sprite'])
            image.convert_alpha()
            self.sprite_list.append(image)
        self.image = self.sprite_list[0]
        self.rect = self.image.get_rect()
        self.rect.topleft = location
        self.mask = pg.mask.from_surface(self.image)
        self.relative_x = 0
        self.relative_y = 0
        self.path = []
        self.start_time = time.time()
        try:
            self.weapon = get_data(self.data['weapon'])
        except KeyError:
            pass

    def update(self, frame, level, enemies, player, projectiles):
        if len(self.sprite_list) > 1:
            self.image = self.sprite_list[frame // 6]
        else:
            self.image = self.sprite_list[0]
        x, y = self.rect.center
        self.image = pg.transform.rotate(self.image, 270)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.mask = pg.mask.from_surface(self.image)

    def draw(self, surface):
        if self.rect.colliderect(pg.Rect(VIEWPORT)):
            x, y = self.rect.topleft
            v_x, v_y, v_w, v_h = VIEWPORT
            self.relative_x = x - v_x
            self.relative_y = y - v_y
            surface.blit(self.image, (self.relative_x, self.relative_y))

    def normal_draw(self, surface):
        surface.blit(self.image, self.rect)


class Player(Character):
    def update(self, frame, level, enemies, player, projectiles):
        super(Player, self).update(frame, level, enemies, player, projectiles)
        if self.health <= 0:
            pg.quit()
            sys.exit()
        trajectory(self, relative_mouse())


class Enemy(Character):
    def update(self, frame, level, enemies, player, projectiles):
        super(Enemy, self).update(frame, level, enemies, player, projectiles)
        if self.health <= 0:
            self.kill()

        if (time.time() - self.start_time) % 2 < 0.05 and\
                h(self.rect.center, player.sprite.rect.center) <= self.data['track_range']:
            enemy_list = list(enemies)
            enemy_list.remove(self)
            path = a_star(
                self.rect.center,
                player.sprite.rect.center,
                self.speed,
                self.rect.width,
                (level, enemy_list),
                int((self.data['track_range']//self.speed)*1.5),
                acceptable_distance=self.data['acceptable_distance']
            )
            try:
                if len(path) > 1:
                    self.path = path
            except TypeError:
                pass

        if frame % 2 == 0:
            try:
                if len(self.path) > 0:
                    self.rect = self.image.get_rect()
                    self.rect.center = self.path[0]
                    self.path.remove(self.path[0])
            except (TypeError, ValueError, ):
                pass

        if (time.time() - self.start_time) % 3 < 0.05 and\
                h(self.rect.center, player.sprite.rect.center) <= self.data['track_range']:
            projectiles.add(Bullet(
                'projectiles:default',
                self.rect.topleft,
                player.sprite.rect.center,
                player,
            ))

        trajectory(self, pg.Rect(player.sprite.relative_x, player.sprite.relative_y, SCALE, SCALE).center, relative=True)

    def __init__(self, character_id, location, player, level):
        super(Enemy, self).__init__(character_id, location)


def draw_screen(screen, groups):
    screen.fill((255, 255, 255))
    for group in groups:
        try:
            for item in group:
                item.draw(screen)
        except TypeError:
            group.sprite.draw(screen)

    screen.blit(FONT.render(str(int(ACTUAL_FPS)), False, pg.Color(0, 0, 0)), (0, 0))

    pg.display.update()


def tick(frame_number, groups, level, enemies, player, projectiles):
    for group in groups:
        group.update(frame_number, level, enemies, player, projectiles)


def main(level_id):
    global WINDOW
    global VIEWPORT
    global ACTUAL_FPS
    START_TIME = time.time()
    BORDER = 128
    VIEWPORT = (0, 0, 1250, 775)
    TOTAL_FRAME = 0
    pressed_keys = []
    if SCALED:
        WINDOW = pg.display.set_mode((WIDTH, HEIGHT), pg.SCALED)
    else:
        WINDOW = pg.display.set_mode((WIDTH, HEIGHT))

    clock = pg.time.Clock()

    run = True
    enemies = pg.sprite.Group()
    projectiles = pg.sprite.Group()
    player = pg.sprite.GroupSingle(Player('characters:player', (500, 500)))
    level = pg.sprite.GroupSingle(Level(level_id))

    frame = 0

    while run:
        clock.tick(FPS)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                run = False

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_t:
                    enemies.add(Enemy("characters:enemies:tank", (relative_mouse()), player, level))

                pressed_keys.append(event.key)

            if event.type == pg.KEYUP:
                pressed_keys.remove(event.key)

            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    projectiles.add(Bullet(
                        'projectiles:default',
                        player.sprite.rect.topleft,
                        relative_mouse(),
                        enemies,
                    ))

        if pg.K_w in pressed_keys or pg.K_UP in pressed_keys:
            x, y, w, h = player.sprite.rect
            player.sprite.rect = pg.Rect(x, y - player.sprite.speed, w, h)
            if check_collision_group(player, pg.sprite.Group(enemies, level)):
                player.sprite.rect = pg.Rect(x, y, w, h)
        if pg.K_a in pressed_keys or pg.K_LEFT in pressed_keys:
            x, y, w, h = player.sprite.rect
            player.sprite.rect = pg.Rect(x - player.sprite.speed, y, w, h)
            if check_collision_group(player, pg.sprite.Group(enemies, level)):
                player.sprite.rect = pg.Rect(x, y, w, h)
        if pg.K_s in pressed_keys or pg.K_DOWN in pressed_keys:
            x, y, w, h = player.sprite.rect
            player.sprite.rect = pg.Rect(x, y + player.sprite.speed, w, h)
            if check_collision_group(player, pg.sprite.Group(enemies, level)):
                player.sprite.rect = pg.Rect(x, y, w, h)
        if pg.K_d in pressed_keys or pg.K_RIGHT in pressed_keys:
            x, y, w, h = player.sprite.rect
            player.sprite.rect = pg.Rect(x + player.sprite.speed, y, w, h)
            if check_collision_group(player, pg.sprite.Group(enemies, level)):
                player.sprite.rect = pg.Rect(x, y, w, h)

        frame += 1
        if frame > FPS:
            frame = 0
        TOTAL_FRAME += 1

        ACTUAL_FPS = (TOTAL_FRAME//(time.time()-START_TIME))

        draw_screen(WINDOW, (level, enemies, projectiles, player))
        tick(frame, (enemies, projectiles, player, level), level, enemies, player, projectiles)

        # Manage the viewport
        x, y = player.sprite.rect.center
        v_x, v_y, v_w, v_h = VIEWPORT

        if x - BORDER <= v_x:
            VIEWPORT = (v_x - player.sprite.speed, v_y, v_w, v_h)
            v_x -= player.sprite.speed

        if y - BORDER <= v_y:
            VIEWPORT = (v_x, v_y - player.sprite.speed, v_w, v_h)
            v_y -= player.sprite.speed

        if x + BORDER >= v_x + v_w:
            VIEWPORT = (v_x + player.sprite.speed, v_y, v_w, v_h)
            v_x += player.sprite.speed

        if y + BORDER >= v_y + v_h:
            VIEWPORT = (v_x, v_y + player.sprite.speed, v_w, v_h)
            v_y += player.sprite.speed


if __name__ == '__main__':
    main("levels:test")
