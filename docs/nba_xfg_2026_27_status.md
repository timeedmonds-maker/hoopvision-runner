# NBA shot-level xFG status — 2026-27

Verified 2026-10-20 NZ time using the public HoopVision runner.

## Back-door route

Endpoint:
`https://stats.gleague.nba.com/stats/shotqualityvideologs`

Request contract retained from 2025-26:
- `GameID=<10 digit NBA game id>`
- `PlayerID=<NBA person id>`
- browser-like NBA headers

Shot-level xFG field:
- `shotList[].shotQuality`
- percentage form = `shotQuality * 100` when stored as 0..1 probability

Primary join:
`(game_id, event_num, player_id)`

## Live verification

### Positive control — 2025-26 regular season
Game `0022500001`, player `1641708` (Amen Thompson):
- HTTP 200
- 16 shot rows
- 16 numeric `shotQuality` values
- event 15 resolved exactly
- event 15 `shotQuality=0.379` -> xFG 37.9%

Therefore the endpoint and access route are still operational.

### 2026-27 preseason controls
MIA-TOR `0012600009`, Andrew Wiggins `203952`:
- HTTP 200
- response game id correct
- `shotList=[]`
- no shot-level xFG rows

UTA-DEN `0012600067`, Cameron Johnson `1629661`:
- HTTP 200
- response game id correct
- `shotList=[]`
- no shot-level xFG rows

## Current conclusion

The back-door endpoint is alive, but NBA is not exposing shot-level xFG through this route for the tested 2026-27 preseason games.

Do **not** mark 2026-27 regular-season xFG as confirmed until a completed 2026-27 regular-season game returns non-empty `shotList` rows with numeric `shotQuality`.

The first regular-season recheck should use the same endpoint immediately after a completed opening-night game and validate:
1. HTTP 200;
2. matching `gameId`;
3. non-empty `shotList`;
4. numeric `shotQuality`;
5. exact event join against public PBP/HLS using `eventNum` and `PlayerID`.
