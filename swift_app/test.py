import requests

url = "https://indiawris.gov.in/basin/getMasterBasin"

payload = {"datasetcode": "DISCHARG"}

headers = {
    "Content-Type": "application/json",
    "Origin": "https://indiawris.gov.in",
    "Referer": "https://indiawris.gov.in/wris/",
    "User-Agent": "Mozilla/5.0"
}

r = requests.post(url, json=payload, headers=headers, verify=False)

print(r.status_code)
print(r.text[:500])