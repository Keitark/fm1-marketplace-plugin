// Disposable local browser QA relay. No bridge/helper import or device I/O.
// The local dev Worker must have FM1_RELAY_TOKEN=test-only-browser-fixture-token-0000.
const origin=process.argv[2];
if(origin!=='http://127.0.0.1:3000')throw new Error('This fixture only serves the local development preview on port 3000.');
const token='test-only-browser-fixture-token-0000';
const catalog={apps:[{profile:'nes',title:'NES',variants:[{id:'nes-test',title:'Synthetic NES test',variant:'test',sha256:'a'.repeat(64),ready:true}]}],simulation:true};
let stopped=false;
async function post(route,body){const response=await fetch(origin+route,{method:'POST',headers:{authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(body),redirect:'error'});if(!response.ok)throw new Error('Local fixture response '+response.status);return response.json();}
async function poll(){await post('/relay/heartbeat',{allow_switch:true});const response=await post('/relay/poll',{});for(const row of response.tasks){const args=row.arguments;const data=row.operation==='catalog'?catalog:row.operation==='status'?{simulation:true,engine:{active:false,blocked_unknown:false}}:{id:args.job_id||row.id,operation:row.operation,status:row.operation==='switch_app'?'failed':'succeeded',simulation:true,progress:{phase:'fixture',verified_sectors:2,total_sectors:4,message:'Synthetic browser fixture; no device connected.'}};await post('/relay/result',{id:row.id,status:'succeeded',data});}}
process.on('SIGINT',()=>{stopped=true;});
console.log('Synthetic local HTTP relay ready. No device operations.');
while(!stopped){await poll();await new Promise(resolve=>setTimeout(resolve,100));}
await post('/relay/heartbeat',{allow_switch:false});
