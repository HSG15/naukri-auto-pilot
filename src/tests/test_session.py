import httpcloak
#============================test login with httpclok================
def test_login(username, password):
    session = httpcloak.Session(preset="chrome-latest")
    
    res = session.post(
        "https://www.naukri.com/central-login-services/v1/login",
        headers={
            "accept": "application/json",
            "appid": "105",
            "clientid": "d3skt0p",
            "content-type": "application/json",
            "referer": "https://www.naukri.com/nlogin/login",
            "systemid": "jobseeker",
            "x-requested-with": "XMLHttpRequest",
        },
        json={
            "username": username,
            "password": password
        }
    )

    print("Status:", res.status_code)
    print("Protocol:", res.protocol)
    print("Cookies type:", type(res.cookies))
    print("Cookies:", res.cookies)
    print("Session cookies type:", type(session.cookies))
    print("Session cookies:", session.cookies)
    print("Response:", res.text[:500])

# test_login("mynassae", ",usspass") 
 


session = httpcloak.Session(preset="chrome-latest")

# 1. Check TLS fingerprint (JA3/JA4)
r = session.get("https://tls.peet.ws/api/all")
data = r.json()
print("JA3:", data.get("tls", {}).get("ja3"))
print("JA4:", data.get("tls", {}).get("ja4"))
print("Protocol:", r.protocol)

# 2. Check Cloudflare bot score
r2 = session.get("https://cf.erisa.uk/")
print("\nCloudflare check:")
print(r2.text)

# 3. Check ECH / TLS version
r3 = session.get("https://www.cloudflare.com/cdn-cgi/trace")
print("\nCloudflare trace:")
print(r3.text)