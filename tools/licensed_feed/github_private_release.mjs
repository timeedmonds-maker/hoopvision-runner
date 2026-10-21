/**
 * GitHub-only, private 104 Release destination for licensed SDK observations.
 * Never publishes raw records, tracking payloads, archive paths or token values.
 * No GCP, private source checkout, Actions artifacts, GitHub cache or public Releases.
 */
import {spawnSync} from 'node:child_process';
import {copyFileSync,existsSync,mkdirSync,mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {capture,checkJob} from './capture.mjs';

export const PRIVATE_REPO='timeedmonds-maker/104';
const PUBLIC_REPO='timeedmonds-maker/hoopvision-runner';
const TEST_GAME='0022600002';
const TEST_TIPOFF=Date.parse('2026-10-20T23:00:00Z');
const LIMIT_BYTES=32*1024*1024;
const hash=path=>createHash('sha256').update(readFileSync(path)).digest('hex');

export function pilotJob(){
 const ms=Math.floor((TEST_TIPOFF-10*60000)/5000)*5000;
 return checkJob({game_id:TEST_GAME,account_id:'nba',
   program_id:'companion-'+TEST_GAME+'-positions',part:0,start_ms:ms,count:300});
}
export function assertScopedContext(env){
 if(env.GITHUB_REPOSITORY!==PUBLIC_REPO || env.GITHUB_REF!=='refs/heads/main' ||
    env.GITHUB_EVENT_NAME!=='workflow_dispatch')throw Error('unauthorized_execution_context');
 if(typeof env.GH_TOKEN!=='string'||env.GH_TOKEN.length<30)
   throw Error('private_token_unavailable');
}
export function privateTag(job){
 checkJob(job);
 if(job.game_id!==TEST_GAME||job.part!==0||job.count!==300||
    job.start_ms!==pilotJob().start_ms)throw Error('unexpected_pilot_job');
 return 'gamepulse-sdk-github-acceptance-'+job.game_id;
}
export function shellGh(args){
 const result=spawnSync('gh',args,{encoding:'utf8',
   env:process.env,stdio:['ignore','pipe','pipe'],timeout:120000,maxBuffer:1024*1024});
 return {ok:result.status===0,stdout:result.stdout||''};
}
export function verifyAndStore(job,folder,execGh=shellGh){
 const tag=privateTag(job);
 const archive=join(folder,'checkpoint.tar.gz'),manifest=join(folder,'manifest.json');
 if(!existsSync(archive)||!existsSync(manifest))throw Error('capture_files_missing');
 const data=JSON.parse(readFileSync(manifest,'utf8'));
 if(data.game_id!==job.game_id||data.part!==job.part||
    data.start_ms!==job.start_ms||data.successful_windows!==300||
    data.unique_keyframes<1||data.frames_with_players<1)throw Error('capture_qa_failed');
 if(readFileSync(archive).length>LIMIT_BYTES)throw Error('archive_oversized');
 const names=['sdk-part-00.tar.gz','sdk-part-00.json'];
 copyFileSync(archive,join(folder,names[0]));
 copyFileSync(manifest,join(folder,names[1]));
 let response=execGh(['release','view',tag,'--repo',PRIVATE_REPO,'--json','assets']);
 if(!response.ok){
   const created=execGh(['release','create',tag,'--repo',PRIVATE_REPO,
      '--target','main','--title',tag,
      '--notes','Private licensed-feed acceptance test; tracking never published publicly']);
   if(!created.ok)throw Error('private_release_create_failed');
   response=execGh(['release','view',tag,'--repo',PRIVATE_REPO,'--json','assets']);
 }
 if(!response.ok)throw Error('private_release_read_failed');
 let assets;
 try{assets=JSON.parse(response.stdout).assets||[];}catch{throw Error('private_asset_listing_invalid');}
 if(!Array.isArray(assets))throw Error('private_asset_listing_invalid');
 const existing=new Set(assets.map(a=>a.name));
 for(const name of names){
   if(!existing.has(name)){
     if(!execGh(['release','upload',tag,join(folder,name),'--repo',PRIVATE_REPO]).ok)
       throw Error('private_upload_failed');
   }
 }
 const verificationDir=mkdtempSync(join(tmpdir(),'private-only-readback-'));
 try{
   for(const name of names){
     if(!execGh(['release','download',tag,'--repo',PRIVATE_REPO,
       '--pattern',name,'--dir',verificationDir]).ok)
       throw Error('private_readback_failed');
     const expected=hash(join(folder,name)),returned=hash(join(verificationDir,name));
     if(expected!==returned)throw Error('private_sha_mismatch');
   }
 }finally{
   rmSync(verificationDir,{recursive:true,force:true});
 }
 return 'PRIVATE_GITHUB_SHA_READBACK_CERTIFIED';
}
export async function runPilot(){
 assertScopedContext(process.env);
 const job=pilotJob();
 const directory=mkdtempSync(join(tmpdir(),'gp-private-only-'));
 try{
   await capture(job,directory);
   const certified=verifyAndStore(job,directory);
   console.log(certified);
 }catch{
   console.error('PRIVATE_GITHUB_PILOT_FAILED');
   process.exitCode=2;
 }finally{
   rmSync(directory,{recursive:true,force:true});
 }
}
if(process.argv[1]?.endsWith('github_private_release.mjs'))await runPilot();
