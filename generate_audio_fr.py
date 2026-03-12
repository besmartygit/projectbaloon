import asyncio
import os
import re
import unicodedata
import edge_tts

# ----------------------------
# Settings
# ----------------------------
OUT_DIR = "audio_fr"
VOICE = "fr-FR-DeniseNeural"   # natural female voice
# Try also: "fr-FR-HenriNeural" (male), "fr-FR-EloiseNeural" (if available)

PHRASES = {
    "mirror_question": "Miroir, miroir, dis-moi qui écrit le mieux au monde ?",
    "moi": "Moi",
    "toi_no_name": "Toi, tu écris le mieux au monde !",
    "au_revoir_enfant": "Au revoir, cher enfant. Toi, tu écris le mieux au monde !",
    # optional extra variants
    "bravo": "Bravo !",
    "encore": "Encore !",
}

# 30+ easy toddler-friendly French words (3–6 letters)
WORDS = [
    # 3 letters
    "toi"
]

# Keep only 3..6 letters
WORDS = [w for w in WORDS if 3 <= len(w) <= 6]

# ----------------------------
# Helpers
# ----------------------------
def slugify(text: str) -> str:
    """Safe filename: remove accents, keep alphanum + underscore."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "audio"

async def tts_to_mp3(text: str, out_path: str, voice: str = VOICE):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(out_path)

async def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Generate phrases
    for key, phrase in PHRASES.items():
        filename = f"phrase_{key}.mp3"
        out_path = os.path.join(OUT_DIR, filename)
        print("Generating:", out_path, "->", phrase)
        await tts_to_mp3(phrase, out_path)

    # Generate words
    words_dir = os.path.join(OUT_DIR, "words")
    os.makedirs(words_dir, exist_ok=True)

    # De-duplicate while keeping order
    seen = set()
    words_unique = []
    for w in WORDS:
        if w not in seen:
            seen.add(w)
            words_unique.append(w)

    for w in words_unique:
        filename = f"word_{len(w)}_{slugify(w)}.mp3"
        out_path = os.path.join(words_dir, filename)
        print("Generating:", out_path, "->", w)
        await tts_to_mp3(w, out_path)

    print("\nDone!")
    print(f"Audio saved to: {OUT_DIR}/")
    print(f"Phrases: {len(PHRASES)} files")
    print(f"Words:   {len(words_unique)} files in {OUT_DIR}/words/")

if __name__ == "__main__":
    asyncio.run(main())
