/** NBA licensed SDK companion source presence test. App receives only
 * account/program, not a token. No direct authenticated URL replay, no
 * request interception, no access-control bypass. Only SDK-origin response
 * bodies can be preserved privately; public output contains aggregate counts.
 */
import puppeteer from 'puppeteer-core';
import {build} from 'esbuild';
import {createServer} from 'node:http';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const gid=process.env.NBA_GAME_ID||'';
const start=Date.parse(process.env.NBA_TIPOFF_UTC||'');
const dir=process.env.IGP_PRIVATE_CAPTURE_DIR;
if(!/^00226\d{5}$/.test(gid)||!Number.isFinite(start)||!dir)throw Error('invalid_companion_probe_scope');
const programId='companion-'+gid, origin='nba-cdn.cloud.easelive.tv';
const sourceDir=mkdtempSync(join(tmpdir(),'igp-licensed-companion-'));
let browser,server;
function chrome(){for(const n of ['google-chrome','google-chrome-stable','chromium']){
 try{return execFileSync('which',[n],{encoding:'utf8'}).trim()}catch{}
}throw Error('chromium_missing')}
const result={schema:'igp.licensed-sdk-companion-source-readback.v1',
 game_id:gid, sdk_client:'@ease-live/ease-live-bridge-web',source_mode:'SDK_INITIALIZED_CLIENT_NO_URL_REPLAY',
 status:'NOT_AVAILABLE',initialization_result:null,observed_200_event_responses:0,
 observed_200_slot_responses:0,other_status_counts:{},original_total_event_objects:0,
 shot_detail_objects:0,original_body_bytes:0,original_body_sha256:null,
 raw_29joint_pose_60hz_observed:false,authentication_bypass_attempted:false};
try{
 const output=join(sourceDir,'bundle.js');
 await build({entryPoints:[new URL('./browser.js',import.meta.url).pathname],bundle:true,
 platform:'browser',format:'iife',outfile:output,logLevel:'silent'});
 server=createServer((req,res)=>{
  if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html'}).end('<!doctype html><html><body><div id="overlay"></div><script src="/bundle.js"></script></body></html>');return}
  if(req.url==='/bundle.js'){res.writeHead(200,{'Content-Type':'application/javascript'}).end(readFileSync(output));return}
  res.writeHead(404).end();
 });
 await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
 browser=await puppeteer.launch({headless:true,executablePath:chrome(),
 args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage();
 const seen=new Set(),pending=new Set(),candidateBodies=[];
 page.on('response',response=>{
  const job=(async()=>{
   let url;try{url=new URL(response.url())}catch{return}
   if(url.hostname!==origin||!url.pathname.includes('/'+programId+'/'))return;
   const hasEvents=url.pathname.endsWith('/events');
   const hasSlots=url.pathname.endsWith('/events/slot');
   if(!hasEvents&&!hasSlots)return;
   if(response.status()!==200){
    const k=String(response.status());result.other_status_counts[k]=(result.other_status_counts[k]||0)+1;return
   }
   try{
    const buffer=await response.buffer();
    if(buffer.length>12_000_000)return;
    const raw=JSON.parse(buffer.toString('utf8'));
    const events=Array.isArray(raw)?raw:(Array.isArray(raw?.events)?raw.events:null);
    if(!events||!events.length)return;
    if(hasEvents)result.observed_200_event_responses++;
    if(hasSlots)result.observed_200_slot_responses++;
    const key=Buffer.from(buffer).toString('base64url').slice(0,48);
    if(seen.has(key))return;seen.add(key);
    const count=events.filter(e=>JSON.stringify(e).includes('ShotDetails#show')).length;
    result.original_total_event_objects+=events.length;
    result.shot_detail_objects+=count;
    candidateBodies.push({buffer,full:hasEvents,shots:count,events:events.length});
   }catch{}
  })();
  pending.add(job);job.finally(()=>pending.delete(job));
 });
 await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'domcontentloaded',timeout:15000});
 await page.waitForFunction(()=>typeof window.ephemeralFeed?.initialize==='function',{timeout:12000});
 result.initialization_result=await page.evaluate(({programId})=>
   window.ephemeralFeed.initialize({accountId:'nba',programId}),{programId});
 if(result.initialization_result==='ready'){
   for(const minutes of [8,24,38,54,75,98,120,145,160]){
     await page.evaluate(t=>window.ephemeralFeed.seek(t),start+minutes*60_000);
     await new Promise(resolve=>setTimeout(resolve,750));
   }
   await new Promise(resolve=>setTimeout(resolve,3200));
 }
 await Promise.allSettled([...pending]);
 const winners=candidateBodies.filter(x=>x.shots>0).sort((a,b)=>
      (b.full?1:0)-(a.full?1:0)||b.shots-a.shots||b.buffer.length-a.buffer.length);
 if(winners.length){
   const best=winners[0];
   // This is the *observed* original JSON returned by the authorized SDK.
   // Do not consolidate/claim a full game if only an SDK slot is returned.
   writeFileSync(join(dir,'companion_original_sdk_response.json'),best.buffer);
   const {createHash}=await import('node:crypto');
   result.original_body_sha256=createHash('sha256').update(best.buffer).digest('hex');
   result.original_body_bytes=best.buffer.length;
   result.original_body_event_count=best.events;
   result.original_body_shot_details_count=best.shots;
   result.full_original_events_endpoint_observed=best.full;
   result.status=best.full?'FULL_EVENT_RESPONSE_OBSERVED':'ORIGINAL_PARTIAL_SDK_EVENT_SLOT_OBSERVED';
 } else result.status=result.initialization_result==='ready'?
    'SDK_PROGRAM_READY_BUT_NO_SHOTDETAIL_RESPONSE':'SDK_PROGRAM_NOT_READY';
 await page.close();
}finally{
 if(browser)await browser.close();
 if(server)await new Promise(ok=>server.close(ok));
 rmSync(sourceDir,{recursive:true,force:true});
 writeFileSync(join(dir,'companion_probe_receipt.json'),JSON.stringify(result,null,2)+'\n');
 console.log('IGP_COMPANION_AUTHORIZED_SDK_SHOT_SOURCE_PROBE',JSON.stringify(result));
}
