from pymongo import MongoClient, InsertOne, UpdateOne
import time


client = MongoClient("mongodb://localhost:27017/")
db_v1 = client["playstation_ecosystem"]  # incijalna schema
db_v2 = client["playstation_ecosystem_optimized"]

def etl_games_opt():
    print("Faza 1: Kreiranje games_opt (Igre + Cene)")
    db_v2["games_opt"].drop()
    
    pipeline = [
        # Games ce sada imati i cenu i broj trofeja direktno u dokumentu
        {
            "$lookup": {
                "from": "prices",
                "localField": "_id",
                "foreignField": "gameid",
                "as": "cena_info"
            }
        },
        { "$unwind": { "path": "$cena_info", "preserveNullAndEmptyArrays": True } },

        {
            "$lookup": {
                "from": "player_history_opt",
                "let": { "game_id": "$_id" },
                "pipeline": [
                    { "$match": { "$expr": { "$eq": ["$gameid", "$$game_id"] } } },
                    { "$group": { "_id": "$playerid" } },
                    { "$count": "unique_players_count" }
                ],
                "as": "history_stats"
            }
        },
        { "$unwind": { "path": "$history_stats", "preserveNullAndEmptyArrays": True } },
        
        {
            "$project": {
                "_id": 1,
                "title": 1,
                "platform": 1,
                "developers": 1,
                "publishers": 1,
                "supported_languages": 1,
                "release_date": 1,
                "genres": 1,
                "price_usd": { "$ifNull": ["$cena_info.usd", "$$REMOVE"] }, # ako cena ne postoji, uklanja se polje
                "achievements": 1,
                "total_achievements_count": { "$size": { "$ifNull": ["$achievements", []] } },
                "total_num_of_players": { "$ifNull": ["$history_stats.unique_players_count", 0] }
            }
        },
        
        # Upisujemo rezultat u novu bazu i novu kolekciju
        {
            "$out": {
                "db": "playstation_ecosystem_optimized",
                "coll": "games_opt"
            }
        }
    ]
    
    db_v1["games"].aggregate(pipeline)
    print("Kolekcija games_opt je uspešno kreirana u novoj bazi.")

def etl_player_history_opt():
    print("\nFaza 2: Generisanje player_history_opt")
    db_v2["player_history_opt"].drop()
    
    pipeline = [
        # Player history ce sada imati i informacije o igri i o igracu direktno u dokumentu
        {
            "$lookup": {
                "from": "players",
                "localField": "playerid",
                "foreignField": "_id",
                "as": "p_info"
            }
        },
        { "$unwind": { "path": "$p_info", "preserveNullAndEmptyArrays": True } },
        {
            "$lookup": {
                "from": "games",
                "localField": "gameid",
                "foreignField": "_id",
                "as": "g_info"
            }
        },
        { "$unwind": { "path": "$g_info", "preserveNullAndEmptyArrays": True } },
        
        {
            "$project": {
                "playerid": 1,
                "gameid": 1,
                "achievementid": 1,
                "date_acquired": 1,
                "player_country": { "$ifNull": ["$p_info.country", "Unknown"] },
                "game_title": { "$ifNull": ["$g_info.title", ""] },
                "game_release_date": "$g_info.release_date",
                "game_total_achievements": { "$size": { "$ifNull": ["$g_info.achievements", []] } },
                "target_achievement": {
                    "$filter": {
                        "input": { "$ifNull": ["$g_info.achievements", []] },  #niz svih trofeja
                        "as": "ach", #svaki pojedinačni trofej privremeno nazivamo ach
                        "cond": { "$eq": ["$$ach.achievementid", "$achievementid"] }
                    }
                }
            }
        },
        { "$unwind": { "path": "$target_achievement", "preserveNullAndEmptyArrays": True } },

        {
            "$project": {
                "_id": 0,
                "playerid": 1,
                "gameid": 1,
                "achievementid": 1,
                "date_acquired": 1,
                "player_country": 1,
                "game_title": 1,
                "game_release_date": 1,
                "game_total_achievements": 1,
                "ach_rarity": { "$ifNull": ["$target_achievement.rarity", "Common"] },
                "ach_title": { "$ifNull": ["$target_achievement.title", ""] }
            }
        },
        # Upisujemo rezultat u novu bazu i novu kolekciju
        {
            "$out": {
                "db": "playstation_ecosystem_optimized",
                "coll": "player_history_opt"
            }
        }
    ]
    
    print("Pokreće se agregacija...")
    db_v1["player_history"].aggregate(pipeline, allowDiskUse=True)
    print("Kolekcija player_history_opt je uspešno kreirana u novoj bazi.")

def etl_prices_opt():
    print("\nFaza 3: Kopiranje prices kolekcije u optimizovanu bazu")
    db_v2["prices_opt"].drop()
    
    db_v1["prices"].aggregate([
        {"$out": {"db": "playstation_ecosystem_optimized", "coll": "prices_opt"}}
    ])
    print("Kolekcija prices je kopirana u optimizovanu bazu.")

def etl_players_opt():
    print("\nFaza 4: Kopiranje players kolekcije u optimizovanu bazu")
    db_v2["players_opt"].drop()
    
    db_v1["players"].aggregate([
        {"$out": {"db": "playstation_ecosystem_optimized", "coll": "players_opt"}}
    ])
    print("Kolekcija players je kopirana u optimizovanu bazu.")

def create_indexes_new_db():
    print("\nFaza 5: Kreiranje indeksa u novoj bazi")
    
    print("Indeksiranje player_history_opt...")
    db_v2["player_history_opt"].create_index([("gameid", 1), ("date_acquired", 1)])
    db_v2["player_history_opt"].create_index([("date_acquired", 1), ("ach_rarity", 1)]) 
    db_v2["player_history_opt"].create_index({ "gameid": 1, "playerid": 1, "game_title": 1, "game_total_achievements": 1 })

    print("Svi indeksi su izgrađeni u 'playstation_ecosystem_optimized'!")

if __name__ == "__main__":
    etl_games_opt()
    etl_player_history_opt()
    etl_prices_opt()
    etl_players_opt()
    create_indexes_new_db()
    print("\n[USPEH] Kompletan uvoz podataka u MongoDB je završen")