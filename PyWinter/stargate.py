import pygame
import math
import random
import os

BASE_PATH = os.path.dirname(__file__) # Cartella dove si trova lo script .py
SOUND_DIR = os.path.join(BASE_PATH, "sounds")

# --- Inizializzazione ---
pygame.mixer.pre_init(44100, -16, 2, 512) # Pre-inizializzazione per ridurre il lag audio
pygame.init()
WIDTH, HEIGHT = 800, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SGC - Dialing Sequence with Audio")
clock = pygame.time.Clock()

# --- Caricamento Suoni ---
# Assicurati di avere un file 'woosh.wav' nella stessa cartella dello script
try:
    woosh_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "woosh.wav"))
    lock_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "lock.wav"))
    has_sound = True
except FileNotFoundError:
    print(f"Errore: Assicurati che la cartella '{SOUND_DIR}' contenga i file .wav")
    has_sound = False
except Exception as e:
    print(f"Errore imprevisto durante il caricamento audio: {e}")
    has_sound = False

# --- Costanti e Colori ---
BLACK = (5, 5, 10)
GATE_GREY = (80, 80, 90)
GLOW_BLUE = (100, 220, 255)
CHEVRON_OFF = (60, 10, 10)
CHEVRON_ON = (255, 50, 0)
NUM_SYMBOLS = 33
TARGET_CHEVRONS = 7

# --- Stato del Sistema ---
current_angle = 0.0
target_angle = 0.0
locked_chevrons = 0
is_dialing = True
waiting_timer = 0
event_horizon_active = False
played_woosh = False # Per evitare che il suono parta a ripetizione

# Generazione sequenza
dialing_sequence = [random.randint(0, NUM_SYMBOLS - 1) for _ in range(TARGET_CHEVRONS)]

def get_angle_for_symbol(index):
    return -(index * (2 * math.pi / NUM_SYMBOLS)) - (math.pi / 2)

target_angle = get_angle_for_symbol(dialing_sequence[0])

def draw_gate(angle, locked_count, horizon):
    # 1. Orizzonte degli eventi (Ka-woosh!)
    if horizon:
        for r in range(250, 0, -12):
            # Colore cangiante per l'effetto vortice
            c = random.randint(150, 255)
            pygame.draw.circle(screen, (0, c//2, c), (400, 400), r)

    # 2. Anello esterno e Chevron
    pygame.draw.circle(screen, GATE_GREY, (400, 400), 320, 15)
    for i in range(9):
        ch_angle = math.radians(i * (360 / 9) - 90)
        cx = 400 + math.cos(ch_angle) * 325
        cy = 400 + math.sin(ch_angle) * 325
        is_active = i < locked_count or (i == 0 and locked_count > 0)
        color = CHEVRON_ON if is_active else CHEVRON_OFF
        pygame.draw.circle(screen, color, (int(cx), int(cy)), 15)

    # 3. Anello interno e Simboli
    for i in range(NUM_SYMBOLS):
        sym_angle = angle + (i * (2 * math.pi / NUM_SYMBOLS))
        sx = 400 + math.cos(sym_angle) * 260
        sy = 400 + math.sin(sym_angle) * 260
        
        dist_to_top = abs((sym_angle % (2*math.pi)) - (3*math.pi/2))
        color = GLOW_BLUE if dist_to_top < 0.1 else (100, 100, 110)
        pygame.draw.circle(screen, color, (int(sx), int(sy)), 6)

def main():
    global current_angle, target_angle, locked_chevrons, is_dialing, waiting_timer, event_horizon_active, played_woosh
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(BLACK)

        if is_dialing:
            diff = target_angle - current_angle
            if abs(diff) > 0.005:
                current_angle += diff * 0.04 # Rotazione fluida
            else:
                if waiting_timer == 0:
                    waiting_timer = 45 # Pausa tra un simbolo e l'altro
                    if has_sound: lock_sound.play() # Suono 'clack' al blocco
                
                waiting_timer -= 1
                if waiting_timer <= 0:
                    locked_chevrons += 1
                    if locked_chevrons < TARGET_CHEVRONS:
                        target_angle = get_angle_for_symbol(dialing_sequence[locked_chevrons])
                    else:
                        is_dialing = False
                        event_horizon_active = True
                        if has_sound and not played_woosh:
                            woosh_sound.play()
                            played_woosh = True
        
        draw_gate(current_angle, locked_chevrons, event_horizon_active)
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()