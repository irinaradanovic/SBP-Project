# Optimizovana schema

games_opt kolekcija (info o igrama i mogućim dostignućima, dodata i cena u USD i broj mogućih dostignuća):

1. Delimična denormalizacija: Ugrađivanjem polja `price_usd` (najčešće korišćene valute za analitiku) eliminisano je skupo pretraživanje kolekcije `prices`
2. Izračunata polja: Dodavanjem polja `total_achievements_count` i `total_num_of_players` izbegnuto je kontinualno računanje veličine niza pri svakom upitu

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
   ],
   "price_usd": double,
   "total_achievements_count": integer,
   "total_num_of_players": integer
}
```

---
players_opt kolekcija (ista kao i original)

```text
{
  "_id": "string",
  "nickname": "string",
  "country": "string",
  "purchased_games": ["string"]
}
```

---
player_history_opt kolekcija (info o dostignućima igrača kroz vreme, dodat naziv igre i datum izbacivanja, drzava igraca i rarity dostignuca i njen naziv)

1. Prvobitna kolekcija je imala 19.5 miliona dokumenata i zahtevala je višestruke $lookup i $unwind operacije, što je dovodilo do skeniranja stotina miliona zapisa u radnoj memoriji
2. Ugrađivanjem podataka o igraču i igri, baza sada izvršava kompleksne upite bez skokova u druge delove memorije.

```text
{
  "_id": "ObjectId",
  "achievementid": "string",
  "date_acquired": "date",
  "gameid": "string",
  "playerid": "string",
  "player_country":"string",
  "game_title":"string",
  "game_release_date":"date",
  "game_total_achievements":integer,
  "ach_rarity":"string",
  "ach_title": "string"
}
```

---
prices_opt kolekcija (info o cenama igara, isto kao u originalu)

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

---
# Indeksiranje
---

# Indeksi nad player_history_opt
1. Indeks: {"gameid": 1, "date_acquired":1}
Kompozitni indeks (Compound Index).

U Upitu 1, prva faza je masovno grupisanje 19.5 miliona redova po ključu $gameid kako bi se pronašao prvi osvojeni trofej. 

2. Indeks: {"date_acquired": 1, "ach_rarity": 1}
Kompozitni indeks (Compound Index).

Optimizuje Upit 4 i Upit 5.

Za Upit 4: Prva faza je $match koja filtrira opseg datuma za 2024. godinu i uslov ach_rarity: "Platinum". Pošto indeks sadrži oba polja u ovom redosledu, baza vrši skeniranje i brzo odbacuje nevažeće redove.

3. Indeks { "gameid": 1, "playerid": 1, "game_title": 1, "game_total_achievements": 1 }

Optimizuje Upit 2.
