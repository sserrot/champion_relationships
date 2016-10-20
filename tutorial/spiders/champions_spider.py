import scrapy
import champion_list
import os
from bs4 import BeautifulSoup

base = 'http://gameinfo.na.leagueoflegends.com/en/game-info/champions/'


class ChampionsSpider(scrapy.Spider):
    name = "champions"

    # champs = champion_list.main()
    #
    # # scrape all champions
    #
    # full_url = [base + x + '/' for x in champs]
    #
    # # add wukong
    #
    # full_url.append('http://gameinfo.na.leagueoflegends.com/en/game-info/champions/monkeyking/')  #  rito why?

    test_url = ['http://gameinfo.na.leagueoflegends.com/en/game-info/champions/monkeyking/']

    start_urls = test_url

    def parse(self, response):
        # use lxml to get decent HTML parsing speed
        soup = BeautifulSoup(response.text, 'lxml')
        yield {
            "url": response.url,
            "title": soup.div.string
        }

        # if str(quote.css('header.header::text').extract()) == 'Rivals':


        # # save in html
        # champion = response.url.split("/")[6]
        # filename = '%s.html' % champion
        # with open(filename, 'wb') as f:
        #    f.write(response.body)
