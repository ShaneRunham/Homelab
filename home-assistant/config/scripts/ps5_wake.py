"""Wakes the PS5 from rest mode with a direct WAKEUP packet (ps5-mqtt's own wake fails behind firewalld).
The credential is the Remote Play registration ps5-mqtt made (copied from ps5-mqtt/config/credentials.json)."""
import json, socket
c = json.load(open("/config/scripts/ps5-credential.json"))
msg = "WAKEUP * HTTP/1.1\n" + "".join(f"{k}:{c[k]}\n" for k in ("client-type", "auth-type", "model", "app-type", "user-credential"))
msg += "device-discovery-protocol-version:00030010\n"
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.sendto(msg.encode(), ("192.168.0.15", 9302))
