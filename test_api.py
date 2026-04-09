import urllib.request, json, time
try:
    req = urllib.request.Request('https://lichess.org/api/tv/channels')
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        game_id = data['bullet']['gameId']
        
        print('Spectating bullet game:', game_id)
        req2 = urllib.request.Request(f'https://lichess.org/api/stream/game/{game_id}')
        with urllib.request.urlopen(req2) as resp2:
            for line in resp2:
                if line.strip():
                    d = json.loads(line.decode('utf-8').strip())
                    keys = list(d.keys())
                    print('Keys:', keys)
                    if 'status' in d:
                        print('STATUS:', d['status'])
                        print('WINNER:', d.get('winner'))
except Exception as e:
    print('Err:', e)

