import os
import cassiopeia as cass

def main():
    # Setup riotapi
    #key = os.environ.get('DEV_KEY')
    cass.set_default_region("NA")
    #cass.print_calls(True)
    #cass.set_api_key(key)
    #cass.set_load_policy(LoadPolicy.lazy)

    champions = cass.get_champions()
    mapping = {champion.id: champion.name for champion in champions}

    champ_list = [mapping[champion] for champion in mapping]

    champ_list = [champion.replace(' ', '') for champion in champ_list]

    champ_list = [champion.replace('.', '') for champion in champ_list]

    champ_list = [champion.replace('\'', '') for champion in champ_list] # Cho\Gath etc.
    #nunu&willump - might need to replace

    champ_list = [champion.lower() for champion in champ_list]
    
    champ_list.sort()

    return champ_list

if __name__ == "__main__":
    main()
