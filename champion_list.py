import os
from cassiopeia import riotapi
from cassiopeia.type.core.common import LoadPolicy

# to do - iterate through champions (remove spaces first) and link up with the webcrawler champions_spider.py
# https://github.com/meraki-analytics/cassiopeia/blob/master/examples/champion_id_to_name_mapping.py


def main():
    # Setup riotapi
    key = os.environ.get('DEV_KEY')
    riotapi.set_region("NA")
    riotapi.print_calls(True)
    riotapi.set_api_key(key)
    riotapi.set_load_policy(LoadPolicy.lazy)

    champions = riotapi.get_champions()
    mapping = {champion.id: champion.name for champion in champions}

    champ_list = [mapping[champion] for champion in mapping]
    
    champ_list = [champion.replace(' ', '') for champion in champ_list]

    champ_list = [champion.replace('.', '') for champion in champ_list]

    champ_list = [champion.replace('\'', '') for champion in champ_list]

    champ_list = [champion.lower() for champion in champ_list]
    
    champ_list.sort()

    return champ_list

if __name__ == "__main__":
    main()
