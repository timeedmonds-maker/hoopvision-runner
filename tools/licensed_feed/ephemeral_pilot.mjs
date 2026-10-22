/* Single licensed SDK smoke; zero public persistence beyond temporary runner files.
   Game selected from public schedule, never logged, uploaded, or retained. */
import {capture} from './capture.mjs';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

// One-off public NBA opening-game identifier: not private bridge metadata.
// Do not print identifiers or retain any downloaded tracking rows.
const publicHistoricalTest={id:'0022600002',ms:Date.parse('2026-10-20T23:00:00Z')};
const job={
 game_id:publicHistoricalTest.id,account_id:'nba',
 program_id:'companion-'+publicHistoricalTest.id+'-positions',
 part:0,start_ms:Math.floor((publicHistoricalTest.ms-10*60000)/5000)*5000,count:300
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
