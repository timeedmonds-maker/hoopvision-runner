"""Single licensed SDK smoke with zero public persistence beyond runner-local temporary files.

The game is selected from public NBA schedule JSON, never embedded into
workflow configuration, printed, uploaded, or retained. No private source.
"""
import {capture} from './capture.mjs';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const headers={
  Accept:'application/json, text/plain, */*',
  'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
  Referer:'https://www.nba.com/'
};
const url='https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json';
const result=await fetch(url,{headers,signal:AbortSignal.timeout(18000)});
if(!result.ok)throw Error('official_schedule_unavailable');
const schedule=await result.json();
const ids=[];
for(const d of schedule?.leagueSchedule?.gameDates||[]){
 for(const item of d.games||[]){
  const id=String(item.gameId||'');
  const ms=Date.parse(item.gameDateTimeUTC||'');
  if(/^(002|003|004|005|006)26\d{5}$/.test(id)&&
     String(item.gameStatus)==='3'&&Number.isFinite(ms)&&
     ms<Date.now()-6*3600000)ids.push({id,ms});
 }
}
ids.sort((a,b)=>a.ms-b.ms);
if(!ids.length)throw Error('no_completed_game_for_smoke');
const first=ids[0];
const job={
 game_id:first.id,account_id:'nba',program_id:'companion-'+first.id+'-positions',
 part:0,start_ms:Math.floor((first.ms-10*60000)/5000)*5000,count:300
};
const directory=mkdtempSync(join(tmpdir(),'licensed-ephemeral-smoke-'));
try{
 await capture(job,directory);
 const qa=JSON.parse(readFileSync(join(directory,'manifest.json'),'utf8'));
 if(qa.successful_windows!==300||qa.unique_keyframes===0||qa.frames_with_players===0)
  throw Error('insufficient_live_sdk_observations');
 console.log('PUBLIC_EPHEMERAL_300_SLOT_SDK_PASS');
}catch(e){
 console.error('PUBLIC_EPHEMERAL_300_SLOT_SDK_FAILED');
 process.exitCode=1;
}finally{
 rmSync(directory,{recursive:true,force:true});
}
