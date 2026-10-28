// First-party public NBA web shot-detail response discovery (NO iOS auth).
// Aggregates provider JSON field names only. No coordinates, request tokens,
// headers, payload, cookie, signed URL, per-shot identities or values printed.
import puppeteer from 'puppeteer-core';
import {execFileSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';

const pages=[
 'https://www.nba.com/game/det-vs-nyk-0022600129',
 'https://www.nba.com/inside-the-game/blueprint/0022600129'
];
const terms=/(defender.?jump|jump.?defender|release.?time|shot.?vertical|contest.?height|shot.?distance|shot.?difficulty|expected.?fg|expfieldgoalpct)/i;
function executable(){
 for(const n of ['google-chrome','google-chrome-stable','chromium']){
   try{return execFileSync('which',[n],{encoding:'utf8'}).trim()}catch{}
 }
 throw Error('chrome_missing');
}
function isNBA(host){
 return host==='nba.com'||host.endsWith('.nba.com')||
        host==='nba.net'||host.endsWith('.nba.net');
}
function displayPath(raw){
 const u=new URL(raw);
 const pieces=u.pathname.split('/').filter(Boolean).slice(0,5).map(x=>{
   if(x.length>45)return ':opaque';
   if(!/^[a-z0-9_\-\.]+$/i.test(x))return ':opaque';
   if(/^[0-9a-f]{20,}$/i.test(x))return ':opaque';
   return x;
 });
 return u.hostname+'/'+pieces.join('/');
}
function scan(node,output,depth=0,seen={n:0}){
 if(depth>13 || ++seen.n>16000 || node==null)return;
 if(Array.isArray(node)){
  for(const v of node.slice(0,4))scan(v,output,depth+1,seen);
 }else if(typeof node==='object'){
  for(const [k,v] of Object.entries(node).slice(0,150)){
    if(terms.test(k))output.add(k);
    if(typeof v==='object' && v!==null)scan(v,output,depth+1,seen);
  }
 }
}
const browser=await puppeteer.launch({headless:true,executablePath:executable(),
 args:['--no-sandbox','--disable-dev-shm-usage']});
const results=[];
try{
 for(const url of pages){
  const page=await browser.newPage(), pending=[], fields=new Set(),matches=new Set();
  let total=0,jsonCount=0,loaded=false,failed=null;
  page.on('response',response=>{
   const pendingJob=(async()=>{
    let u;
    try{u=new URL(response.url())}catch{return}
    if(!isNBA(u.hostname))return;
    total++;
    const c=(response.headers()['content-type']||'').toLowerCase();
    if(!c.includes('json'))return;
    let len=Number(response.headers()['content-length']||0);
    if(len>2_000_000)return;
    try{
      const obj=await response.json();
      jsonCount++;
      const found=new Set();
      scan(obj,found);
      for(const k of found)fields.add(k);
      if(found.size)matches.add(displayPath(response.url()));
    }catch{}
   })();
   pending.push(pendingJob);
  });
  try{
    const r=await page.goto(url,{waitUntil:'domcontentloaded',timeout:35000});
    loaded=Boolean(r&&r.status()<400);
    await new Promise(ok=>setTimeout(ok,4500));
    const html=await page.evaluate(()=>{
      const x=document.getElementById('__NEXT_DATA__');
      if(!x)return {found:false,containsDefenderJump:false,containsPreciseReference:false};
      const txt=x.textContent||'';
      return {found:true,
        containsDefenderJump:/defender.?jump/i.test(txt),
        containsPreciseReference:/0\.849/.test(txt)};
    });
    await Promise.allSettled(pending);
    results.push({page:url,loaded,html_next_data:html,total_provider_responses:total,
     parsed_json_responses:jsonCount,shot_like_JSON_field_names:[...fields].sort(),
     shot_like_public_endpoint_paths:[...matches].sort()});
  }catch(e){failed=e?.name||'BrowserError';
   results.push({page:url,loaded:false,reason:failed,total_provider_responses:total,
    parsed_json_responses:jsonCount,shot_like_JSON_field_names:[...fields].sort()});
  }finally{await page.close()}
 }
}finally{await browser.close()}
const output={schema:'IPPT_PUBLIC_NBA_WEB_APP_SHOT_RESPONSE_PATHS_ONLY_V1',
 original_native_NBA_iOS_app_not_intercepted:true,urls_without_query_strings:true,
 authenticated_endpoints_not_probed:true,source_payload_or_auth_headers_exposed:false,
 pages:results};
writeFileSync(process.argv[2]||'/tmp/nba-public-web-shot-response-schema.json',
 JSON.stringify(output,null,2)+'\n');
console.log('IPPT_PUBLIC_NBA_WEB_SHOT_DETAIL_RESPONSE_SCHEMA',JSON.stringify(output));
