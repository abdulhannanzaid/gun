import pygame
import random
import math
import sys

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ─── Init ─────────────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# ─── Constants ────────────────────────────────────────────────────────────────
W, H          = 1100, 720
FPS           = 60
PLAYER_R      = 22
BALL_R        = 11
HURDLE_COUNT  = 10

# Colors
BLACK  = (0,   0,   0)
WHITE  = (255, 255, 255)
GRAY   = (80,  80,  80)
LGRAY  = (160, 160, 170)
YELLOW = (255, 220,  30)
ORANGE = (255, 140,  20)
RED    = (220,  40,  40)
GREEN  = ( 50, 200,  80)
BLUE   = ( 60, 130, 255)
CYAN   = ( 30, 210, 210)
PURPLE = (180,  60, 240)
PINK   = (255, 100, 200)
SKIN   = (255, 205, 160)
BROWN  = ( 90,  50,  20)
DBROWN = ( 50,  25,   8)

BOT_COLORS = [RED, GREEN, ORANGE, PURPLE, CYAN, PINK,
              (255,180,50),(100,220,120),(200,80,120),
              (80,200,255),(255,120,80),(150,255,150)]
BOT_NAMES  = ["Blaze","Ember","Spark","Pyro","Ignis","Cinder",
              "Flame","Scorch","Sear","Brand","Flare","Torch"]

# Difficulty presets: (label, color, fuse_sec, tick_ms, bot_speed, throw_delay, human_target_prob)
DIFFICULTIES = {
    'EASY':   ('EASY',   GREEN,  9, 1100, 2.5, 55, 0.35),
    'MEDIUM': ('MEDIUM', YELLOW, 7,  950, 3.2, 28, 0.65),
    'HARD':   ('HARD',   RED,    5,  750, 4.1, 10, 0.92),
}
DIFF_ORDER = ['EASY', 'MEDIUM', 'HARD']


# ─── Sound ────────────────────────────────────────────────────────────────────
def make_sound(freq, duration, wave='sine'):
    sample_rate = 22050
    n = int(sample_rate * duration)
    try:
        if HAS_NUMPY:
            import numpy as _np
            t = _np.linspace(0, duration, n, False)
            w = (0.4 * _np.sin(2*math.pi*freq*t) if wave == 'sine'
                 else 0.4 * _np.sign(_np.sin(2*math.pi*freq*t)))
            data   = (w * 32767).astype(_np.int16)
            stereo = _np.ascontiguousarray(_np.column_stack([data, data]))
            return pygame.sndarray.make_sound(stereo)
    except Exception:
        pass
    import array
    samples = []
    for i in range(n):
        v = int(16000 * math.sin(2*math.pi*freq*i/sample_rate))
        samples += [v, v]
    return pygame.mixer.Sound(buffer=array.array('h', samples))

SND_THROW   = make_sound(520, 0.08)
SND_EXPLODE = make_sound(180, 0.45, 'square')
SND_WARN    = make_sound(900, 0.06)
SND_ELIM    = make_sound(280, 0.30, 'square')


# ─── Helpers ──────────────────────────────────────────────────────────────────
def clamp(v, lo, hi):       return max(lo, min(hi, v))
def dist2(ax,ay,bx,by):     return math.hypot(ax-bx, ay-by)


# ─── Hurdle ───────────────────────────────────────────────────────────────────
class Hurdle:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def collides_circle(self, cx, cy, r):
        rx = clamp(cx, self.rect.left, self.rect.right)
        ry = clamp(cy, self.rect.top,  self.rect.bottom)
        return math.hypot(cx-rx, cy-ry) < r

    def draw(self, surf):
        pygame.draw.rect(surf, BROWN,  self.rect)
        pygame.draw.rect(surf, DBROWN, self.rect, 2)
        if self.rect.w < W-5 and self.rect.h < H-5:
            n = max(1, self.rect.w // 18)
            for i in range(n):
                sx = self.rect.x + 9 + i*18
                pygame.draw.polygon(surf, RED,
                    [(sx, self.rect.y),(sx-5, self.rect.y-9),(sx+5, self.rect.y-9)])


def make_hurdles():
    hurdles = [Hurdle(0,0,W,14), Hurdle(0,H-14,W,14),
               Hurdle(0,0,14,H), Hurdle(W-14,0,14,H)]
    placed = 0
    for _ in range(3000):
        if placed >= HURDLE_COUNT: break
        rw = random.randint(45,95); rh = random.randint(30,65)
        rx = random.randint(80,W-rw-80); ry = random.randint(60,H-rh-60)
        ok = all(not(rx < h.rect.x+h.rect.w+50 and rx+rw > h.rect.x-50 and
                     ry < h.rect.y+h.rect.h+50 and ry+rh > h.rect.y-50)
                 for h in hurdles)
        if ok:
            hurdles.append(Hurdle(rx,ry,rw,rh)); placed += 1
    return hurdles

def hurdle_hit(hurdles, cx, cy, r):
    return any(h.collides_circle(cx,cy,r) for h in hurdles)

def safe_pos(hurdles, others):
    for _ in range(3000):
        x = random.randint(60, W-60)
        y = random.randint(60, H-60)
        if hurdle_hit(hurdles, x, y, PLAYER_R+10): continue
        if all(dist2(x,y,ox,oy) > 70 for ox,oy in others): return x, y
    return W//2, H//2


# ─── Player ───────────────────────────────────────────────────────────────────
class Player:
    def __init__(self, pid, name, color, x, y, is_human=False):
        self.id       = pid
        self.name     = name
        self.color    = color
        self.x        = float(x)
        self.y        = float(y)
        self.vx       = 0.0
        self.vy       = 0.0
        self.speed    = 3.5
        self.is_human = is_human
        self.has_ball = False
        self.alive    = True
        self._wx      = random.uniform(-1,1)
        self._wy      = random.uniform(-1,1)
        self._throw_timer = random.randint(20,60)

    def move(self, dx, dy, hurdles, all_players):
        length = math.hypot(dx, dy)
        if length > 0:
            self.vx = dx/length * self.speed
            self.vy = dy/length * self.speed
        else:
            self.vx *= 0.75; self.vy *= 0.75

        nx = self.x + self.vx
        if hurdle_hit(hurdles, nx, self.y, PLAYER_R): self.vx *= -0.3; nx = self.x
        self.x = clamp(nx, PLAYER_R+15, W-PLAYER_R-15)

        ny = self.y + self.vy
        if hurdle_hit(hurdles, self.x, ny, PLAYER_R): self.vy *= -0.3; ny = self.y
        self.y = clamp(ny, PLAYER_R+15, H-PLAYER_R-15)

        for o in all_players:
            if o is self or not o.alive: continue
            d = dist2(self.x,self.y,o.x,o.y)
            md = PLAYER_R*2+4
            if 0 < d < md:
                push = (md-d)/2
                ax = (self.x-o.x)/d*push; ay = (self.y-o.y)/d*push
                self.x = clamp(self.x+ax, PLAYER_R+15, W-PLAYER_R-15)
                self.y = clamp(self.y+ay, PLAYER_R+15, H-PLAYER_R-15)
                o.x    = clamp(o.x-ax,    PLAYER_R+15, W-PLAYER_R-15)
                o.y    = clamp(o.y-ay,    PLAYER_R+15, H-PLAYER_R-15)

    def draw(self, surf, time_left, fnt_sm, fnt_xs, tick):
        x, y = int(self.x), int(self.y)
        if self.has_ball:
            gc = (255,40,0) if time_left<=2 else (255,160,0)
            for r in range(PLAYER_R+18, PLAYER_R, -4):
                s = pygame.Surface((r*2+4,r*2+4), pygame.SRCALPHA)
                a = int(55*(PLAYER_R+18-r)/18)
                pygame.draw.circle(s,(*gc,a),(r+2,r+2),r)
                surf.blit(s,(x-r-2, y-r-2))

        pygame.draw.circle(surf, self.color, (x, y+12), 14)
        pygame.draw.circle(surf, SKIN,  (x, y-4), PLAYER_R)
        pygame.draw.circle(surf, self.color, (x, y-4), PLAYER_R, 2)

        es = 5 if (self.has_ball and time_left<=3) else 4
        pygame.draw.circle(surf, WHITE,(x-8,y-7),es)
        pygame.draw.circle(surf, WHITE,(x+8,y-7),es)
        pygame.draw.circle(surf, BLACK,(x-7,y-7),2)
        pygame.draw.circle(surf, BLACK,(x+7,y-7),2)

        if self.has_ball:
            mc = RED if time_left<=2 else ORANGE
            pygame.draw.arc(surf, mc, (x-9,y,18,12), 0, math.pi, 3)
        else:
            pygame.draw.arc(surf, (80,80,80),(x-7,y+2,14,9),math.pi,2*math.pi,2)

        sw = abs(math.sin(tick*0.07))*8
        if self.has_ball:
            pygame.draw.line(surf,SKIN,(x-PLAYER_R+2,y+6),(x-PLAYER_R-8,y-8),6)
            pygame.draw.line(surf,SKIN,(x+PLAYER_R-2,y+6),(x+PLAYER_R+8,y-8),6)
        else:
            pygame.draw.line(surf,SKIN,(x-PLAYER_R+2,y+6),(x-PLAYER_R-6,y+14+int(sw)),6)
            pygame.draw.line(surf,SKIN,(x+PLAYER_R-2,y+6),(x+PLAYER_R+6,y+14+int(sw)),6)

        label = (self.name+"!!!" if self.has_ball and time_left<=2 else
                 self.name+" ~"  if self.has_ball else self.name)
        lc = (RED if (self.has_ball and time_left<=2) else
              YELLOW if self.has_ball else
              BLUE if self.is_human else LGRAY)
        tag = fnt_sm.render(label, True, lc)
        tw  = tag.get_width()
        pygame.draw.rect(surf, BLACK,(x-tw//2-5,y-PLAYER_R-22,tw+10,16))
        surf.blit(tag,(x-tw//2, y-PLAYER_R-21))

        if self.is_human:
            pygame.draw.circle(surf, BLUE,(x,y-4),PLAYER_R+5,2)


# ─── Ball ─────────────────────────────────────────────────────────────────────
class Ball:
    THROW_FRAMES = 12

    def __init__(self, fuse):
        self.fuse      = fuse
        self.x = self.y = 0.0
        self.holder    = None
        self.flying    = False
        self.target    = None
        self.fx=self.fy=self.tx=self.ty = 0.0
        self.progress  = 0
        self.time_left = fuse

    def attach(self, player):
        self.holder    = player
        self.flying    = False
        self.target    = None
        self.progress  = 0
        self.time_left = self.fuse
        player.has_ball = True
        self.x = player.x+18; self.y = player.y-14

    def throw(self, from_p, to_p):
        from_p.has_ball = False
        self.holder  = None
        self.flying  = True
        self.target  = to_p
        self.fx,self.fy = from_p.x, from_p.y-14
        self.tx,self.ty = to_p.x,   to_p.y-14
        self.progress   = 0
        self.time_left  = self.fuse
        SND_THROW.play()

    def update(self):
        if not self.flying:
            if self.holder:
                self.x = self.holder.x+18; self.y = self.holder.y-14
            return None
        self.progress += 1
        t = self.progress / self.THROW_FRAMES
        self.x = self.fx + (self.tx-self.fx)*t
        self.y = self.fy + (self.ty-self.fy)*t
        if self.progress >= self.THROW_FRAMES:
            self.flying = False
            self.attach(self.target)
            return 'landed'
        return None

    def draw(self, surf, tick):
        if self.flying:
            t = self.progress / self.THROW_FRAMES
            for i in range(1,6):
                tp = max(0, t-i*0.07)
                tx_ = self.fx+(self.tx-self.fx)*tp
                ty_ = self.fy+(self.ty-self.fy)*tp
                r   = max(2, BALL_R-i)
                s   = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
                pygame.draw.circle(s,(255,200,0,max(20,100-i*18)),(r,r),r)
                surf.blit(s,(int(tx_)-r, int(ty_)-r))

        bx,by = int(self.x), int(self.y)
        tl    = self.time_left
        cc    = (255,30,0) if tl<=2 else (255,140,0) if tl<=4 else (255,220,0)
        pulse = int(abs(math.sin(tick*0.15))*5) if tl<=3 else 2
        for i in range(4,0,-1):
            s = pygame.Surface(((BALL_R+i*3+pulse)*2,)*2, pygame.SRCALPHA)
            r = BALL_R+i*3+pulse
            pygame.draw.circle(s,(*cc,40+i*15),(r,r),r)
            surf.blit(s,(bx-r, by-r))
        pygame.draw.circle(surf, cc,    (bx,by), BALL_R)
        pygame.draw.circle(surf, WHITE, (bx-3,by-3), 3)


# ─── Game ─────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self, n_opponents, diff_key):
        self.screen   = pygame.display.set_mode((W, H))
        pygame.display.set_caption("FIREBALL")
        self.clock    = pygame.time.Clock()
        self.font_lg  = pygame.font.Font(None, 64)
        self.font_md  = pygame.font.Font(None, 36)
        self.font_sm  = pygame.font.Font(None, 22)
        self.font_xs  = pygame.font.Font(None, 18)
        self.n_opp    = n_opponents
        self.diff_key = diff_key
        self.reset()

    def reset(self):
        cfg = DIFFICULTIES[self.diff_key]
        self.diff_label  = cfg[0]
        self.diff_color  = cfg[1]
        self.fuse_sec    = cfg[2]
        self.tick_ms     = cfg[3]
        self.bot_speed   = cfg[4]
        self.bot_delay   = cfg[5]
        self.human_prob  = cfg[6]

        self.hurdles          = make_hurdles()
        self.tick             = 0
        self.time_survived    = 0
        self.score            = 0
        self.last_tick_ms     = pygame.time.get_ticks()
        self.shake_frames     = 0
        self.shake_mag        = 0
        self.msg_text         = ''
        self.msg_frames       = 0
        self.game_over        = False
        self.eliminated_order = []
        self.last_survivor    = None
        self.background       = self._make_bg()

        spawned = []
        hx,hy   = safe_pos(self.hurdles, [])
        self.human  = Player(0,"YOU",BLUE,hx,hy,is_human=True)
        spawned.append((hx,hy))
        self.players = [self.human]

        for i in range(self.n_opp):
            x,y = safe_pos(self.hurdles, spawned)
            spawned.append((x,y))
            self.players.append(Player(i+1, BOT_NAMES[i%len(BOT_NAMES)],
                                       BOT_COLORS[i%len(BOT_COLORS)], x, y))

        self.ball = Ball(self.fuse_sec)
        starter   = random.choice([p for p in self.players if not p.is_human])
        self.ball.attach(starter)
        self._show_msg("Avoid the fireball — pass it fast!", 180)

    def _make_bg(self):
        surf = pygame.Surface((W,H))
        for y in range(H):
            v = int(10+(y/H)*30)
            pygame.draw.line(surf,(v,v,v+10),(0,y),(W,y))
        for x in range(0,W,40): pygame.draw.line(surf,(25,25,40),(x,0),(x,H))
        for y in range(0,H,40): pygame.draw.line(surf,(25,25,40),(0,y),(W,y))
        return surf

    def _show_msg(self, txt, frames=90):
        self.msg_text=txt; self.msg_frames=frames

    def _alive(self):
        return [p for p in self.players if p.alive]

    # ── Input ─────────────────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_r:      self.reset()
                    if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                else:
                    if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and not self.game_over:
                self._handle_click(pygame.mouse.get_pos())

    def _handle_click(self, pos):
        mx,my = pos
        if not self.human.has_ball or self.ball.flying:
            if not self.human.has_ball:
                self._show_msg("You don't have the ball!", 60)
            return
        for p in self._alive():
            if p is self.human: continue
            if dist2(mx,my,p.x,p.y) < PLAYER_R+12:
                self.ball.throw(self.human, p)
                self._show_msg(f"Thrown at {p.name}!", 40)
                return
        self._show_msg("Click an opponent to throw!", 50)

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        self.tick += 1; self.time_survived += 1

        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = int(keys[pygame.K_DOWN]  or keys[pygame.K_s]) - int(keys[pygame.K_UP]   or keys[pygame.K_w])
        self.human.move(dx, dy, self.hurdles, self._alive())

        self._update_bots()
        self._update_ball()
        self._tick_timer()

        if self.shake_frames > 0: self.shake_frames -= 1
        if self.msg_frames   > 0:
            self.msg_frames -= 1
            if self.msg_frames == 0: self.msg_text = ''

        self.score = (self.time_survived//60) * len(self.players)

    def _update_bots(self):
        ball  = self.ball
        alive = self._alive()
        for p in alive:
            if p.is_human: continue
            p.speed = self.bot_speed

            if p.has_ball:
                near,nd = None,float('inf')
                for o in alive:
                    if o is p: continue
                    d = dist2(p.x,p.y,o.x,o.y)
                    if d < nd: nd=d; near=o
                if near and nd < 230:
                    dx=p.x-near.x; dy=p.y-near.y
                else:
                    if random.random()<0.02:
                        p._wx=random.uniform(-1,1); p._wy=random.uniform(-1,1)
                    dx,dy=p._wx,p._wy
                p.move(dx,dy,self.hurdles,alive)

                p._throw_timer -= 1
                if p._throw_timer <= 0 and not ball.flying:
                    p._throw_timer = random.randint(max(1,self.bot_delay-5), self.bot_delay+8)
                    targets = [o for o in alive if o is not p]
                    if not targets: continue
                    target = (self.human
                              if self.human.alive and random.random() < self.human_prob
                              else random.choice(targets))
                    ball.throw(p, target)
            else:
                if ball.holder and ball.holder is not p and ball.holder.alive:
                    dx=ball.holder.x-p.x; dy=ball.holder.y-p.y
                else:
                    if random.random()<0.015:
                        p._wx=random.uniform(-1,1); p._wy=random.uniform(-1,1)
                    dx,dy=p._wx,p._wy
                p.move(dx,dy,self.hurdles,alive)

    def _update_ball(self):
        result = self.ball.update()
        if self.ball.flying:
            if hurdle_hit(self.hurdles, self.ball.x, self.ball.y, BALL_R):
                culprit = self.ball.target
                self.ball.flying=False; self.ball.holder=None
                self._eliminate(culprit,"hit by a ricocheted ball"); return

        if result == 'landed':
            tgt = self.ball.holder
            if tgt is self.human:
                self._show_msg("YOU have the ball — THROW IT!", 120)
            else:
                self._show_msg(f"{tgt.name} has the ball!", 50)
            if hurdle_hit(self.hurdles,tgt.x,tgt.y,PLAYER_R):
                self._eliminate(tgt,"caught ball inside a wall")

        if self.ball.holder and not self.ball.flying:
            h = self.ball.holder
            if hurdle_hit(self.hurdles,h.x,h.y,PLAYER_R):
                self._eliminate(h,"ran into a wall")

    def _tick_timer(self):
        now = pygame.time.get_ticks()
        if now - self.last_tick_ms >= self.tick_ms and not self.ball.flying:
            self.last_tick_ms = now
            if self.ball.holder:
                self.ball.time_left -= 1
                tl = self.ball.time_left
                if 0 < tl <= 3:
                    self._show_msg(f"  {tl}...  ",28); SND_WARN.play()
                elif tl == self.fuse_sec-2:
                    self._show_msg(f"{tl} seconds!",28)
                if tl <= 0:
                    self._eliminate(self.ball.holder,"ball exploded!")

    def _eliminate(self, player, reason=""):
        if not player.alive: return
        player.alive=False; player.has_ball=False
        SND_ELIM.play()
        self.shake_frames=30; self.shake_mag=8
        self.eliminated_order.append(player)
        who = "YOU were" if player.is_human else f"{player.name} was"
        self._show_msg(f"{who} eliminated — {reason}", 160)

        alive = self._alive()
        if len(alive)==1:
            self.last_survivor=alive[0]; self.game_over=True
            SND_EXPLODE.play(); return
        if len(alive)==0:
            self.game_over=True; return
        if (player.has_ball or self.ball.holder is player
                or (not self.ball.flying and not self.ball.holder)):
            self.ball.attach(random.choice(alive))

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        sx = random.randint(-self.shake_mag,self.shake_mag) if self.shake_frames else 0
        sy = random.randint(-self.shake_mag,self.shake_mag) if self.shake_frames else 0

        self.screen.blit(self.background,(sx,sy))

        tmp = pygame.Surface((W,H),pygame.SRCALPHA)
        for h in self.hurdles: h.draw(tmp)
        self.screen.blit(tmp,(sx,sy))

        for p in self.players:
            if not p.alive:
                self._draw_ghost(p,sx,sy)
            else:
                off = pygame.Surface((W,H),pygame.SRCALPHA)
                p.draw(off,self.ball.time_left,self.font_sm,self.font_xs,self.tick)
                self.screen.blit(off,(sx,sy))

        bs = pygame.Surface((W,H),pygame.SRCALPHA)
        self.ball.draw(bs,self.tick)
        self.screen.blit(bs,(sx,sy))

        self._draw_hud(sx,sy)
        if self.game_over: self._draw_game_over()
        pygame.display.flip()

    def _draw_ghost(self,p,sx,sy):
        s = pygame.Surface((PLAYER_R*2+4,)*2,pygame.SRCALPHA)
        pygame.draw.circle(s,(120,120,140,70),(PLAYER_R+2,PLAYER_R+2),PLAYER_R)
        self.screen.blit(s,(int(p.x)-PLAYER_R-2+sx, int(p.y)-PLAYER_R-2+sy))
        lbl = self.font_xs.render("x "+p.name,True,(90,90,110))
        self.screen.blit(lbl,(int(p.x)-lbl.get_width()//2+sx, int(p.y)-PLAYER_R-16+sy))

    def _draw_hud(self,sx,sy):
        pygame.draw.rect(self.screen,(0,0,0),(0,0,W,48))
        pygame.draw.line(self.screen,(55,55,75),(0,48),(W,48),1)

        tl   = self.ball.time_left
        tcol = RED if tl<=2 else ORANGE if tl<=4 else YELLOW
        pulse= int(abs(math.sin(self.tick*0.15))*6) if tl<=3 else 0
        pygame.draw.circle(self.screen,(30,20,0),(W//2+sx,24+sy),30+pulse)
        pygame.draw.circle(self.screen,tcol,     (W//2+sx,24+sy),30+pulse,2+pulse//2)
        ts = self.font_lg.render(str(tl) if self.ball.holder else "-",True,tcol)
        self.screen.blit(ts,(W//2-ts.get_width()//2+sx, 5+sy))

        ti = self.font_sm.render("FIREBALL",True,(200,60,20))
        self.screen.blit(ti,(W//2-ti.get_width()//2+sx,31+sy))

        ds = self.font_sm.render(self.diff_label,True,self.diff_color)
        self.screen.blit(ds,(10+sx,10+sy))
        al = self.font_sm.render(f"Alive: {len(self._alive())}/{len(self.players)}",True,(140,200,140))
        self.screen.blit(al,(10+sx,28+sy))

        sc = self.font_sm.render(f"Score {self.score}  |  {self.time_survived//60}s",True,LGRAY)
        self.screen.blit(sc,(W-sc.get_width()-10+sx,16+sy))

        if self.ball.holder and not self.game_over:
            who = "YOU" if self.ball.holder.is_human else self.ball.holder.name
            col = RED if self.ball.holder.is_human else ORANGE
            hs  = self.font_sm.render(f"  {who} holds the ball  ",True,col)
            hw  = hs.get_width()
            pygame.draw.rect(self.screen,BLACK,(W//2-hw//2-4+sx,50+sy,hw+8,20))
            self.screen.blit(hs,(W//2-hw//2+sx,52+sy))

        if self.msg_text:
            ms = self.font_md.render(self.msg_text,True,YELLOW)
            mw = ms.get_width(); my2=H-58
            pygame.draw.rect(self.screen,BLACK,(W//2-mw//2-8+sx,my2-4+sy,mw+16,34))
            pygame.draw.rect(self.screen,(80,70,0),(W//2-mw//2-8+sx,my2-4+sy,mw+16,34),1)
            self.screen.blit(ms,(W//2-mw//2+sx,my2+sy))

        ctrl = self.font_xs.render("WASD / Arrows: Move   |   Click opponent to throw",True,(65,65,85))
        self.screen.blit(ctrl,(W//2-ctrl.get_width()//2+sx,H-18+sy))

    def _draw_game_over(self):
        ov = pygame.Surface((W,H),pygame.SRCALPHA)
        ov.fill((0,0,0,210)); self.screen.blit(ov,(0,0))

        survived  = self.last_survivor
        human_won = survived and survived.is_human

        for _ in range(120):
            cc = random.choice([GREEN,YELLOW,CYAN,BLUE,ORANGE] if human_won else [RED,ORANGE,(180,0,0)])
            pygame.draw.circle(self.screen,cc,(random.randint(0,W),random.randint(0,H)),random.randint(2,8))

        t1,c1 = ("VICTORY!",GREEN) if human_won else (("ELIMINATED!",RED) if survived else ("DRAW!",YELLOW))
        t2,c2 = (("You are the last survivor!",CYAN) if human_won else
                 ((f"{survived.name} survived.",ORANGE) if survived else ("Everyone burned.",ORANGE)))

        def ctr(s,y):
            self.screen.blit(s,(W//2-s.get_width()//2,y))

        s1 = self.font_lg.render(t1,True,c1)
        s2 = self.font_md.render(t2,True,c2)
        s3 = self.font_md.render(f"Score: {self.score}  |  {self.time_survived//60}s  |  {self.diff_label}",True,WHITE)
        s4 = self.font_sm.render("R — restart      ESC — quit",True,LGRAY)

        for s,y in [(s1,H//2-90),(s2,H//2-30),(s3,H//2+20),(s4,H//2+75)]:
            pygame.draw.rect(self.screen,BLACK,(W//2-s.get_width()//2-12,y-6,s.get_width()+24,s.get_height()+12))
            ctr(s,y)

        if self.eliminated_order:
            eo = self.font_xs.render("Eliminated: "+" → ".join(p.name for p in self.eliminated_order),True,(110,110,120))
            ctr(eo,H//2+115)

    def run(self):
        while True:
            self.handle_events()
            if not self.game_over: self.update()
            self.draw()
            self.clock.tick(FPS)


# ─── Start Screen ─────────────────────────────────────────────────────────────
def draw_button(screen, font, label, rect, active=False, hover=False, active_color=None):
    fill = (70,30,0)  if active else ((55,55,70) if hover else (35,35,45))
    bord = active_color if (active and active_color) else ((220,120,20) if active else ((120,120,140) if hover else (80,80,100)))
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, bord, rect, 2, border_radius=8)
    s = font.render(label, True, active_color if (active and active_color) else (WHITE if active else LGRAY))
    screen.blit(s,(rect.centerx-s.get_width()//2, rect.centery-s.get_height()//2))


def start_screen():
    screen  = pygame.display.set_mode((W, H))
    pygame.display.set_caption("FIREBALL")
    clock   = pygame.time.Clock()
    f_xl    = pygame.font.Font(None, 96)
    f_lg    = pygame.font.Font(None, 54)
    f_md    = pygame.font.Font(None, 38)
    f_sm    = pygame.font.Font(None, 28)
    f_xs    = pygame.font.Font(None, 22)

    n_opp   = 3
    MIN_OPP = 1
    MAX_OPP = min(11, len(BOT_NAMES))
    d_idx   = 0   # 0=EASY,1=MEDIUM,2=HARD

    # Static background
    bg = pygame.Surface((W,H))
    for y in range(H):
        v = int(8+(y/H)*25)
        pygame.draw.line(bg,(v,v,v+12),(0,y),(W,y))
    for x in range(0,W,40): pygame.draw.line(bg,(18,18,30),(x,0),(x,H))
    for y in range(0,H,40): pygame.draw.line(bg,(18,18,30),(0,y),(W,y))

    tick = 0
    # Placeholder rects (real ones built each frame)
    r_minus = pygame.Rect(0,0,1,1)
    r_plus  = pygame.Rect(0,0,1,1)
    diff_rects = [pygame.Rect(0,0,1,1)]*3
    r_play  = pygame.Rect(0,0,1,1)

    while True:
        tick += 1
        mx,my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_LEFT:  n_opp = max(MIN_OPP, n_opp-1)
                if event.key == pygame.K_RIGHT: n_opp = min(MAX_OPP, n_opp+1)
                if event.key == pygame.K_UP:    d_idx = max(0, d_idx-1)
                if event.key == pygame.K_DOWN:  d_idx = min(2, d_idx+1)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return n_opp, DIFF_ORDER[d_idx]
            if event.type == pygame.MOUSEBUTTONDOWN:
                if r_minus.collidepoint(mx,my):  n_opp = max(MIN_OPP, n_opp-1)
                if r_plus.collidepoint(mx,my):   n_opp = min(MAX_OPP, n_opp+1)
                for i,r in enumerate(diff_rects):
                    if r.collidepoint(mx,my): d_idx = i
                if r_play.collidepoint(mx,my):
                    return n_opp, DIFF_ORDER[d_idx]

        # ── Draw ──────────────────────────────────────────────────────────
        screen.blit(bg,(0,0))

        # Title
        pulse = int(abs(math.sin(tick*0.04))*10)
        t = f_xl.render("FIREBALL", True,(220+pulse,50,10))
        screen.blit(t,(W//2-t.get_width()//2, 55))
        sub = f_xs.render("Pass the ball before it explodes — last one standing wins!", True,(145,145,168))
        screen.blit(sub,(W//2-sub.get_width()//2, 158))

        # ── Opponent count ─────────────────────────────────────────────────
        opp_y = 220
        ql = f_sm.render("Number of opponents", True,(200,200,215))
        screen.blit(ql,(W//2-ql.get_width()//2, opp_y))

        # Big clickable MINUS button
        r_minus = pygame.Rect(W//2-130, opp_y+40, 70, 50)
        hover_m = r_minus.collidepoint(mx,my)
        draw_button(screen, f_lg, "  -  ", r_minus,
                    active=False, hover=hover_m,
                    active_color=None)

        # Number in middle
        num_s = f_lg.render(str(n_opp), True, YELLOW)
        screen.blit(num_s,(W//2-num_s.get_width()//2, opp_y+45))

        # Big clickable PLUS button
        r_plus = pygame.Rect(W//2+60, opp_y+40, 70, 50)
        hover_p = r_plus.collidepoint(mx,my)
        draw_button(screen, f_lg, "  +  ", r_plus,
                    active=False, hover=hover_p,
                    active_color=None)

        hint_o = f_xs.render("← → arrow keys also work", True,(75,75,95))
        screen.blit(hint_o,(W//2-hint_o.get_width()//2, opp_y+100))

        # ── Difficulty ─────────────────────────────────────────────────────
        diff_y = 360
        dl = f_sm.render("Difficulty", True,(200,200,215))
        screen.blit(dl,(W//2-dl.get_width()//2, diff_y))

        btn_labels = [("EASY",GREEN),("MEDIUM",YELLOW),("HARD",RED)]
        btn_w, btn_h = 165, 52
        gap   = 18
        total = 3*btn_w+2*gap
        sx0   = W//2 - total//2
        diff_rects = []
        for i,(lbl,col) in enumerate(btn_labels):
            r = pygame.Rect(sx0+i*(btn_w+gap), diff_y+38, btn_w, btn_h)
            active = (i==d_idx)
            hover  = r.collidepoint(mx,my)
            draw_button(screen, f_sm, lbl, r, active=active, hover=hover, active_color=col)
            diff_rects.append(r)

        descs = [
            "Slow bots  •  9-second fuse",
            "Faster bots  •  7-second fuse",
            "Aggressive bots  •  5-second fuse",
        ]
        desc_s = f_xs.render(descs[d_idx], True, btn_labels[d_idx][1])
        screen.blit(desc_s,(W//2-desc_s.get_width()//2, diff_y+100))

        hint_d = f_xs.render("↑ ↓ arrow keys also work", True,(75,75,95))
        screen.blit(hint_d,(W//2-hint_d.get_width()//2, diff_y+120))

        # ── Play button ────────────────────────────────────────────────────
        r_play = pygame.Rect(W//2-120, 510, 240, 56)
        hover_play = r_play.collidepoint(mx,my)
        pygame.draw.rect(screen,(90,30,0) if hover_play else (60,18,0), r_play, border_radius=10)
        pygame.draw.rect(screen,(230,80,20) if hover_play else (160,50,10), r_play, 2, border_radius=10)
        ps = f_md.render("  PLAY  ", True, WHITE)
        screen.blit(ps,(r_play.centerx-ps.get_width()//2, r_play.centery-ps.get_height()//2))

        pe = f_xs.render("ENTER or SPACE to start", True,(70,70,90))
        screen.blit(pe,(W//2-pe.get_width()//2, 574))

        # ── Controls hint ──────────────────────────────────────────────────
        hints = [
            "In game:  WASD / Arrow Keys — Move",
            "In game:  Click an opponent — Throw the fireball",
        ]
        for i,line in enumerate(hints):
            hs2 = f_xs.render(line,True,(65,65,85))
            screen.blit(hs2,(W//2-hs2.get_width()//2, H-58+i*22))

        pygame.display.flip()
        clock.tick(60)


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    n, diff = start_screen()
    game = Game(n, diff)
    game.run()