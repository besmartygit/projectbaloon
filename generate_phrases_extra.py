import asyncio
import os
import edge_tts

# -------- settings --------
OUT_DIR = "sounds"
VOICE = "fr-FR-DeniseNeural"   # try: fr-FR-HenriNeural (male)

PHRASES = {
    "phrase_toi.mp3": "Toi,",
    "phrase_tu_ecris.mp3": "tu écris le mieux au monde !",
    "phrase_au_revoir_cher.mp3": "Au revoir, cher",
    "phrase_point_toi.mp3": ". Toi, tu écris le mieux au monde !",

    # "enfant" (useful as a building block)
    "phrase_enfant.mp3": "enfant",
    # Optional full sentence version (if you want it too)
    "phrase_au_revoir_cher_enfant.mp3": "Au revoir, cher enfant. Toi, tu écris le mieux au monde !",
}

async def tts_to_mp3(text: str, out_path: str, voice: str = VOICE):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(out_path)

async def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for filename, text in PHRASES.items():
        out_path = os.path.join(OUT_DIR, filename)
        print(f"Generating: {out_path}  ->  {text}")
        await tts_to_mp3(text, out_path)

    print("\nDone! Files created in:", OUT_DIR)

if __name__ == "__main__":
    asyncio.run(main())
