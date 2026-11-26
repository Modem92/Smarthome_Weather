/* Deterministic browser scheduling contract, no sockets or real credentials. */
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../wetterstation/mobile/web/app.js'),'utf8');
const scheduling=source.slice(source.indexOf('function schedulePoll(){'),source.indexOf("window.addEventListener('beforeunload'"));
let now=0,calls=0,remote={revision:'r1',page_id:'p'},sequence=0;
const timers=new Map(),elements=new Map(),events={};
const context=vm.createContext({Date:{now:()=>now},
 document:{hidden:false,addEventListener:(kind,handler)=>events[kind]=handler},
 window:{addEventListener:(kind,handler)=>events[kind]=handler},
 setTimeout:fn=>{timers.set(++sequence,fn);return sequence;},clearTimeout:id=>timers.delete(id),
 request:async()=>{calls++;return remote;},renderBoard(){},setControls(){},draft(){},notice(){},
 byId:id=>{if(!elements.has(id))elements.set(id,{});return elements.get(id);},
 csrf:'dummy',layout:{pages:[]},layoutRevision:'r1',pageId:'p',viewport:{},
 saving:false,blocked:false,paused:false,resuming:false,lastActivity:0,IDLE_MS:60000,pollTimer:null});
vm.runInContext(scheduling,context);
async function tick(){const [id,fn]=timers.entries().next().value;timers.delete(id);await fn();}
(async()=>{
 vm.runInContext('schedulePoll()',context);await tick();assert.equal(calls,1);
 now=60001;await tick();assert.equal(calls,1);assert.equal(timers.size,0);assert.equal(context.paused,true);
 await vm.runInContext('resumePolling()',context);assert.equal(calls,2);assert.equal(context.paused,false);
 context.document.hidden=true;events.visibilitychange();assert.equal(timers.size,0);
 await vm.runInContext('resumePolling()',context);assert.equal(calls,2);
 context.document.hidden=false;await vm.runInContext('resumePolling()',context);assert.equal(calls,3);
 remote={revision:'r2',page_id:'p'};vm.runInContext('pausePolling()',context);
 let cancelled=false;
 context.event={target:{closest:()=>null},preventDefault(){cancelled=true;},stopImmediatePropagation(){}};
 vm.runInContext('activity(event)',context);await new Promise(resolve=>setImmediate(resolve));
 assert.equal(cancelled,true);assert.equal(context.blocked,true);assert.equal(timers.size,0);
 // Reload/logout/recovery must stay usable even if a stale revision prevents edits.
 cancelled=false;context.event.target.closest=()=>({});vm.runInContext('activity(event)',context);assert.equal(cancelled,false);
 console.log('Idle polling, visibility, resume-before-edit, conflict and recovery: OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
