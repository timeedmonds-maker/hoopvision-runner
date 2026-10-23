import assert from 'node:assert/strict';
import {test} from 'node:test';
import {eligibleSlot} from './live_capture_cycle.mjs';
const tipoff=Date.parse('2026-10-23T01:30:00Z');
test('live-first selects latest elapsed slot, not oldest backlog',()=>{
 assert.equal(eligibleSlot(tipoff,tipoff+41*60000+31000),50);
});
test('live-first resumes next newest missing slot',()=>{
 const s=new Set([tipoff+40*60000]);
 assert.equal(eligibleSlot(tipoff,tipoff+41*60000+31000,s),49);
});
test('does not request an incomplete current minute',()=>{
 assert.equal(eligibleSlot(tipoff,tipoff+31000),null);
});
test('ends once all due slots are already archived',()=>{
 const s=new Set(Array.from({length:41},(_,i)=>tipoff+i*60000));
 assert.equal(eligibleSlot(tipoff,tipoff+41*60000+31000,s),null);
});
