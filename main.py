import pygame
import random
import sys
import os
import asyncio
from pathlib import Path

pygame.init()

# Detect web (pygbag) vs desktop
IS_WEB = (sys.platform == "emscripten")

# --- Screen setup ---
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ORION Toddler Balloon Game")

# --- Colors & Fonts ---
WHITE = (255, 255, 255)
YELLOW = (255, 223, 0)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 170, 0)

font = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 40)
big_font = pygame.font.Font(None, 96)

# --- Web-friendly resource path ---
def resource_path(relative_path: str) -> str:
    if sys.platform == "emscripten":
        # On web, serve from current working dir; keep paths relative.
        return relative_path.lstrip("/\\")
    try:
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    except Exception:
        base_path = Path(os.path.abspath("."))
    return str((base_path / relative_path).resolve())

# Diagnostics
try:
    print("[INFO] CWD:", os.getcwd())
    print("[INFO] __file__ dir:", os.path.dirname(os.path.abspath(__file__)))
except Exception:
    print("[INFO] __file__ not available (interactive/frozen/web).")
print("[INFO] Assets under:", resource_path("."))

# --- Error overlay (shows exceptions on canvas) ---
_last_error = None
def _draw_error_overlay(surface, msg):
    if not msg:
        return
    import textwrap
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    font_err = pygame.font.Font(None, 28)
    y = 32
    for line in textwrap.wrap(msg, width=70):
        txt = font_err.render(line, True, (255, 100, 100))
        surface.blit(txt, (24, y))
        y += txt.get_height() + 4

# --- Audio init ---
SOUND_ENABLED = True
def init_audio():
    global SOUND_ENABLED
    if IS_WEB:
        try:
            pygame.mixer.init()  # keep it simple on web
            print("[AUDIO][web] OK")
        except Exception as e:
            print("[AUDIO][web] init failed:", e)
            SOUND_ENABLED = False
    else:
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            print("[AUDIO][desktop] OK:", pygame.mixer.get_init())
        except Exception as e:
            print("[AUDIO][desktop] init failed:", e)
            SOUND_ENABLED = False

init_audio()

# --- Balloon images loading (with fallback) ---
def load_balloon_images():
    candidates = []
    for i in range(1, 6):
        bases = [f"balloon{i}", os.path.join("images", f"balloon{i}")]
        exts = [".png", ".PNG", ".jpg", ".jpeg", ".JPG", ".JPEG"]
        paths = [resource_path(b + e) for b in bases for e in exts]
        candidates.append(paths)

    images = []
    for i, paths in enumerate(candidates, start=1):
        loaded = False
        for p in paths:
            if os.path.exists(p):
                try:
                    img = pygame.image.load(p).convert_alpha()
                    max_w, max_h = 140, 180
                    iw, ih = img.get_width(), img.get_height()
                    if iw > max_w or ih > max_h:
                        scale = min(max_w / iw, max_h / ih)
                        img = pygame.transform.smoothscale(img, (int(iw * scale), int(ih * scale)))
                    images.append(img)
                    print(f"[OK] Loaded balloon{i}: {p}")
                    loaded = True
                    break
                except Exception as e:
                    print(f"[ERR] Error loading {p}: {e}")
        if not loaded:
            print(f"[WARN] Missing balloon{i}.* in ./ or ./images/")
    if images:
        return images

    # Fallback drawn balloons
    print("[WARN] No balloon images found. Using fallback drawn balloons.")
    colors = [(255, 0, 0), (0, 160, 255), (0, 180, 0), (255, 150, 0), (200, 0, 200)]
    images = []
    for c in colors:
        w, h = 90, 120
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, c, (0, 0, w, h - 20))
        pygame.draw.line(surf, (80, 80, 80), (w // 2, h - 20), (w // 2, h), 2)
        pygame.draw.polygon(surf, c, [(w // 2 - 6, h - 26), (w // 2 + 6, h - 26), (w // 2, h - 18)])
        images.append(surf)
    return images

BALLOON_IMAGES = load_balloon_images()

# --- Language buttons (use images if present) ---
flags = {
    "Macedonian": pygame.Rect(150, 200, 100, 60),  # images/mk.png
    "English":    pygame.Rect(350, 200, 100, 60),  # images/uk.jpg
    "French":     pygame.Rect(550, 200, 100, 60),  # images/fr.png
}
FLAG_IMAGE_FILES = {
    "Macedonian": "images/mk.png",
    "English":    "images/uk.png",
    "French":     "images/fr.png",
}

def _scale_surface_to_fit(surf, target_rect):
    tw, th = target_rect.width, target_rect.height
    sw, sh = surf.get_width(), surf.get_height()
    scale = min(tw / sw, th / sh)
    new_size = (max(1, int(sw * scale)), max(1, int(sh * scale)))
    return pygame.transform.smoothscale(surf, new_size)

def load_flag_surfaces(flag_rects):
    loaded = {}
    for lang, rect in flag_rects.items():
        path = resource_path(FLAG_IMAGE_FILES[lang])
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = _scale_surface_to_fit(img, rect)
                loaded[lang] = img
                print(f"[OK] Loaded flag for {lang}: {path}")
            except Exception as e:
                print(f"[ERR] Failed to load flag {lang} from {path}: {e}")
                loaded[lang] = None
        else:
            print(f"[WARN] Flag image missing for {lang}: {path}")
            loaded[lang] = None
    return loaded

FLAG_SURFACES = load_flag_surfaces(flags)

# --- Buttons ---
selected_language = None
start_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2, 200, 80)

def make_button_rect_for_text(text_surface, centerx, centery, pad_x=28, pad_y=18):
    w = text_surface.get_width() + pad_x * 2
    h = text_surface.get_height() + pad_y * 2
    return pygame.Rect(centerx - w // 2, centery - h // 2, w, h)

# --- Game state ---
game_started = False
game_over = False
applause_played = False
balloons = []
balloon_speed = 2
popped_count = 0
MAX_COUNT = 10
running = True
_spinner_x = 0  # tiny spinner so you can see loop is alive

# --- Sounds (use .ogg on web, .wav on desktop) ---
def number_sound_path(code, n):
    ext = "ogg" if IS_WEB else "wav"
    return resource_path(f"sounds/{code}_{n}.{ext}")

def applause_sound_path():
    ext = "ogg" if IS_WEB else "wav"
    return resource_path(f"sounds/applause.{ext}")

def speak_number(n, lang):
    if not SOUND_ENABLED:
        return
    langs = {"Macedonian": "mk", "English": "en", "French": "fr"}
    code = langs.get(lang, "fr")
    filepath = number_sound_path(code, n)
    if os.path.exists(filepath):
        try:
            snd = pygame.mixer.Sound(filepath)
            snd.play()
        except Exception as e:
            print(f"[ERR] Error playing {filepath}: {e}")
    else:
        print(f"[WARN] Missing sound file: {filepath}")

def play_applause():
    if not SOUND_ENABLED:
        return
    ap = applause_sound_path()
    if os.path.exists(ap):
        try:
            pygame.mixer.Sound(ap).play()
        except Exception as e:
            print(f"[ERR] Error playing applause: {e}")
    else:
        print("[WARN] Missing applause sound")

# --- Helpers ---
def create_balloon():
    surf = random.choice(BALLOON_IMAGES)
    rect = surf.get_rect()
    rect.centerx = random.randint(rect.width // 2, WIDTH - rect.width // 2)
    rect.centery = HEIGHT + rect.height // 2
    drift = random.choice([-1, 0, 1])
    return {"surf": surf, "rect": rect, "dx": drift}

def is_balloon_touched(balloon, touch_x, touch_y):
    return balloon["rect"].collidepoint(touch_x, touch_y)

def start_game():
    global game_started, game_over, applause_played, balloons, popped_count
    game_started = True
    game_over = False
    applause_played = False
    balloons = [create_balloon()]
    popped_count = 0
    print("[INFO] Game started.")

def finish_game():
    global game_started, game_over, applause_played
    game_over = True
    game_started = False
    print("[INFO] Game over. Reached max count.")
    if not applause_played:
        play_applause()
        applause_played = True

def draw_flag_button(surface, rect, lang):
    img = FLAG_SURFACES.get(lang)
    if img:
        img_rect = img.get_rect(center=rect.center)
        surface.blit(img, img_rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, width=2, border_radius=12)
    else:
        pygame.draw.rect(surface, RED, rect, border_radius=12)
        letter = "M" if lang == "Macedonian" else ("E" if lang == "English" else "F")
        text = font.render(letter, True, (255, 255, 255))
        surface.blit(text, (rect.centerx - text.get_width() // 2,
                            rect.centery - text.get_height() // 2))

# --- Async main loop (desktop + web) ---
async def main():
    global running, game_started, game_over, selected_language, popped_count, balloons, _spinner_x, _last_error

    clock = pygame.time.Clock()

    while running:
        try:
            # EVENTS
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # Optional quick quit on Esc (desktop)
                if event.type == pygame.KEYDOWN and not IS_WEB:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos

                    if game_over:
                        restart_text = font.render("START", True, BLACK)
                        restart_button = make_button_rect_for_text(restart_text, WIDTH // 2, HEIGHT // 2 + 80)
                        if restart_button.collidepoint(mx, my):
                            start_game()
                        for lang, rect in flags.items():
                            if rect.collidepoint(mx, my):
                                selected_language = lang
                                start_game()

                    elif not selected_language:
                        for lang, rect in flags.items():
                            if rect.collidepoint(mx, my):
                                selected_language = lang
                                print("[INFO] Selected language:", selected_language)

                    elif not game_started:
                        if start_button.collidepoint(mx, my):
                            start_game()

                    else:
                        for b in balloons[:]:
                            if is_balloon_touched(b, mx, my):
                                balloons.remove(b)
                                popped_count += 1
                                if popped_count <= MAX_COUNT and selected_language:
                                    speak_number(popped_count, selected_language)
                                if popped_count >= MAX_COUNT:
                                    finish_game()

            # UPDATE + DRAW
            screen.fill(WHITE)

            if not selected_language:
                # Tiny spinner so you can see the loop is alive
                pygame.draw.rect(screen, (120,120,120), (10 + (_spinner_x % 120), 10, 30, 8))
                _spinner_x += 2

                for lang, rect in flags.items():
                    draw_flag_button(screen, rect, lang)
            else:
                # Move flags to top row
                x_positions = [WIDTH // 2 - 200, WIDTH // 2, WIDTH // 2 + 200]
                for i, (lang, rect) in enumerate(flags.items()):
                    rect.x, rect.y = x_positions[i] - rect.width // 2, 20
                    draw_flag_button(screen, rect, lang)

                if not game_started and not game_over:
                    pygame.draw.rect(screen, YELLOW, start_button, border_radius=16)
                    start_text = font.render("START", True, BLACK)
                    screen.blit(start_text, (start_button.centerx - start_text.get_width() // 2,
                                             start_button.centery - start_text.get_height() // 2))

            # Game loop when running
            if game_started and not game_over:
                if random.randint(1, 45) == 1:
                    balloons.append(create_balloon())
                for b in balloons[:]:
                    b["rect"].y -= balloon_speed
                    b["rect"].x += b["dx"]
                    if b["rect"].left < 0 or b["rect"].right > WIDTH:
                        b["dx"] *= -1
                    screen.blit(b["surf"], b["rect"])
                    if b["rect"].bottom < 0:
                        balloons.remove(b)

                count_label = small_font.render(f"{popped_count}/{MAX_COUNT}", True, BLACK)
                screen.blit(count_label, (WIDTH - 140, 20))

            # Game over screen
            if game_over:
                bravo = big_font.render("BRAVO !", True, GREEN)
                screen.blit(bravo, (WIDTH // 2 - bravo.get_width() // 2, HEIGHT // 2 - 140))

                info = small_font.render("You counted until 10 !", True, BLACK)
                screen.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT // 2 - 80))

                restart_text = font.render("START", True, BLACK)
                restart_button = make_button_rect_for_text(restart_text, WIDTH // 2, HEIGHT // 2 + 80)
                radius = max(12, restart_button.height // 2)
                pygame.draw.rect(screen, YELLOW, restart_button, border_radius=radius)
                screen.blit(restart_text, (restart_button.centerx - restart_text.get_width() // 2,
                                           restart_button.centery - restart_text.get_height() // 2))

            # Flip
            pygame.display.flip()

            # Clear last error if frame succeeded
            _last_error = None

        except Exception as e:
            # Show error on screen instead of going black
            import traceback
            _last_error = traceback.format_exc()
            screen.fill((0,0,0))
            _draw_error_overlay(screen, _last_error)
            pygame.display.flip()

        # Yield on web, tick on desktop
        if IS_WEB:
            await asyncio.sleep(0)
        else:
            clock.tick(60)

# --- Entry point ---
if __name__ == "__main__":
    if IS_WEB:
        asyncio.run(main())
        pygame.quit()
        # no sys.exit() on web
    else:
        asyncio.run(main())
        pygame.quit()
        sys.exit()
