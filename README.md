# champion_relationships

Exploring the relationships between all Champions in [League of Legends](leagueoflegends.com).

Tools Used:

[Cassiopeia](https://github.com/meraki-analytics/cassiopeia) to interact with Riot API.

[Scrapy](https://doc.scrapy.org/en/1.2/) to scrape Riot website for champion relationships not in API.

[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) to parse the HTML from Scrapy.

[R](https://www.r-project.org/) to analyze the relationships between champions.


***Important Files***

champions.csv - contains information about champions (name, faction, rivals, and friends) in a .csv file.

champions.json - same information in JSON.

champion_list.py - Uses [Riot API](https://developer.riotgames.com/) to extract a formatted and ordered list of all champions.

tutorial/spiders/champions_spider.py - Scrapy Spider that crawls Riot website for champion information not in the Riot API.

champion_relationships isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc. League of Legends © Riot Games, Inc.
