import subprocess

names = ["Jarvis"]
r = subprocess.run(["schtasks", "/query", "/fo", "LIST", "/v"], capture_output=True, text=True)
print("RC:", r.returncode)
print(r.stdout[-6000:] if r.stdout else "")
print("STDERR:", r.stderr[-2000:] if r.stderr else "")
