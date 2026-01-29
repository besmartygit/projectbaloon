
import pygame
import random
import sys
import os
from pathlib import Path

pygame.init()

# --- Robust audio init (tries real device, falls back to silent mode if needed) ---
SOUND_ENABLED = True
def _init_mixer_real_device():
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.init()

try:
    _init_mixer_real_device()
    print("[AUDIO] Using real audio device. Driver:", pygame.mixer.get_init())
except Exception as e:
    print(f"[AUDIO] Real device init failed: {e}")
    print("[AUDIO] Falling back to dummy (no sound) so the game can still run.")
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    try:
        pygame.mixer.quit()
    except Exception:
        pass
    try:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        SOUND_ENABLED = False  # running, but silent
    except Exception as e2:
        print(f"[AUDIO] Dummy init also failed: {e2}")
        SOUND_ENABLED = False

# --- Screen setup ---
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ORION Toddler Balloon Game")

# --- Resource path helper (works in dev and with PyInstaller) ---
def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    except Exception:
        base_path = Path(os.path.abspath("."))
    p = (base_path / relative_path).resolve()
    return str(p)

# Diagnostics
try:
    print("[INFO] CWD:", os.getcwd())
    print("[INFO] __file__ dir:", os.path.dirname(os.path.abspath(__file__)))
except Exception:
    print("[INFO] __file__ not available (interactive/frozen context).")
print("[INFO] Looking for assets under:", resource_path("."))

# --- Load balloon images (robust, with graceful fallback) ---
def load_balloon_images():
    """
    Try to load balloon1..balloon5 from (.) or ./images with common extensions.
    If none found, generate simple drawn balloons so the game still runs.
    """
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
                    # Constrain large images a bit
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
            print(f"[WARN] Could not find balloon{i}.* next to script or in ./images/")
    if images:
        return images

    # ---- Fallback: generate simple balloon surfaces (no files needed) ----
    print("[WARN] No balloon images found. Using fallback drawn balloons.")
    colors = [(255, 0, 0), (0, 160, 255), (0, 180, 0), (255, 150, 0), (200, 0, 200)]
    images = []
    for c in colors:
        w, h = 90, 120
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # balloon body
        pygame.draw.ellipse(surf, c, (0, 0, w, h - 20))
        # string
        pygame.draw.line(surf, (80, 80, 80), (w // 2, h - 20), (w // 2, h), 2)
        # small triangular knot
        pygame.draw.polygon(surf, c, [(w // 2 - 6, h - 26), (w // 2 + 6, h - 26), (w // 2, h - 18)])
        images.append(surf)
    return images

BALLOON_IMAGES = load_balloon_images()

# --- Colors & Fonts ---
WHITE = (255, 255, 255)
YELLOW = (255, 223, 0)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 170, 0)

font = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 40)
big_font = pygame.font.Font(None, 96)

# --- Language flag buttons (positions & rects only) ---
flags = {
    "Macedonian": pygame.Rect(150, 200, 100, 60),  # uses images/mk.png
    "English":    pygame.Rect(350, 200, 100, 60),  # uses images/uk.jpg
    "French":     pygame.Rect(550, 200, 100, 60),  # uses images/fr.png
}

# --- Load flag images and scale to button rects (fallback to letter if missing) ---
FLAG_IMAGE_FILES = {
    "Macedonian": "images/mk.png",
    "English":    "images/uk.png",
    "French":     "images/fr.png",
}

def _scale_surface_to_fit(surf, target_rect):
    """Scale surf to fit inside target_rect preserving aspect ratio."""
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

selected_language = None
start_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2, 200, 80)
# restart_button is now dynamic based on text; no fixed rect here

game_started = False
game_over = False
applause_played = False

# --- Balloons ---
balloons = []
balloon_speed = 2
popped_count = 0
MAX_COUNT = 10

# --- Sound system ---
def speak_number(n, lang):
    if not SOUND_ENABLED:
        return
    langs = {"Macedonian": "mk", "English": "en", "French": "fr"}
    code = langs.get(lang, "fr")
    filename = f"sounds/{code}_{n}.wav"
    filepath = resource_path(filename)

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
    applause_path = resource_path("sounds/applause.wav")
    if os.path.exists(applause_path):
        try:
            applause = pygame.mixer.Sound(applause_path)
            applause.play()
        except Exception as e:
            print(f"[ERR] Error playing applause: {e}")
    else:
        print("[WARN] Missing applause.wav in sounds/")

# --- Helpers for game logic ---
def create_balloon():
    surf = random.choice(BALLOON_IMAGES)
    rect = surf.get_rect()
    rect.centerx = random.randint(rect.width // 2, WIDTH - rect.width // 2)
    rect.centery = HEIGHT + rect.height // 2
    drift = random.choice([-1, 0, 1])  # slight horizontal drift
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

# --- UI helpers ---
def draw_flag_button(surface, rect, lang):
    """Draw flag image if available; otherwise draw a colored rect with first letter."""
    img = FLAG_SURFACES.get(lang)
    if img:
        img_rect = img.get_rect(center=rect.center)
        surface.blit(img, img_rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, width=2, border_radius=12)
    else:
        pygame.draw.rect(surface, (255, 0, 0), rect, border_radius=12)
        text = font.render(lang[0], True, (255, 255, 255))
        surface.blit(text, (rect.centerx - text.get_width() // 2,
                            rect.centery - text.get_height() // 2))

def make_button_rect_for_text(text_surface, centerx, centery, pad_x=28, pad_y=18):
    """Create a rect that hugs the text with padding; good for pill-shaped buttons."""
    w = text_surface.get_width() + pad_x * 2
    h = text_surface.get_height() + pad_y * 2
    return pygame.Rect(centerx - w // 2, centery - h // 2, w, h)

# --- Main loop ---
clock = pygame.time.Clock()
running = True

while running:
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            if game_over:
                # Dynamic "RECOMMENCER" button rect so clicks match visuals
                restart_text = font.render("RECOMMENCER", True, BLACK)
                restart_button = make_button_rect_for_text(
                    restart_text, WIDTH // 2, HEIGHT // 2 + 80
                )
                if restart_button.collidepoint(mx, my):
                    start_game()
                # allow changing language after game over
                for lang, rect in flags.items():
                    if rect.collidepoint(mx, my):
                        selected_language = lang
                        start_game()

            elif not selected_language:
                for lang, rect in flags.items():
                    if rect.collidepoint(mx, my):
                        selected_language = lang
                        print(f"[INFO] Selected language: {selected_language}")

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

    # Draw flags
    if not selected_language:
        for lang, rect in flags.items():
            draw_flag_button(screen, rect, lang)
    else:
        # Move flags to top
        x_positions = [WIDTH // 2 - 200, WIDTH // 2, WIDTH // 2 + 200]
        for i, (lang, rect) in enumerate(flags.items()):
            rect.x, rect.y = x_positions[i] - rect.width // 2, 20
            draw_flag_button(screen, rect, lang)

        if not game_started and not game_over:
            pygame.draw.rect(screen, YELLOW, start_button, border_radius=16)
            start_text = font.render("START", True, BLACK)
            screen.blit(
                start_text,
                (
                    start_button.centerx - start_text.get_width() // 2,
                    start_button.centery - start_text.get_height() // 2,
                ),
            )

    # Game loop
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

        info = small_font.render("Tu as tout compté jusqu’à 10 !", True, BLACK)
        screen.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT // 2 - 80))

        # Build text + rect sized perfectly around it
        restart_text = font.render("RECOMMENCER", True, BLACK)
        restart_button = make_button_rect_for_text(
            restart_text, WIDTH // 2, HEIGHT // 2 + 80
        )
        radius = max(12, restart_button.height // 2)  # pill shape
        pygame.draw.rect(screen, YELLOW, restart_button, border_radius=radius)

        # Center the text inside the button
        screen.blit(
            restart_text,
            (
                restart_button.centerx - restart_text.get_width() // 2,
                restart_button.centery - restart_text.get_height() // 2,
            ),
        )

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

