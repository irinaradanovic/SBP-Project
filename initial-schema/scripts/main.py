from clean_utils import parse_date, parse_list
from pymongo import MongoClient, UpdateOne, InsertOne
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


client = MongoClient("mongodb://localhost:27017/")
db = client["playstation_ecosystem"]

def import_games_and_achievements():
    print("Faza 1: Igre i dostignuća")
    games_collection = db["games"]
    games_collection.drop() # resetuj kolekciju ako postoji
    
    print("Ucitavanje games.csv...")
    games_df = pd.read_csv(os.path.join(DATA_DIR, 'games.csv'))
    
    games_docs = []
    for _, row in games_df.iterrows():
        doc = {"_id": str(row['gameid'])}
        if not pd.isna(row['title']): doc['title'] = row['title']
        if not pd.isna(row['platform']): doc['platform'] = row['platform']
        
        for field in ['developers', 'publishers', 'genres', 'supported_languages']:
            lst = parse_list(row[field])
            if lst: doc[field] = lst
            
        rel_date = parse_date(row['release_date'])
        if rel_date: doc['release_date'] = rel_date
        
        # Inicijalizujemo prazne liste za achievements
        doc['achievements'] = []
        games_docs.append(doc)
        
    if games_docs:
        games_collection.insert_many(games_docs)
        print(f"Uvezeno {len(games_docs)} igara.")


    print("Ucitavanje achievements.csv i ugnjezdenje u igre...")
    ach_df = pd.read_csv(os.path.join(DATA_DIR, 'achievements.csv'))
    
    bulk_updates = []
    for _, row in ach_df.iterrows():
        ach_obj = {"achievementid": str(row['achievementid'])}
        if not pd.isna(row['title']): ach_obj['title'] = row['title']
        if not pd.isna(row['description']): ach_obj['description'] = row['description']
        if not pd.isna(row['rarity']): ach_obj['rarity'] = row['rarity']
        
        # Ubacujemo achievement u odgovarajuću igru koristeći $push
        bulk_updates.append(UpdateOne(
            {"_id": str(row['gameid'])},
            {"$push": {"achievements": ach_obj}}
        ))
        
        if len(bulk_updates) >= 20000:
            games_collection.bulk_write(bulk_updates)
            bulk_updates = []
            
    if bulk_updates:
        games_collection.bulk_write(bulk_updates)
    print("Games kolekcija je uspešno ugnježdena sa achievements.")


def import_players_and_history():
    print("\nFaza 2: Igraci i istorija dostignuca")
    players_collection = db["players"]
    players_collection.drop()
    
    print("Ucitavanje players.csv...")
    players_df = pd.read_csv(os.path.join(DATA_DIR, 'players.csv'))
    
    players_docs = []
    for _, row in players_df.iterrows():
        doc = {"_id": str(row['playerid'])}
        if not pd.isna(row['nickname']): doc['nickname'] = row['nickname']
        if not pd.isna(row['country']): doc['country'] = row['country']
        
        doc['purchased_games'] = []
        doc['earned_achievements'] = []
        players_docs.append(doc)
        
    if players_docs:
        players_collection.insert_many(players_docs)
        print(f"Uvezeno {len(players_docs)} igrača.")


    print("Ucitavanje purchased_games.csv...")
    pur_df = pd.read_csv(os.path.join(DATA_DIR, 'purchased_games.csv'))
    
    bulk_updates = []
    for _, row in pur_df.iterrows():
        games_list = parse_list(row['library'])
        if games_list:
            games_list_str = [str(g) for g in games_list]
            bulk_updates.append(UpdateOne(
                {"_id": str(row['playerid'])},
                {"$set": {"purchased_games": games_list_str}}
            ))
            
        if len(bulk_updates) >= 20000:
            players_collection.bulk_write(bulk_updates)
            bulk_updates = []
            
    if bulk_updates:
        players_collection.bulk_write(bulk_updates)
    print("Biblioteke kupljenih igara uspešno dodate igračima.")


    #Kreiranje mape iz achievements.csv za dobavljanje gameid podatka
    print("Kreiranje mape dostignuća i pripadajućih igara iz achievements.csv...")
    ach_map_df = pd.read_csv(os.path.join(DATA_DIR, 'achievements.csv'), usecols=['achievementid', 'gameid'])
    ach_to_game_map = dict(zip(ach_map_df['achievementid'].astype(str), ach_map_df['gameid'].astype(str)))
    del ach_map_df # Oslobađamo memoriju

    print("Ucitavanje history.csv...")
    chunk_size = 50000
    chunk_count = 0
    
    for chunk in pd.read_csv(os.path.join(DATA_DIR, 'history.csv'), chunksize=chunk_size):
        bulk_updates = []
        for _, row in chunk.iterrows():
            ach_id = str(row['achievementid'])
            game_id = ach_to_game_map.get(ach_id)
            
            earned_obj = {
                "achievementid": ach_id
            }
            # Dodajemo gameid samo ako smo ga uspešno locirali u mapi
            if game_id:
                earned_obj["gameid"] = game_id
                
            acq_date = parse_date(row['date_acquired'])
            if acq_date: 
                earned_obj['date_acquired'] = acq_date
            
            bulk_updates.append(UpdateOne(
                {"_id": str(row['playerid'])},
                {"$push": {"earned_achievements": earned_obj}}
            ))
            
        if bulk_updates:
            players_collection.bulk_write(bulk_updates)
            
        chunk_count += 1
        print(f"Obrađeno {chunk_count * chunk_size} redova iz history.csv...")
        
    print("Istorija zarađenih dostignuća uspešno ugnježđena u igrače.")


def import_price_history():
    print("\nFaza 3: Istorija cena")
    price_collection = db["price_history"]
    price_collection.drop()
    
    print("UUcitavanje prices.csv...")
    prices_df = pd.read_csv(os.path.join(DATA_DIR, 'prices.csv'))
    
    price_docs = []
    for _, row in prices_df.iterrows():
        doc = {"gameid": str(row['gameid'])}
        
        for curr in ['usd', 'eur', 'gbp', 'jpy', 'rub']:
            if not pd.isna(row[curr]): 
                doc[curr] = float(row[curr])
                
        acq_date = parse_date(row['date_acquired'])
        if acq_date: doc['date_acquired'] = acq_date
        
        price_docs.append(InsertOne(doc))
        
        if len(price_docs) >= 20000:
            price_collection.bulk_write(price_docs)
            price_docs = []
            
    if price_docs:
        price_collection.bulk_write(price_docs)
    print("Kolekcija 'price_history' uspešno napunjena.")


if __name__ == "__main__":
    import_games_and_achievements()
    import_players_and_history()
    import_price_history()
    print("\n[USPEH] Kompletan uvoz podataka u MongoDB je završen")