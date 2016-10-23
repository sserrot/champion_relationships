import urllib.request
import shutil
import champion_list

base = 'https://ddragon.leagueoflegends.com/cdn/6.20.1/img/champion/'

champs = champion_list.main()

# this is to find any errors in grabbing champion images
# wrong_http = [""]

# Download the file from `url` and save it locally under `file_name`:

for c in champs:
    url = base + c.title() + '.png'
    file_name = c + '.png'
    try:
        with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print('saving ' + file_name + ' to directory...')
    except IOError:
        #wrong_http.append(("ERROR:" + c))
        continue

# do it for Wukong and other champions with errors

formatted_champs = ["AurelionSol", "DrMundo","FiddleSticks", "JarvanIV", "KogMaw", "LeeSin", "MasterYi",
"MissFortune", "TwistedFate", "XinZhao", "RekSai", "TahmKench"]

for c in formatted_champs:
    url = base + c + '.png'
    file_name = c.lower() + '.png'
    try:
        with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
    except IOError:
        continue

# get Wukong
url = 'https://ddragon.leagueoflegends.com/cdn/6.20.1/img/champion/MonkeyKing.png'
file_name = 'wukong.png'
with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
    shutil.copyfileobj(response, out_file)

# get Skaarl
url = 'https://lolstatic-a.akamaihd.net/game-info/1.1.9/images/champion/icons/Skaarl_Square_Icon.png'
file_name = 'skaarl.png'
with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
    shutil.copyfileobj(response, out_file)

# print out to find any other champion images that fail
# print(wrong_http)
