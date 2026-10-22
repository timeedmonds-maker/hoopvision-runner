/** Private Release season lane. No credential reaches the browser or SDK import. */
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {copyFileSync,existsSync,mkdtempSync,readFileSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {planGame,parseSchedule,selectDue,summarize} from './season_core.mjs';

const REPO='timeedmonds-maker/104';
const PUBLIC='timeedmonds-maker/hoopvision-runner';
const PILOT=process.env.GAMEPULSE_FULLGAME_PILOT==='true';
const INDEX=PILOT?'gamepulse-sdk-public-pilot-index':'gamepulse-sdk-2026-27-index';
const TOKEN=process.env.GH_TOKEN;
const sha=path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const temp=()=>mkdtempSync(join(tmpdir(),'gp-season-'));
function gh(args){
 const p=spawnSync('gh',args,{encoding:'utf8',timeout:120000,maxBuffer:1024*1024,
  stdio:['ignore','pipe','pipe'],env:{...process.env,GH_TOKEN:TOKEN}});
 return {ok:p.status===0,out:p.stdout||''};
}
function call(args){
 const result=gh([...args,'--repo',REPO]);
 if(!result.ok)throw Error('private_github_operation_failed');
 return result.out;
}
function names(tag){
 const r=gh(['release','view',tag,'--repo',REPO,'--json','assets']);
 if(!r.ok)return null;
 try{return new Set(JSON.parse(r.out).assets.map(x=>x.name));}
 catch{throw Error('private_asset_listing_invalid');}
}
function ensure(tag){
 if(names(tag)!==null)return;
 call(['release','create',tag,'--target','main','--title',tag,
  '--notes','Private licensed SDK capture; no public observation assets','--latest=false']);
}
function download(tag,name,directory){
 call(['release','download',tag,'--pattern',name,'--dir',directory]);
 const path=join(directory,name);
 if(!existsSync(path))throw Error('private_readback_missing');
 return path;
}
function readIndex(){
 ensure(INDEX);
 const dir=temp();
 try{
  const assets=names(INDEX);
  if(!assets.has('index.json'))return {schema:'gamepulse-season-index.v1',games:{}};
  const obj=JSON.parse(readFileSync(download(INDEX,'index.json',dir),'utf8'));
  if(obj.schema!=='gamepulse-season-index.v1'||!obj.games||typeof obj.games!=='object')
   throw Error('private_index_invalid');
  return obj;
 }finally{rmSync(dir,{recursive:true,force:true});}
}
function writeIndex(index){
 const dir=temp();
 try{
  index.updated_at=new Date().toISOString();
  const p=join(dir,'index.json');writeFileSync(p,JSON.stringify(index)+'\n');
  call(['release','upload',INDEX,p,'--clobber']);
  const verify=temp();
  try{if(sha(download(INDEX,'index.json',verify))!==sha(p))throw Error('private_index_sha_mismatch');}
  finally{rmSync(verify,{recursive:true,force:true});}
 }finally{rmSync(dir,{recursive:true,force:true});}
}
function validatedPart(tag,job,dir){
 const base='sdk-part-'+String(job.part).padStart(2,'0');
 const archive=download(tag,base+'.tar.gz',dir),sidecar=download(tag,base+'.json',dir);
 const m=JSON.parse(readFileSync(sidecar,'utf8'));
 if(m.archive_sha256&&m.archive_sha256!==sha(archive))throw Error('private_archive_sha_mismatch');
 const unpack=temp();
 try{
  const tar=spawnSync('tar',['-xzf',archive,'-C',unpack,'manifest.json'],{stdio:'ignore',timeout:60000});
  if(tar.status!==0)throw Error('private_archive_invalid');
  const embedded=JSON.parse(readFileSync(join(unpack,'manifest.json'),'utf8'));
  for(const field of ['game_id','part','start_ms','successful_windows','frames_with_players',
   'frames_with_ball','empty_windows'])if(m[field]!==embedded[field])throw Error('private_manifest_mismatch');
  // Older private 104 checkpoint manifests did not include a part ordinal.
  // Bind it from the exact asset name and independently checked start/window.
  const normalized={...m,part:m.part??job.part};
  summarize([job],[normalized]);
  return normalized;
 }finally{rmSync(unpack,{recursive:true,force:true});}
}
function repairArchiveOnly(tag,job){
 const base='sdk-part-'+String(job.part).padStart(2,'0');
 const dir=temp(),unpack=temp();
 try{
  const archive=download(tag,base+'.tar.gz',dir);
  const tar=spawnSync('tar',['-xzf',archive,'-C',unpack,'manifest.json'],{stdio:'ignore',timeout:60000});
  if(tar.status!==0)throw Error('orphan_archive_invalid');
  const manifest=JSON.parse(readFileSync(join(unpack,'manifest.json'),'utf8'));
  summarize([job],[{...manifest,part:manifest.part??job.part}]);
  const sidecar=join(dir,base+'.json');
  writeFileSync(sidecar,JSON.stringify({...manifest,part:job.part,archive_sha256:sha(archive)})+'\n');
  call(['release','upload',tag,sidecar]);
  const check=temp();
  try{if(sha(download(tag,base+'.json',check))!==sha(sidecar))throw Error('orphan_repair_sha_mismatch');}
  finally{rmSync(check,{recursive:true,force:true});}
 }finally{rmSync(dir,{recursive:true,force:true});rmSync(unpack,{recursive:true,force:true});}
}
async function capturePart(tag,job,capture){
 const dir=temp();
 try{
  await capture(job,dir);
  const source=JSON.parse(readFileSync(join(dir,'manifest.json'),'utf8'));
  summarize([job],[source]);
  const base='sdk-part-'+String(job.part).padStart(2,'0');
  const archive=join(dir,base+'.tar.gz'),sidecar=join(dir,base+'.json');
  copyFileSync(join(dir,'checkpoint.tar.gz'),archive);
  writeFileSync(sidecar,JSON.stringify({...source,archive_sha256:sha(archive)})+'\n');
  if(readFileSync(archive).length>32*1024*1024)throw Error('checkpoint_too_large');
  call(['release','upload',tag,archive]);
  call(['release','upload',tag,sidecar]);
  const check=temp();
  try{
   const a=download(tag,base+'.tar.gz',check),b=download(tag,base+'.json',check);
   if(sha(a)!==sha(archive)||sha(b)!==sha(sidecar))throw Error('private_sha_mismatch');
  }finally{rmSync(check,{recursive:true,force:true});}
  return source;
 }finally{rmSync(dir,{recursive:true,force:true});}
}
async function archiveGame(game,index,capture){
 const plan=planGame(game),tag=(PILOT?'gamepulse-sdk-public-pilot-':'gamepulse-sdk-')+game.id;
 ensure(tag);
 const reports=[];
 const partLimit=Number(process.env.GAMEPULSE_PARTS_PER_RUN||13);
 if(!Number.isSafeInteger(partLimit)||partLimit<1||partLimit>13)throw Error('invalid_parts_limit');
 let newParts=0;
 for(const job of plan.parts){
  const base='sdk-part-'+String(job.part).padStart(2,'0');
  const existing=names(tag);
  const pair=[existing.has(base+'.tar.gz'),existing.has(base+'.json')];
  if(pair[0]&&!pair[1])repairArchiveOnly(tag,job);
  if(!pair[0]&&pair[1])throw Error('orphan_manifest_requires_review');
  const dir=temp();
  try{reports.push(pair[0]?validatedPart(tag,job,dir):await capturePart(tag,job,capture));}
  finally{rmSync(dir,{recursive:true,force:true});}
  index.games[game.id]={status:'partial',last_checkpoint:job.part,last_attempt:new Date().toISOString()};
  writeIndex(index);
  if(!pair[0] && ++newParts>=partLimit && job.part<plan.parts.length-1){
   console.log('PRIVATE_GAME_PARTIAL_SHA_READBACK');
   return;
  }
 }
 const sum=summarize(plan.parts,reports);
 if(sum.windows!==plan.windows||plan.windows!==3720||plan.parts.length!==13)
  throw Error('full_game_coverage_failed');
 const done={schema:'gamepulse-fullgame-manifest.v1',game_id:game.id,
  tipoff_utc:new Date(game.start).toISOString(),planned_start_ms:plan.begin,
  planned_end_exclusive_ms:plan.end,expected_windows:plan.windows,
  successful_windows:sum.windows,parts:plan.parts.length,
  sum_frames_with_players:sum.players,sum_frames_with_ball:sum.ball,
  empty_windows:sum.empty,data_class:'observed; no missing coordinates imputed',
  acceptance:sum.players>100&&sum.ball>50?'complete_with_QA':'complete_with_missingness_warning',
  completed_at:new Date().toISOString()};
 const dir=temp();
 try{
  const marker=join(dir,'sdk-COMPLETE.json');writeFileSync(marker,JSON.stringify(done)+'\n');
  if(names(tag).has('sdk-COMPLETE.json')){
   const existing=temp();
   try{
    const old=download(tag,'sdk-COMPLETE.json',existing);
    if(JSON.parse(readFileSync(old,'utf8')).successful_windows!==plan.windows)
     throw Error('existing_complete_marker_conflict');
   }finally{rmSync(existing,{recursive:true,force:true});}
  }else call(['release','upload',tag,marker]);
  const readback=temp();
  try{
   const remote=download(tag,'sdk-COMPLETE.json',readback);
   if(!names(tag).has('sdk-COMPLETE.json')||JSON.parse(readFileSync(remote,'utf8')).successful_windows!==3720)
    throw Error('private_complete_readback_failed');
  }finally{rmSync(readback,{recursive:true,force:true});}
 }finally{rmSync(dir,{recursive:true,force:true});}
 index.games[game.id]={status:'complete',captured_at:done.completed_at,qa:done.acceptance,
  windows:sum.windows,frames_with_players:sum.players,frames_with_ball:sum.ball};
 writeIndex(index);
 console.log('PRIVATE_GAME_COMPLETE_SHA_READBACK');
}
async function schedule(){
 const headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Referer':'https://www.nba.com/'};
 const sources=[['modern','https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'],
  ['legacy','https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2026/league/00_full_schedule.json']];
 for(const [kind,url] of sources){
  try{
   const r=await fetch(url,{headers,signal:AbortSignal.timeout(20000)});
   if(!r.ok)continue;
   const games=parseSchedule(await r.json(),kind);
   if(games.length)return games;
  }catch{}
 }
 throw Error('schedule_sources_unavailable');
}
export function assertContext(env){
 if(env.GITHUB_REPOSITORY!==PUBLIC||env.GITHUB_REF!=='refs/heads/main'||
    !['workflow_dispatch','push','schedule'].includes(env.GITHUB_EVENT_NAME)||
    (env.GITHUB_EVENT_NAME!=='workflow_dispatch'&&env.GAMEPULSE_FULLGAME_PILOT!=='true')||
    typeof env.GH_TOKEN!=='string'||
    env.GH_TOKEN.length<30)
  throw Error('unauthorized_private_collection');
}
export async function run(){
 assertContext({...process.env,GH_TOKEN:TOKEN});
 delete process.env.GH_TOKEN;
 // All third-party imports occur only after GH_TOKEN leaves process.env.
 const {capture}=await import('./capture.mjs');
 const index=readIndex(),games=await schedule();
 const due=selectDue(games,index,Date.now());
 console.log('PRIVATE_SEASON_DUE_COUNT',due.length);
 if(process.env.DRY_RUN==='true')return;
 for(const game of due){
  try{await archiveGame(game,index,capture);}
  catch{
   index.games[game.id]={status:'retry',retry_after:Date.now()+6*3600000,
    last_attempt:new Date().toISOString()};
   writeIndex(index);
   console.error('PRIVATE_SEASON_RETRY_REQUIRED');
   process.exitCode=2;
  }
 }
}
if(process.argv[1]?.endsWith('season_private_release.mjs'))
 run().catch(()=>{console.error('PRIVATE_SEASON_STOPPED');process.exitCode=2;});
