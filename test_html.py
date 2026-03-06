import urllib.request
import json
req = urllib.request.Request('http://127.0.0.1:5000/api/create-auction', data=b'', method='POST')
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())
    room_code = data['room_code']

url = f'http://127.0.0.1:5000/admin/{room_code}'
with urllib.request.urlopen(url) as response:
    html = response.read().decode('utf-8')

# Find the script block
idx = html.find('AUCTION_CONFIG')
print("--- SCRIPT BLOCK ---")
print(html[idx-100:idx+300])
print("--------------------")
