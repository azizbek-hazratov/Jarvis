"""
JARVIS — terminal rejimi

Ishga tushirish:
    python jarvis.py            # buyruqlar uchun tasdiq so'raydi (tavsiya)
    python jarvis.py --erkin    # tasdiqsiz bajaradi (ehtiyot bo'ling)

Chiqish: "chiqish" yoki Ctrl+C
"""

import sys

import anyio
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

from jarvis_core import Jarvis, auto_approve

ERKIN = "--erkin" in sys.argv


async def confirm_in_terminal(tool_name, input_data, context):
    """Bash uchun terminalda tasdiq so'raydi."""
    if tool_name == "Bash":
        command = input_data.get("command", "")
        print(f"\n  [!] Terminal buyrug'i:")
        print(f"      {command}")
        answer = await anyio.to_thread.run_sync(
            lambda: input("      Ruxsat berasizmi? (ha/yo'q): ").strip().lower()
        )
        if answer in ("ha", "h", "y", "yes", "ok", "+"):
            return PermissionResultAllow(updated_input=input_data)
        return PermissionResultDeny(message="Azizbek ruxsat bermadi.")
    return PermissionResultAllow(updated_input=input_data)


async def main():
    print("=" * 58)
    print("  JARVIS  ·  terminal rejimi" + ("  [ERKIN REJIM]" if ERKIN else ""))
    print("  Chiqish uchun: chiqish")
    print("=" * 58)
    if ERKIN:
        print("  Diqqat: buyruqlar tasdiqsiz bajariladi.\n")

    ruxsat = auto_approve if ERKIN else confirm_in_terminal
    async with Jarvis(confirm_fn=ruxsat) as jarvis:
        while True:
            try:
                user_input = await anyio.to_thread.run_sync(
                    lambda: input("\nSiz: ").strip()
                )
            except (EOFError, KeyboardInterrupt):
                user_input = "chiqish"

            if not user_input:
                continue

            if user_input.lower() in ("chiqish", "exit", "quit", "q"):
                print("\n  (xotira yangilanyapti...)", end="", flush=True)
                ok = await jarvis.remember()
                print(" tayyor." if ok else " o'tkazib yuborildi.")
                print("Jarvis: Xayr, Azizbek!")
                break

            print("\nJarvis: ", end="", flush=True)
            try:
                await jarvis.ask(
                    user_input,
                    on_chunk=lambda t: print(t, end="", flush=True),
                )
            except Exception as e:
                print(f"\n  [xato] {e}")
            print()


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        print("\nXayr!")
