// NBA-only schedule/control metadata. No licensed player XYZ or raw app records leave private 104.
import {appendFileSync} from 'node:fs';
const TOKEN=process.env.GH_TOKEN;
const NOW=Date.now();
const MAX=6;
if(!TOKEN || !process.env.GITHUB_OUTPUT)throw Error('PRIVATE_TOKEN_OR_OUTPUT_MISSING');
async function get(url,privateRead=false){
  const res=await fetch(url,{headers:privateRead?{
    Authorization:'Bearer '+TOKEN,Accept:'application/vnd.github+json',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
    'Accept':'application/json, text/plain, */*','Referer':'https://www.nba.com/', 'Origin':'https://www.nba.com', 'Accept-Language':'en-US,en;q=0.9'}:{'User-Agent':'igp-auto-season'},
    signal:AbortSignal.timeout(30000)});
  if(res.status===404)return null;
  if(!res.ok)throw Error('NBA_OR_PRIVATE_STATUS_'+res.status);
  return res.json();
}
async function privateFile(path){
  const url='https://api.github.com/repos/timeedmonds-maker/104/contents/'+path+
    '?ref=research%2Fgamepulse-clock-boundary-integrity-20261025';
  const response=await get(url,true);
  if(!response||response.encoding!=='base64')throw Error('PRIVATE_CANONICAL_INDEX_UNAVAILABLE');
  return JSON.parse(Buffer.from(response.content.replace(/\s/g,''),'base64').toString('utf8'));
}
let fixtures;
for(const source of ['https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json',
  'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json',
  'https://stats.nba.com/stats/scheduleleaguev2?LeagueID=00&Season=2026-27',
  'https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2026/league/00_full_schedule.json']){
  try {
    const payload=await get(source);
    let rows;
    if(source.includes('scheduleLeagueV2')||source.includes('scheduleleaguev2'))rows=((payload.leagueSchedule||payload).gameDates||[])
      .flatMap(d=>d.games||[]).map(x=>({id:String(x.gameId),
        start:Date.parse(x.gameDateTimeUTC),status:String(x.gameStatus)==='3'}));
    else rows=(payload.data.lscd||[]).flatMap(m=>Array.isArray(m.mscd)?
      m.mscd.flatMap(v=>v.g||[]):m.mscd?.g||[]).map(x=>({id:String(x.gid),
      start:Date.parse(String(x.gdtutc)+'T'+String(x.utctm)+':00Z'),
      status:/^final/i.test(String(x.stt||''))}));
    if(rows.length<100)throw Error('NBA_SCHEDULE_INCOMPLETE');
    const map=new Map();
    for(const r of rows){
      if(!/^00226\d{5}$/.test(r.id)||!r.status||!Number.isFinite(r.start)
         ||r.start<Date.parse('2026-10-20T00:00:00Z')
         ||r.start+315*60000>NOW)continue;
      if(map.has(r.id))throw Error('NBA_DUPLICATE_GAME_ID');
      map.set(r.id,{id:r.id,tipoff:new Date(r.start).toISOString(),start:r.start});
    }
    if(map.size<56)throw Error('NBA_FROZEN_56_MISSING_FROM_SCHEDULE');
    fixtures=[...map.values()].sort((a,b)=>a.start-b.start);
    break;
  }catch(error){console.log('NBA_SCHEDULE_FALLBACK',String(error).slice(0,90));}
}
if(!fixtures){
 const y=new Date(NOW-24*3600000).toISOString().slice(0,10);
 const compact=y.replaceAll('-','');
 const probes=[
  'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates='+compact,
  'https://www.nba.com/games?date='+y,
  'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json',
  'https://stats.gleague.nba.com/stats/scoreboardv3?GameDate='+y+'&LeagueID=00',
  'https://www.nba.com/inside-the-game/blueprint/0022600138',
  'https://api-web.nba.com/games?date='+y
 ];
 await Promise.all(probes.map(async (url)=>{
  try {
   const res=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0',
     'Accept':'application/json,text/html,*/*','Referer':'https://www.nba.com/'},
     signal:AbortSignal.timeout(6000)});
   const raw=await res.text();
   const match=(raw.match(/00226\\d{5}/g)||[]);
   console.log('IGP_OFFICIAL_SCHEDULE_ALTERNATE_PROBE',new URL(url).hostname,
       res.status,raw.length,'nba_game_ID_mentions',new Set(match).size);
  } catch(e){console.log('IGP_OFFICIAL_SCHEDULE_ALTERNATE_PROBE_ERROR',
    new URL(url).hostname,String(e).slice(0,65));}
 }));
 throw Error('NO_AUTHORITATIVE_NBA_SCHEDULE');
}
const index=await privateFile('gamepulse/fusion/materialized/igp_2026_27_unified_season_v3/index.json');
if(index.official_games!==56||Object.keys(index.per_game_model).length!==56)
  throw Error('FROZEN_56_CHANGED');
const add=await privateFile(index.post56_additive_oct28.index);
if(add.base_unified_season_games_frozen!==56)throw Error('ADDITIVE_BASELINE_DRIFT');
const pending=fixtures.filter(g=>!(g.id in index.per_game_model)).filter(g=>{
 const grades=add.games[g.id]?.source_capture_grades||{};
 return !(grades.original_native_xyz==='SHA_FULL_13PART'
          &&grades.original_companion==='COMPLETE_ORIGINAL_RESPONSE'
          &&grades.original_nba_blueprint==='SOURCE_SHA_ACCEPTED'
          &&grades.official_logical_chains==='SHA_VERIFIED');
});
const fresh=pending.filter(g=>!(g.id in add.games));
const incomplete=pending.filter(g=>(g.id in add.games));
const rotation=incomplete.length?Math.floor(NOW/(3*3600000))%incomplete.length:0;
const selected=[...fresh,...incomplete.slice(rotation),...incomplete.slice(0,rotation)].slice(0,MAX);
const parts=[],apps=[],games=[];
let reused=0;
for(const game of selected){
  const release=await get('https://api.github.com/repos/timeedmonds-maker/104/releases/tags/gamepulse-sdk-'+game.id,true);
  const a=new Set((release?.assets||[]).map(x=>x.name));
  for(let part=0;part<13;part++){
    const k='sdk-part-'+String(part).padStart(2,'0');
    if(a.has(k+'.tar.gz')&&a.has(k+'.json')){reused++;continue;}
    parts.push({...game,part});
  }
  if(!add.games[game.id]?.original_companion_original_event_body_sha256 ||
     add.games[game.id]?.source_capture_grades?.original_companion!=='COMPLETE_ORIGINAL_RESPONSE')
       apps.push(game);
  games.push(game);
}
const safe=items=>JSON.stringify({include:items.length?items:[{id:'none',tipoff:'1970-01-01T00:00:00Z',part:0}]});
const entries={count:String(selected.length),games:safe(games),parts:safe(parts),
  apps:safe(apps),selected:JSON.stringify(selected.map(x=>x.id))};
for(const [key,value] of Object.entries(entries))
  appendFileSync(process.env.GITHUB_OUTPUT,key+'='+value+'\n');
console.log('IGP_AUTO_SEASON_DISCOVERY',JSON.stringify({
 official_final:fixtures.length,unified_games:56+Object.keys(add.games).length,
 gaps:pending.length,selected:games.length,missing_original_parts:parts.length,
 existing_parts_reused:reused,missing_companion:apps.length}));
