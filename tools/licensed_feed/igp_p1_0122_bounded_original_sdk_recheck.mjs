/** P1 0122 original-only 2-part SDK recapture. NEVER overwrites original SHA archives.
 * Explicit known game only, original source SDK client only, private release+QA.
 * This is a candidate source readback, NOT a model or tracking coverage claim.
 */
import {spawnSync} from 'node:child_process';
import {mkdtempSync,readFileSync,writeFileSync,copyFileSync,mkdirSync,rmSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {planGame} from './season_core.mjs';

const REPO='timeedmonds-maker/104';
const GAME='0022600122';
const START=Date.parse('2026-10-26T23:30:00.000Z');
const SOURCE='gamepulse-sdk-'+GAME;
const RECOVERY='gamepulse-sdk-recovery-'+GAME+'-20261030-P1';
const TOKEN=process.env.GH_TOKEN||'';
const GUARD=process.env.GAMEPULSE_P1_0122_SDK_RECHECK==='approved_source_only';
const CHECK=process.env.GITHUB_REPOSITORY==='timeedmonds-maker/hoopvision-runner' &&
 process.env.GITHUB_REF==='refs/heads/main' && process.env.GITHUB_EVENT_NAME==='push';
if(!GUARD||!CHECK||TOKEN.length<30)throw Error('source_recheck_not_authorized');
if(Date.now()>START+7*24*3600000)throw Error('source_recheck_window_expired');
delete process.env.GH_TOKEN;
const stamp=()=>mkdtempSync(join(tmpdir(),'igp0122-p1-'));
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const fail=m=>{throw Error(m)};
function gh(args){
 const a=spawnSync('gh',args,{encoding:'utf8',timeout:120000,maxBuffer:4*1024*1024,
 stdio:['ignore','pipe','pipe'],env:{...process.env,GH_TOKEN:TOKEN}});
 if(a.status!==0)fail('PRIVATE_GH_SOURCE_OPERATION_FAILED');
 return a.stdout||'';
}
function names(tag){
 const a=spawnSync('gh',['release','view',tag,'--repo',REPO,'--json','assets'],
 {encoding:'utf8',timeout:120000,maxBuffer:1024*1024,env:{...process.env,GH_TOKEN:TOKEN}});
 if(a.status!==0)return null;
 return new Set(JSON.parse(a.stdout).assets.map(x=>x.name));
}
function ensure(){
 if(names(RECOVERY))return;
 gh(['release','create',RECOVERY,'--repo',REPO,'--target','main',
 '--title',RECOVERY,'--notes','Original SDK P1 0122 non-destructive recheck only; licensed assets private',
 '--latest=false']);
}
function upload(tag,local){
 gh(['release','upload',tag,local,'--repo',REPO]);
}
function download(tag,pattern,dir){
 gh(['release','download',tag,'--repo',REPO,'--pattern',pattern,'--dir',dir]);
}
const sourceDir=stamp(),scratch=stamp(),testDir=stamp();
try{
 if(!names(SOURCE))fail('KNOWN_ORIGINAL_SOURCE_RELEASE_MISSING');
 download(SOURCE,'sdk-part-*.json',sourceDir);
 const plan=planGame({id:GAME,start:START});
 if(plan.parts.length!==13)fail('INVALID_SOURCE_PLAN_PART_COUNT');
 const original=plan.parts.map(j=>{
  const path=join(sourceDir,'sdk-part-'+String(j.part).padStart(2,'0')+'.json');
  if(!existsSync(path))fail('ORIGINAL_PART_METADATA_MISSING');
  const d=JSON.parse(readFileSync(path,'utf8'));
  if(d.game_id!==GAME||d.part!==j.part||d.start_ms!==j.start_ms||
   d.successful_windows!==j.count||d.observed!==true||d.imputed!==false||
   !Number.isSafeInteger(d.frames_with_players)||!Number.isSafeInteger(d.frames_with_ball)||
   typeof d.archive_sha256!=='string')fail('ORIGINAL_PART_SOURCE_METADATA_DRIFT');
  return d;
 });
 // Only exact parts 2..7 (typical live game) qualify: select two least player-dense.
 const selected=original.filter(x=>x.part>=2&&x.part<=7)
   .sort((a,b)=>a.frames_with_players-b.frames_with_players||a.part-b.part).slice(0,2);
 if(selected.length!==2)fail('INVALID_RECHECK_PART_SELECTION');
 const {capture}=await import('./capture.mjs');
 ensure();
 const results=[];
 for(const old of selected){
  const part=old.part,job=plan.parts[part],dir=join(scratch,'part'+part);
  mkdirSync(dir,{recursive:true});
  let fresh=null,status='NO_FRESH_SOURCE',archiveSaved=false,improved=false;
  try{
   process.env.GAMEPULSE_FINAL_FASTLANE='true';
   await capture(job,dir);
   fresh=JSON.parse(readFileSync(join(dir,'manifest.json'),'utf8'));
   if(fresh.game_id!==GAME||fresh.part!==part||
      fresh.start_ms!==job.start_ms||fresh.successful_windows!==job.count||
      fresh.observed!==true||fresh.imputed!==false)fail('RECHECK_SOURCE_SCOPE_CHANGED');
   status='ORIGINAL_SDK_SOURCE_RECAPTURED';
   improved=fresh.frames_with_players>old.frames_with_players||
     (fresh.frames_with_players===old.frames_with_players &&
      fresh.frames_with_ball>old.frames_with_ball);
   if(improved){
    const local=join(dir,'p1-recovery-part-'+String(part).padStart(2,'0')+'.tar.gz');
    copyFileSync(join(dir,'checkpoint.tar.gz'),local);
    upload(RECOVERY,local);
    download(RECOVERY,'p1-recovery-part-'+String(part).padStart(2,'0')+'.tar.gz',testDir);
    if(sha(join(testDir,'p1-recovery-part-'+String(part).padStart(2,'0')+'.tar.gz'))!==sha(local))
      fail('RECHECK_ARCHIVE_PRIVATE_SHA_READBACK_FAILED');
    archiveSaved=true;
   }
  }catch(e){
    if(String(e?.message||'').startsWith('RECHECK_'))throw e;
    status='SDK_SOURCE_UNAVAILABLE_OR_CAPTURE_FAILED';
  }finally{delete process.env.GAMEPULSE_FINAL_FASTLANE;}
  results.push({
    part,original:{frames_with_players:old.frames_with_players,
      frames_with_ball:old.frames_with_ball,
      empty_windows:old.empty_windows,archive_sha256:old.archive_sha256},
    fresh:fresh?{frames_with_players:fresh.frames_with_players,
      frames_with_ball:fresh.frames_with_ball,empty_windows:fresh.empty_windows}:null,
    status,improved,archiveSaved,
    raw_original_part_unmodified:true,physical_possessions_certified:0
  });
  console.log('IGP0122_P1_SDK_RECHECK',part,status,'improved',improved);
 }
 const qa={schema:'igp.0122.p1-authorized-original-sdk-source-recheck.v1',
   game_id:GAME,source_original_tag:SOURCE,recovery_private_tag:RECOVERY,
   original_release_13_parts_preserved:true,original_parts_indexed:13,
   selected_parts:results.map(x=>x.part),rechecks:results,
   improved_parts:results.filter(x=>x.improved).length,
   source_recheck_window_before_expiry:true,original_source_unchanged:true,
   complete_ten_plus_ball_tracking_gain_not_yet_scored:true,
   physical_accuracy_certified:false};
 const receipt=join(scratch,'igp_0122_p1_recheck_receipt.json');
 writeFileSync(receipt,JSON.stringify(qa,null,2)+'\n');
 upload(RECOVERY,receipt);
 download(RECOVERY,'igp_0122_p1_recheck_receipt.json',testDir);
 if(sha(receipt)!==sha(join(testDir,'igp_0122_p1_recheck_receipt.json')))
   fail('RECHECK_PRIVATE_QA_SHA_FAILED');
 // Workflow will commit its own private QA from the private recovery release,
 // never print original player position arrays or raw event bodies.
 console.log('IGP0122_P1_TWO_PART_ORIGINAL_SOURCE_RECHECK_ACCEPTED',JSON.stringify({
  game:GAME,original_parts_immutable:13,selected_parts:qa.selected_parts,
  improved_parts:qa.improved_parts,sdk_source_read_success_count:results.filter(
   x=>x.status==='ORIGINAL_SDK_SOURCE_RECAPTURED').length,
  private_recovery_tag:RECOVERY
 }));
}finally{
 rmSync(sourceDir,{recursive:true,force:true});
 rmSync(scratch,{recursive:true,force:true});
 rmSync(testDir,{recursive:true,force:true});
}
