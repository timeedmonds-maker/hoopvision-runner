/** Private Release season lane. No credential reaches the browser or SDK import. */
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {copyFileSync,existsSync,mkdtempSync,readFileSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {planGame,parseSchedule,selectDue,summarize,diagnoseTrackingCoverage} from './season_core.mjs';

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
 const result=gh(['release','create',tag,'--repo',REPO,'--target','main','--title',tag,
  '--notes','Private licensed SDK capture; no public observation assets','--latest=false']);
 if(!result.ok && names(tag)===null)throw Error('private_release_create_failed');
}
function download(tag,name,directory){
 const path=join(directory,name);
 for(let attempt=0;attempt<4;attempt++){
  const result=gh(['release','download',tag,'--pattern',name,'--dir',directory,'--repo',REPO]);
  if(result.ok&&existsSync(path))return path;
  if(attempt<3)spawnSync('sleep',['2'],{stdio:'ignore'});
 }
 throw Error('private_readback_missing');
}
function uploadOrExisting(tag,file,name){
 for(let attempt=0;attempt<4;attempt++){
  const result=gh(['release','upload',tag,file,'--repo',REPO]);
  if(result.ok||names(tag)?.has(name))return;
  if(attempt<3)spawnSync('sleep',['2'],{stdio:'ignore'});
 }
 throw Error('private_upload_failed');
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
  uploadOrExisting(tag,sidecar,base+'.json');
  const check=temp();
  try{if(sha(download(tag,base+'.json',check))!==sha(sidecar))throw Error('orphan_repair_sha_mismatch');}
  finally{rmSync(check,{recursive:true,force:true});}
 }finally{rmSync(dir,{recursive:true,force:true});rmSync(unpack,{recursive:true,force:true});}
}
function repairOrphanManifest(tag,job){
 const base='sdk-part-'+String(job.part).padStart(2,'0');
 const sidecarName=base+'.json',archiveName=base+'.tar.gz';
 const releasePath='repos/'+REPO+'/releases/tags/'+tag;
 function listing(){
  const result=gh(['api',releasePath]);
  if(!result.ok)throw Error('orphan_release_inspection_failed');
  let payload;
  try{payload=JSON.parse(result.out);}catch{throw Error('orphan_asset_listing_invalid');}
  if(!Array.isArray(payload.assets))throw Error('orphan_asset_listing_invalid');
  return payload.assets;
 }
 let assets=listing();
 if(assets.some(x=>x.name===archiveName))return;
 const original=assets.find(x=>x.name===sidecarName);
 if(!original)return;
 const folder=temp(),check=temp();
 try{
  const source=download(tag,sidecarName,folder);
  const record=JSON.parse(readFileSync(source,'utf8'));
  if(record.game_id!==job.game_id||record.part!==job.part||
     record.start_ms!==job.start_ms||record.successful_windows!==job.count)
   throw Error('orphan_sidecar_identity_mismatch');
  const backupName=base+'-orphan-backup.json';
  const backup=join(folder,backupName);
  copyFileSync(source,backup);
  uploadOrExisting(tag,backup,backupName);
  if(sha(download(tag,backupName,check))!==sha(source))
   throw Error('orphan_backup_readback_mismatch');
  assets=listing();
  if(assets.some(x=>x.name===archiveName))return;
  const current=assets.find(x=>x.name===sidecarName);
  if(!current)return;
  if(current.id!==original.id||!Number.isSafeInteger(current.id))
   throw Error('orphan_sidecar_changed_during_repair');
  const deletion=gh(['api','--method','DELETE',
   'repos/'+REPO+'/releases/assets/'+current.id]);
  if(!deletion.ok&&names(tag)?.has(sidecarName))
   throw Error('orphan_sidecar_cleanup_denied');
  console.log('PRIVATE_ORPHAN_MANIFEST_BACKUP_VERIFIED');
 }finally{rmSync(folder,{recursive:true,force:true});rmSync(check,{recursive:true,force:true});}
}
async function capturePart(tag,job,capture){
 const dir=temp();
 try{
  // Transient source anchor/slot failures warrant a fresh SDK browser
  // session, not a fabricated successful window or a whole-game restart.
  for(let attempt=0;;attempt++){
   try{await capture(job,dir);break;}
   catch(e){
    const recoverable=['sdk_session_url_missing','uncovered_window','sdk_initialization_failed']
      .includes(e?.message);
    if(!recoverable||attempt>=2)throw e;
    // Another authorised worker may have saved the missing exact part.
    const base='sdk-part-'+String(job.part).padStart(2,'0');
    if(names(tag)?.has(base+'.tar.gz')&&names(tag)?.has(base+'.json')){
     const check=temp();
     try{return validatedPart(tag,job,check);}
     finally{rmSync(check,{recursive:true,force:true});}
    }
    console.log('PRIVATE_SDK_TRANSIENT_CHECKPOINT_RETRY',job.part,attempt+1);
    await new Promise(resolve=>setTimeout(resolve,1500*(attempt+1)));
   }
  }
  const source=JSON.parse(readFileSync(join(dir,'manifest.json'),'utf8'));
  summarize([job],[source]);
  const base='sdk-part-'+String(job.part).padStart(2,'0');
  const archive=join(dir,base+'.tar.gz'),sidecar=join(dir,base+'.json');
  copyFileSync(join(dir,'checkpoint.tar.gz'),archive);
  writeFileSync(sidecar,JSON.stringify({...source,archive_sha256:sha(archive)})+'\n');
  if(readFileSync(archive).length>32*1024*1024)throw Error('checkpoint_too_large');
  // Another public worker may reach the same part first. Reuse its archive
  // rather than overwrite it or bind a sidecar to a different local tarball.
  uploadOrExisting(tag,archive,base+'.tar.gz');
  if(!names(tag)?.has(base+'.json'))repairArchiveOnly(tag,job);
  const check=temp();
  try{return validatedPart(tag,job,check);}
  finally{rmSync(check,{recursive:true,force:true});}
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
  if(!pair[0]&&pair[1]){
   repairOrphanManifest(tag,job);
   const revised=names(tag);
   pair[0]=revised.has(base+'.tar.gz');
   pair[1]=revised.has(base+'.json');
  }
  const dir=temp();
  try{reports.push(pair[0]?validatedPart(tag,job,dir):await capturePart(tag,job,capture));}
  finally{rmSync(dir,{recursive:true,force:true});}
  // Release assets are the durable per-part state. Do not rewrite the shared
  // private season index for each of the 13 SHA readbacks.
  index.games[game.id]={status:'partial',last_checkpoint:job.part,last_attempt:new Date().toISOString()};
  if(!pair[0] && ++newParts>=partLimit && job.part<plan.parts.length-1){
   writeIndex(index);
   console.log('PRIVATE_GAME_PARTIAL_SHA_READBACK');
   return;
  }
 }
 const sum=summarize(plan.parts,reports);
 if(sum.windows!==plan.windows||plan.windows!==3720||plan.parts.length!==13)
  throw Error('full_game_coverage_failed');
 const coverage=diagnoseTrackingCoverage(plan.parts,reports);
 const hasSufficientObservations=sum.players>100&&sum.ball>50;
 const done={schema:'gamepulse-fullgame-manifest.v1',game_id:game.id,
  tipoff_utc:new Date(game.start).toISOString(),planned_start_ms:plan.begin,
  planned_end_exclusive_ms:plan.end,expected_windows:plan.windows,
  successful_windows:sum.windows,parts:plan.parts.length,
  sum_frames_with_players:sum.players,sum_frames_with_ball:sum.ball,
  empty_windows:sum.empty,data_class:'observed; no missing coordinates imputed',
  tracking_coverage_qa:coverage,
  acceptance:!hasSufficientObservations?'complete_with_missingness_warning':
   coverage.suspicious_parts.length?'complete_with_tracking_gaps':'complete_with_QA',
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
async function captureElapsedPriority(capture){
 if(process.env.GITHUB_EVENT_NAME!=='schedule')return;
 const id=process.env.GAMEPULSE_PRIORITY_ID;
 const start=Date.parse(process.env.GAMEPULSE_PRIORITY_TIPOFF||'');
 const now=Date.now();
 if(!Number.isSafeInteger(start)||now<start||now>=start+24*3600000)return;
 const jobs=planGame({id,start}).parts;
 const tag='gamepulse-sdk-'+id,existing=names(tag);
 if(!existing)return;
 let processed=0;
 for(const job of jobs){
  if(job.start_ms+job.count*5000+600000>now)break;
  const base='sdk-part-'+String(job.part).padStart(2,'0');
  if(existing.has(base+'.tar.gz')&&existing.has(base+'.json'))continue;
  if(existing.has(base+'.json')&&!existing.has(base+'.tar.gz'))throw Error('priority_orphan_sidecar');
  if(existing.has(base+'.tar.gz'))repairArchiveOnly(tag,job);
  else await capturePart(tag,job,capture);
  console.log('PRIVATE_PRIORITY_LIVE_PART_SHA_READBACK',job.part);
  if(++processed>=2)break;
 }
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

async function requireOfficialFinal(gameId){
 for(let attempt=0;attempt<3;attempt++){
  try{
   const response=await fetch('https://cdn.nba.com/static/json/liveData/boxscore/boxscore_'+gameId+'.json',{
    headers:{'Accept':'application/json','Referer':'https://www.nba.com/'},
    signal:AbortSignal.timeout(9000)});
   if(response.ok){
    const body=await response.json();
    const game=body?.game;
    if(String(game?.gameId)===gameId&&String(game?.gameStatus)==='3')return;
   }
  }catch{}
  try{if((await schedule()).some(g=>g.id===gameId))return;}catch{}
  if(attempt<2)await new Promise(done=>setTimeout(done,2000));
 }
 throw Error('official_final_not_verified');
}
function pilotGame(){
 const tags=JSON.parse(call(['release','list','--limit','100','--json','tagName']));
 const matches=tags.filter(x=>typeof x.tagName==='string'&&
  x.tagName.startsWith('gamepulse-sdk-github-acceptance-'));
 if(matches.length!==1)throw Error('private_pilot_assignment_ambiguous');
 const dir=temp();
 try{
  const manifest=JSON.parse(readFileSync(download(matches[0].tagName,'sdk-part-00.json',dir),'utf8'));
  const game={id:manifest.game_id,start:manifest.start_ms+600000};
  planGame(game);
  if(manifest.successful_windows!==300||manifest.frames_with_players<1)
   throw Error('private_pilot_assignment_invalid');
  return game;
 }finally{rmSync(dir,{recursive:true,force:true});}
}

export function assertContext(env){
 if(env.GITHUB_REPOSITORY!==PUBLIC||env.GITHUB_REF!=='refs/heads/main'||
    !['workflow_dispatch','push','schedule'].includes(env.GITHUB_EVENT_NAME)||
    (env.GITHUB_EVENT_NAME==='push'&&env.GAMEPULSE_FULLGAME_PILOT!=='true'&&env.GAMEPULSE_PRIORITY_FANOUT!=='true'&&env.GAMEPULSE_PRIORITY_FINALIZE!=='true'&&env.GAMEPULSE_PRODUCTION_ENABLED!=='true')||
    (env.GITHUB_EVENT_NAME==='schedule'&&
     (env.GAMEPULSE_PRODUCTION_ENABLED!=='true'||
      (env.GAMEPULSE_FULLGAME_PILOT==='true'&&env.GAMEPULSE_PILOT_FINALIZE!=='true')))||
    (env.GITHUB_EVENT_NAME==='workflow_dispatch'&&env.DRY_RUN!=='true'&&
     env.GAMEPULSE_PRODUCTION_ENABLED!=='true')||
    typeof env.GH_TOKEN!=='string'||
    env.GH_TOKEN.length<30)
  throw Error('unauthorized_private_collection');
}
export async function run(){
 assertContext({...process.env,GH_TOKEN:TOKEN});
 delete process.env.GH_TOKEN;
 // All third-party imports occur only after GH_TOKEN leaves process.env.
 const {capture}=await import('./capture.mjs');
 if(process.env.GAMEPULSE_PRIORITY_FANOUT==='true'){
  if(PILOT||process.env.GITHUB_EVENT_NAME!=='push')throw Error('priority_context_invalid');
  const game={id:process.env.GAMEPULSE_PRIORITY_ID,start:Date.parse(process.env.GAMEPULSE_PRIORITY_TIPOFF||'')};
  const plan=planGame(game),part=Number(process.env.GAMEPULSE_PRIORITY_PART);
  if(!Number.isSafeInteger(part)||part<0||part>12)throw Error('invalid_priority_part');
  const job=plan.parts[part];
  // Once the official NBA schedule marks the game final, every future time
  // window is postgame and can be queried immediately. Never infer empty slots:
  // capture() still requires an actual successful SDK response for every slot.
  if(process.env.GAMEPULSE_FINAL_FASTLANE==='true'){
   await requireOfficialFinal(game.id);
  }else{
   const remaining=job.start_ms+job.count*5000+10*60000-Date.now();
   if(remaining>40*60000)throw Error('priority_window_not_yet_observed');
   if(remaining>0)await new Promise(done=>setTimeout(done,remaining));
  }
  if(Date.now()>game.start+7*24*3600000)throw Error('priority_assignment_expired');
  const tag='gamepulse-sdk-'+game.id;
  ensure(tag);
  const existing=names(tag),base='sdk-part-'+String(part).padStart(2,'0');
  if(!existing)throw Error('private_release_missing');
  const archive=existing.has(base+'.tar.gz'),manifest=existing.has(base+'.json');
  if(manifest&&!archive)repairOrphanManifest(tag,job);
  const current=names(tag),hasArchive=current.has(base+'.tar.gz'),
   hasManifest=current.has(base+'.json');
  if(hasArchive&&!hasManifest)repairArchiveOnly(tag,job);
  if(hasArchive){
   const dir=temp();
   try{validatedPart(tag,job,dir);}finally{rmSync(dir,{recursive:true,force:true});}
  }else await capturePart(tag,job,capture);
  console.log('PRIVATE_PRIORITY_PART_SHA_READBACK_CERTIFIED');
  return;
 }
 if(process.env.GAMEPULSE_PRIORITY_FINALIZE==='true'){
  if(PILOT||!['push','schedule'].includes(process.env.GITHUB_EVENT_NAME))throw Error('priority_context_invalid');
  const game={id:process.env.GAMEPULSE_PRIORITY_ID,
   start:Date.parse(process.env.GAMEPULSE_PRIORITY_TIPOFF||'')};
  planGame(game);
  if(process.env.GAMEPULSE_FINAL_FASTLANE==='true'){
   await requireOfficialFinal(game.id);
  }else if(Date.now()<game.start+315*60000)throw Error('priority_fullgame_not_ready');
  if(Date.now()>game.start+7*24*3600000)throw Error('priority_assignment_expired');
  const index=readIndex();
  await archiveGame(game,index,capture);
  if(index.games[game.id]?.status!=='complete')throw Error('priority_fullgame_incomplete');
  console.log('PRIVATE_PRIORITY_FULLGAME_CERTIFIED');
  return;
 }
 await captureElapsedPriority(capture);
 const priorityStart=Date.parse(process.env.GAMEPULSE_PRIORITY_TIPOFF||'');
 if(process.env.GITHUB_EVENT_NAME==='schedule'&&Number.isFinite(priorityStart)
    &&Date.now()>=priorityStart&&Date.now()<priorityStart+315*60000)return;
 const index=readIndex(),games=PILOT?[pilotGame()]:await schedule();
 if(PILOT&&index.games[games[0].id]?.status==='retry')
  index.games[games[0].id].retry_after=0;
 const due=selectDue(games,index,Date.now(),1,process.env.GAMEPULSE_PRIORITY_ID||null);
 console.log('PRIVATE_SEASON_DUE_COUNT',due.length);
 if(process.env.DRY_RUN==='true')return;
 for(const game of due){
  try{await archiveGame(game,index,capture);}
  catch(e){
   const reason=/^[a-z_]+$/.test(e?.message||'')?e.message:'capture_or_archive_failed';
   index.games[game.id]={status:'retry',retry_after:Date.now()+6*3600000,
    last_attempt:new Date().toISOString()};
   writeIndex(index);
   console.error('PRIVATE_SEASON_RETRY_REQUIRED',reason);
   process.exitCode=2;
  }
 }
}
if(process.argv[1]?.endsWith('season_private_release.mjs'))
 run().catch(e=>{
  const reason=/^[a-z_]+$/.test(e?.message||'')?e.message:'collector_failed';
  console.error('PRIVATE_SEASON_STOPPED',reason);process.exitCode=2;
 });
