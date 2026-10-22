import {test} from 'node:test';
import assert from 'node:assert/strict';
import {planGame,parseSchedule,selectDue,summarize,priorityId} from './season_core.mjs';
import {assertContext} from './season_private_release.mjs';

const id='0022600002';
const start=Date.parse('2026-10-20T23:00:00Z');
test('full game has 3720 unique five-second windows in 13 chunks',()=>{
 const plan=planGame({id,start});
 assert.equal(plan.windows,3720);
 assert.equal(plan.parts.length,13);
 assert.deepEqual(plan.parts.map(x=>x.count),[...Array(12).fill(300),120]);
 assert.equal(plan.parts[0].start_ms,start-600000);
 for(let i=1;i<plan.parts.length;i++)
  assert.equal(plan.parts[i].start_ms,plan.parts[i-1].start_ms+plan.parts[i-1].count*5000);
 assert.equal(plan.parts.at(-1).start_ms+plan.parts.at(-1).count*5000,plan.end);
});
test('both official schedule formats select only final 2026-27 supported games',()=>{
 const modern={leagueSchedule:{gameDates:[{games:[
  {gameId:id,gameStatus:3,gameDateTimeUTC:new Date(start).toISOString()},
  {gameId:'0022600003',gameStatus:1,gameDateTimeUTC:new Date(start).toISOString()},
  {gameId:'0032600002',gameStatus:3,gameDateTimeUTC:new Date(start).toISOString()}]}]}};
 const legacy={data:{lscd:[{mscd:{g:[{gid:id,stt:'Final',
  gdtutc:'2026-10-20',utctm:'23:00'},{gid:'0022600003',stt:'Preview',
  gdtutc:'2026-10-20',utctm:'23:00'}]}}]}};
 assert.deepEqual(parseSchedule(modern,'modern'),[{id,start},{id:'0032600002',start}]);
 assert.deepEqual(parseSchedule(legacy,'legacy'),[{id,start}]);
 assert.throws(()=>parseSchedule({},'modern'));
});
test('complete games and cooldown are skipped while partial resumes',()=>{
 const games=[{id,start},{id:'0022600003',start:start+3600000}];
 assert.deepEqual(selectDue(games,{games:{[id]:{status:'complete'}}},start+36000000),[games[1]]);
 assert.deepEqual(selectDue(games,{games:{[id]:{status:'partial'},'0022600003':{
  status:'retry',retry_after:start+40000000}}},start+36000000),[games[0]]);
 assert.equal(selectDue(games,{games:{}},start+315*60000).length,0);
});
test('remote manifests must reconcile every assigned slot and remain observed',()=>{
 const p=planGame({id,start});
 const manifests=p.parts.map(j=>({game_id:j.game_id,part:j.part,start_ms:j.start_ms,
  successful_windows:j.count,frames_with_players:100,frames_with_ball:90,
  empty_windows:0,observed:true,imputed:false}));
 assert.equal(summarize(p.parts,manifests).windows,3720);
 assert.throws(()=>summarize(p.parts,manifests.slice(1)));
 assert.throws(()=>summarize(p.parts,[{...manifests[0],successful_windows:299},...manifests.slice(1)]));
 assert.throws(()=>summarize(p.parts,[{...manifests[0],imputed:true},...manifests.slice(1)]));
});
test('private token is usable only on trusted main, with isolated push pilot',()=>{
 const env={GITHUB_REPOSITORY:'timeedmonds-maker/hoopvision-runner',
  GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'workflow_dispatch',DRY_RUN:'true',GH_TOKEN:'x'.repeat(35)};
 assert.doesNotThrow(()=>assertContext(env));
 assert.doesNotThrow(()=>assertContext({...env,GITHUB_EVENT_NAME:'push',GAMEPULSE_FULLGAME_PILOT:'true'}));
 assert.doesNotThrow(()=>assertContext({...env,GITHUB_EVENT_NAME:'schedule',GAMEPULSE_PRODUCTION_ENABLED:'true'}));
 assert.doesNotThrow(()=>assertContext({...env,GITHUB_EVENT_NAME:'schedule',
  GAMEPULSE_PRODUCTION_ENABLED:'true',GAMEPULSE_FULLGAME_PILOT:'true',GAMEPULSE_PILOT_FINALIZE:'true'}));
 for(const bad of [{...env,DRY_RUN:'false'},{...env,GITHUB_EVENT_NAME:'push'},
  {...env,GITHUB_EVENT_NAME:'schedule'},
  {...env,GITHUB_EVENT_NAME:'schedule',GAMEPULSE_FULLGAME_PILOT:'true'},
  {...env,GH_TOKEN:''},{...env,GITHUB_REF:'refs/heads/untrusted'},
  {...env,GITHUB_EVENT_NAME:'pull_request'},{...env,GITHUB_REPOSITORY:'other/repo'}])
  assert.throws(()=>assertContext(bad));
});

test('priority sorts an eligible assigned game ahead of backlog',()=>{
 const older={id:'0022600001',start:start-3600000};
 const preferred={id:'0022600091',start};
 const now=start+8*3600000;
 assert.deepEqual(selectDue([older,preferred],{games:{}},now,1,preferred.id),[preferred]);
 assert.deepEqual(selectDue([older,preferred],{games:{[preferred.id]:{status:'complete'}}},now,1,preferred.id),[older]);
 assert.equal(priorityId({schema:'gamepulse-priority.v1',game_id:preferred.id,
  tipoff_utc:new Date(start).toISOString(),
  expires_at_utc:new Date(start+24*3600000).toISOString()},now),preferred.id);
});

test('bounded main-only fanout context rejects untrusted contexts',()=>{
 const env={GITHUB_REPOSITORY:'timeedmonds-maker/hoopvision-runner',
  GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'push',
  GAMEPULSE_PRIORITY_FANOUT:'true',GH_TOKEN:'x'.repeat(35)};
 assert.doesNotThrow(()=>assertContext(env));
 assert.throws(()=>assertContext({...env,GITHUB_REF:'refs/heads/untrusted'}));
 assert.throws(()=>assertContext({...env,GITHUB_EVENT_NAME:'pull_request'}));
});

test('full-game priority certification is authorised only on trusted main',()=>{
 const trusted={GITHUB_REPOSITORY:'timeedmonds-maker/hoopvision-runner',
  GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'push',
  GAMEPULSE_PRIORITY_FINALIZE:'true',GH_TOKEN:'x'.repeat(35)};
 assert.doesNotThrow(()=>assertContext(trusted));
 assert.throws(()=>assertContext({...trusted,GITHUB_REF:'refs/heads/feature'}));
 assert.throws(()=>assertContext({...trusted,GITHUB_EVENT_NAME:'pull_request'}));
 assert.throws(()=>assertContext({...trusted,GH_TOKEN:''}));
});
