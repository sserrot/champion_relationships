import scrapy
import champion_list
from bs4 import BeautifulSoup
import re

base = 'https://universe.leagueoflegends.com/en_US/champion/'
#'https://universe.leagueoflegends.com/en_US/champion/aatrox/'


class ChampionsSpider(scrapy.Spider):
    name = "champions"

    champs = champion_list.main()
    # scrape all champions
    full_url = [base + c + '/' for c in champs]

    # add wukong
    full_url.append('https://universe.leagueoflegends.com/en_US/champion/monkeyking/')  #  rito why?

    start_urls = full_url

    def parse(self, response):
        # use lxml to get decent HTML parsing speed
        soup = BeautifulSoup(response.text, 'lxml')

        # get champion name
        champion_name = [name for name in soup.find('div', class_='default-2-3').h3]
        champion_name = [champion.replace(' ', '') for champion in champion_name]
        champion_name = [champion.replace('.', '') for champion in champion_name]
        champion_name = [champion.replace('\'', '') for champion in champion_name]

        # get what faction the champion is in
        # use regex to remove white spaces (causes problems with 2 faction champions, but we'll handle that in R)
        faction = [re.sub(r"\W", "", name.text) for name in soup.find_all('div', class_='faction-small')]

        # find friends and rivals - base case = no relationships
        friends = [""]
        rivals = [""]
        header = soup.find_all('div', {'id': 'lore-blocks'})  # grab the lore block and prep to iterate headers

        # check if the lore block header == friends and then assign all names to friends[]
        # overall trys are if there are no friends or rivals (poor Rek'sai)
        try:
            if header[0].find_all('header', class_='header')[0].h3.text.lower() == 'friends':
                friends_soup = header[0].find_all('ul', class_='grid-list gs-no-gutter champion-grid')[0]
                friends = [name['data-rg-id'] for name in friends_soup.find_all('div', class_="champ-name")]
                # check for rivals and store if exist.
                try:
                    if header[0].find_all('header', class_='header')[1].h3.text.lower() == 'rivals':
                        rivals_soup = header[0].find_all('ul', class_='grid-list gs-no-gutter champion-grid')[1]
                        rivals = [name['data-rg-id'] for name in rivals_soup.find_all('div', class_="champ-name")]
                except IndexError:
                    rivals = [""]
        except IndexError:
            friends = [""]

        try:
            if header[0].find_all('header', class_='header')[0].h3.text.lower() == 'rivals':
                rivals_soup = header[0].find_all('ul', class_='grid-list gs-no-gutter champion-grid')[0]
                rivals = [name['data-rg-id'] for name in rivals_soup.find_all('div', class_="champ-name")]
        except IndexError:
            rivals = [""]

        # get rid of MonkeyKing for further data analysis
        friends = [champ_name.replace('MonkeyKing', 'Wukong') for champ_name in friends]

        yield {
            "champion_name": champion_name,
            "faction": faction,
            "friends": friends,
            "rivals": rivals
        }

# scrapy crawl champions -o champions.json to get a json file
