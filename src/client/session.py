import httpcloak

def build_session():
    return httpcloak.Session(
        preset="chrome-latest",
        timeout=30,
    )