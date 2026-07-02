# Inicijalna schema

games kolekcija (info o igrama i mogućim dostignućima):

```text
{
  "_id": "string",
  "title": "string",
  "platform": "string",
  "developers": ["string"],
  "publishers": ["string"],
  "genres": ["string"],
  "supported_languages": ["string"],
  "release_date": "date",
  "achievements": [
    {
      "achievementid": "string",
      "title": "string",
      "description": "string",
      "rarity": "string"
    },
   ]
}
```

---
players kolekcija

```text
{
  "_id": "string",
  "nickname": "string",
  "country": "string",
  "purchased_games": ["string"]
}
```

---
player_history kolekcija (info o dostignućima igrača kroz vreme)

```text
{
  "_id": "ObjectId",
  "achievementid": "string",
  "date_acquired": "date",
  "gameid": "string",
  "playerid": "string"
}
```

---
prices kolekcija (info o cenama igara)

```text
{
  "_id": "string",
  "gameid": "string",
  "usd": double,
  "eur": double,
  "gbp": double,
  "jpy": double,
  "rub": double,
  "date_acquired": "date"
}
```