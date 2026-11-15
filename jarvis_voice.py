"""
JARVIS — ovozli rejim
Mikrofondan eshitadi, ovoz bilan javob beradi.

Kerakli kutubxonalar:
    pip install SpeechRecognition PyAudio edge-tts

Ishga tushirish:  python jarvis_voice.py
Chiqish:          "chiqish" deb ayting yoki Ctrl+C
"""

import asyncio
import subprocess
import tempfile
from pathlib import Path

import anyio
import edge_tts
import speech_recognition as sr
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

from jarvis_core import Jarvis

# uz-UZ-SardorNeural (erkak)  |  uz-UZ-MadinaNeural (ayol)
VOICE = "uz-UZ-SardorNeural"

recognizer = sr.Recognizer()


# ---------- Ovozni matnga (STT) ----------
def listen() -> str | None:
    """Mikrofondan eshitib, matnga aylantiradi."""
    with sr.Microphone() as source:
        print("\n🎤 Eshityapman...", flush=True)
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
        except sr.WaitTimeoutError:
            return None

    print("   (tushunyapman...)", flush=True)
    try:
        return recognizer.recognize_google(audio, language="uz-UZ")
    except sr.UnknownValueError:
        print("   Tushunmadim, qaytaring.")
        return None
    except sr.RequestError as e:
        print(f"   [xato] Tanish xizmatiga ulanib bo'lmadi: {e}")
        return None


# ---------- Matnni ovozga (TTS) ----------
async def speak(text: str):
    """Matnni o'zbekcha ovoz bilan o'qiydi."""
    if not text.strip():
        return
    # Uzun javobni qisqartirmaymiz, lekin markdown belgilarini tozalaymiz
    clean = text.replace("*", "").replace("#", "").replace("`", "")

    tmp = Path(tempfile.gettempdir()) / "jarvis_tts.mp3"
    communicate = edge_tts.Communicate(clean, VOICE)
    await communicate.save(str(tmp))

    # FFmpeg'ning ffplay dasturi bilan eshittiramiz
    subprocess.run(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(tmp)],
        check=False,
    )


# ---------- Ruxsat ----------
async def confirm_in_terminal(tool_name, input_data, context):
    if tool_name == "Bash":
        command = input_data.get("command", "")
        print(f"\n  [!] Buyruq: {command}")
        answer = await anyio.to_thread.run_sync(
            lambda: input("      Ruxsat? (ha/yo'q): ").strip().lower()
        )
        if answer in ("ha", "h", "y", "yes", "ok"):
            return PermissionResultAllow(updated_input=input_data)
        return PermissionResultDeny(message="Ruxsat berilmadi.")
    return PermissionResultAllow(updated_input=input_data)


async def main():
    print("=" * 55)
    print("  JARVIS  ·  ovozli rejim")
    print("  Gapiring. Chiqish uchun: 'chiqish' deng.")
    print("=" * 55)

    extra = "\nSen ovozli rejimda ishlayapsan — javoblaring qisqa va " \
            "gapirishga qulay bo'lsin. Ro'yxat va belgilar ishlatma.\n"

    async with Jarvis(confirm_fn=confirm_in_terminal, extra_prompt=extra) as jarvis:
        await speak("Salom Azizbek, men tayyorman.")

        while True:
            text = await anyio.to_thread.run_sync(listen)
            if not text:
                continue

            print(f"Siz: {text}")
            if text.strip().lower() in ("chiqish", "to'xta", "xayr"):
                print("  (xotira yangilanyapti...)")
                await jarvis.remember()
                await speak("Xayr, Azizbek.")
                break

            print("Jarvis: ", end="", flush=True)
            try:
                javob = await jarvis.ask(
                    text, on_chunk=lambda t: print(t, end="", flush=True)
                )
                print()
                await speak(javob)
            except Exception as e:
                print(f"\n  [xato] {e}")


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        print("\nXayr!")
