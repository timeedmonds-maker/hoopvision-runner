/** Public free CPU, private Release writes; one isolated game per job. */
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {copyFileSync,mkdtempSync,rmSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {planGame} from './season_core.mjs';
const PRIV='timeedmonds-maker/104',PUB='timeedmonds-maker/hoopvision-runner';
const TOKEN=process.env.GH_TOKEN;
const sha=b=>createHash('sha256').update(b).digest('hex');
const pause=ms=>new Promise(ok=>setTimeout(ok,ms));
function gh(args) {
 const r=spawnSync('gh',args,{encoding:'utf8',timeout:110000,maxBuffer:2*1024*1024,
  env:{...process.env,GH_TOKEN:TOKEN}});
 if(r.status!==0)throw Error('private_operation_failed');
 return r.stdout;
}
function getAssets(tag) {
 try{
  const obj=JSON.parse(gh(['api','repos/'+PRIV+'/releases/tags/'+tag]));
  return new Map((obj.assets||[]).map(a=>[a.name,a]));
 }catch(e){if(e.message!=='private_operation_failed')throw e;return null;}
}
function ensure(tag) {
 if(getAssets(tag)!==null)return;
 try{gh(['release','create',tag,'--repo',PRIV,'--title',tag,
  '--notes','Original observed live Game Pulse checkpoints, private only','--latest=false']);}
 catch(e){if(getAssets(tag)===null)throw e;}
}
export function eligibleSlot(start,now,slotsAlready=new Set()) {
 const full=planGame({id:'0022600001',start});
 for(let i=0;i<310;i++){
  const from=full.begin+i*60000;
  if(from>=full.end)return null;
  if(now<from+Math.min(60000,full.end-from)+30000)return null;
  if(!slotsAlready.has(from))return i;
 }
 return null;
}
async function main() {
 const id=process.env.GAMEPULSE_LIVE_ID;
 const start=Date.parse(process.env.GAMEPULSE_LIVE_TIPOFF||'');
 if(process.env.GITHUB_REPOSITORY!==PUB||
    process.env.GITHUB_REF!=='refs/heads/main'||
    !['schedule','push','workflow_dispatch'].includes(process.env.GITHUB_EVENT_NAME)||
    !/^00226\d{5}$/.test(id||'')||!Number.isSafeInteger(start)||
    !TOKEN||TOKEN.length<30)throw Error('unauthorized_live_collection');
 delete process.env.GH_TOKEN;
 const {capture}=await import('./capture.mjs');
 const tag='gamepulse-live-sdk-'+id;
 ensure(tag);
 const deadline=Date.now()+215000;
 let collected=0,failed=0;
 while(Date.now()<deadline && collected<8){
  const assets=getAssets(tag)||new Map();
  const archived=new Set([...assets.keys()].filter(n=>/^live-\d{13}\.tar\.gz$/.test(n)&&
    assets.has(n.replace('.tar.gz','.json')))
    .map(n=>Number(n.match(/^live-(\d{13})/)[1])));
  const slot=eligibleSlot(start,Date.now(),archived);
  if(slot===null){await pause(12000);continue;}
  const plan=planGame({id,start}),from=plan.begin+slot*60000;
  const job={game_id:id,account_id:'nba',program_id:'companion-'+id+'-positions',
   part:Math.floor((from-plan.begin)/(300*5000)),start_ms:from,
   count:Math.min(12,(plan.end-from)/5000)};
  const base='live-'+job.start_ms,dir=mkdtempSync(join(tmpdir(),'gp-live-'));
  try{
   await capture(job,dir);
   const archive=join(dir,base+'.tar.gz'),side=join(dir,base+'.json');
   copyFileSync(join(dir,'checkpoint.tar.gz'),archive);
   const m=JSON.parse(readFileSync(join(dir,'manifest.json'),'utf8'));
   if(m.successful_windows!==job.count||m.game_id!==id||
      m.observed!==true||m.imputed!==false)throw Error('source_coverage_not_verified');
   const digest=sha(readFileSync(archive));
   writeFileSync(side,JSON.stringify({...m,archive_sha256:digest})+'\n');
   gh(['release','upload',tag,archive,side,'--repo',PRIV]);
   const after=getAssets(tag);
   if(after?.get(base+'.tar.gz')?.digest!=='sha256:'+digest||
      !after.has(base+'.json'))throw Error('private_release_sha_not_verified');
   collected++;failed=0;
   console.log('PRIVATE_LIVE_CHECKPOINT_SHA_VERIFIED',collected,job.count);
  }catch(e){
   failed++;
   console.log('PRIVATE_LIVE_SOURCE_RETRY_REQUIRED',failed,
    /^[a-z_]+$/.test(e.message||'')?e.message:'source_unavailable');
   if(failed>=2)break;
   await pause(20000);
  }finally{rmSync(dir,{recursive:true,force:true});}
 }
 console.log('LIVE_PRIVATE_CAPTURE_CYCLE_ENDED',collected,failed);
 if(failed && !collected)process.exitCode=2;
}
if(process.argv[1]?.endsWith('live_capture_cycle.mjs')){
 main().catch(e=>{console.error(/^[a-z_]+$/.test(e.message||'')?e.message:'live_worker_failed');process.exitCode=2;});
}
