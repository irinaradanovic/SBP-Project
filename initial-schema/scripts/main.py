from clean_utils import parse_date, parse_list
from pymongo import MongoClient, InsertOne, UpdateOne
import pandas as pd
import os
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

client = MongoClient("mongodb://localhost:27017/")
db = client["playstation_ecosystem"]

def import_games_and_achievements():
    print("Faza 1: Igre i dostignuća")
    games_collection = db["games"]
    games_collection.drop()
    
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
    print("\nFaza 2: Igrači i Istorija")
    players_collection = db["players"]
    history_collection = db["player_history"]
    
    players_collection.drop()
    history_collection.drop()
    
    print("Učitavanje i uvoz igrača...")
    players_df = pd.read_csv(os.path.join(DATA_DIR, 'players.csv'))
    players_docs = []
    for _, row in players_df.iterrows():
        doc = {"_id": str(row['playerid'])}
        if not pd.isna(row['nickname']): doc['nickname'] = row['nickname']
        if not pd.isna(row['country']): doc['country'] = row['country']
        doc['purchased_games'] = []
        players_docs.append(doc)
    
    if players_docs:
        players_collection.insert_many(players_docs)
    print(f"Uvezeno {len(players_docs)} igrača.")
    del players_df
    del players_docs

    # Dodavanje kupljenih igara igračima
    print("\nDodavanje kupljenih igara igračima...")
    pur_df = pd.read_csv(os.path.join(DATA_DIR, 'purchased_games.csv'))
    bulk_updates = []
    for _, row in pur_df.iterrows():
        games_list = parse_list(row['library'])
        if games_list:
            bulk_updates.append(UpdateOne(
                {"_id": str(row['playerid'])},
                {"$set": {"purchased_games": [str(g) for g in games_list]}}
            ))
        if len(bulk_updates) >= 20000:
            players_collection.bulk_write(bulk_updates)
            bulk_updates = []
    if bulk_updates:
        players_collection.bulk_write(bulk_updates)
    print("Biblioteke kupljenih igara uspešno dodate.")
    del pur_df


    print("\nUvoženje istorije dostignuća u posebnu kolekciju 'player_history'...")
    chunk_size = 50000
    chunk_count = 0
    
    for chunk in pd.read_csv(os.path.join(DATA_DIR, 'history.csv'), chunksize=chunk_size):
        bulk_inserts = []
        for _, row in chunk.iterrows():
            ach_id = str(row['achievementid'])
            # Achievemnt id sadrži game_id kao prefiks, pa ga izdvajamo
            game_id = ach_id.split('_')[0]
            
            doc = {
                "playerid": str(row['playerid']),
                "achievementid": ach_id
            }
            if game_id: 
                doc["gameid"] = game_id
                
            acq_date = parse_date(row['date_acquired'])
            if acq_date: 
                doc['date_acquired'] = acq_date
                
            bulk_inserts.append(InsertOne(doc))
            
        if bulk_inserts:
            history_collection.bulk_write(bulk_inserts, ordered=False)
            
        chunk_count += 1
        print(f"Uspešno upisano {chunk_count * chunk_size} redova u bazu...")
        time.sleep(0.3)
        
    print("Kolekcija 'player_history' je uspešno kreirana i napunjena!")


def import_price_history():
    print("\nFaza 3: Istorija cena")
    price_collection = db["price_history"]
    price_collection.drop()
    
    print("Ucitavanje prices.csv...")
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