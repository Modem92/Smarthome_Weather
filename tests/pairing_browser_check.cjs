/* Independent mobile browsers against the isolated widget_demo.py harness. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const output=path.resolve(__dirname,'../build/checks/widget-check');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const executable=path.join(process.env.ProgramFiles,'Google/Chrome/Application/chrome.exe');
const connection=JSON.parse(fs.readFileSync(path.join(output,'connection.json'),'utf8'));
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function waitFile(name,condition){
  for(let i=0;i<100;i++){
    try{const data=JSON.parse(fs.readFileSync(path.join(output,name),'utf8'));if(condition(data))return data;}catch{}
    await delay(100);
  }
  throw new Error(`Timed out: ${name}`);
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:executable,args:['--disable-background-networking']});
  const errors=[],external=[];
  try{
    const phone=async()=>{
      const context=await browser.newContext({ignoreHTTPSErrors:true,viewport:{width:375,height:850},isMobile:true});
      await context.route('**/*',route=>{if(new URL(route.request().url()).origin===connection.url)return route.continue();external.push(route.request().url());return route.abort();});
      const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
      await page.goto(connection.url);return {context,page};
    };
    const first=await phone();await first.page.waitForFunction(()=>!document.querySelector('#code').disabled);
    const initial=await waitFile('pairing.json',data=>data?.code);
    const second=await phone();await second.page.waitForFunction(()=>document.querySelector('#pair-state').textContent.includes('Position 2'));
    assert(await second.page.locator('#code').isDisabled());
    assert(!(await first.page.content()).includes(initial.code));
    await first.page.locator('#code').fill(initial.code);await first.page.locator('#login-form button').click();
    await first.page.locator('#widget-panel').waitFor({state:'visible'});
    await second.page.waitForFunction(()=>!document.querySelector('#code').disabled);
    const next=await waitFile('pairing.json',data=>data?.code&&data.code!==initial.code);
    assert.notEqual(initial.label,next.label);
    assert.equal(await first.page.evaluate(async()=>(await fetch('/api/settings')).status),200);
    await second.page.locator('#code').fill(next.code);await second.page.locator('#login-form button').click();
    await second.page.locator('#widget-panel').waitFor({state:'visible'});
    await waitFile('pairing.json',data=>data===null);
    await waitFile('display.json',data=>!data.labels.includes(next.code)&&data.labels.some(label=>label.includes('Wetterübersicht')));
    // Reloading an authenticated phone never displays a code.
    await first.page.reload();await first.page.locator('#widget-panel').waitFor({state:'visible'});
    await waitFile('pairing.json',data=>data===null);
    fs.writeFileSync(path.join(output,'restart.request'),'restart isolated test server');
    // Both old cookies must fail, without any stored sessions or shared code.
    for(const phone of [first,second]){
      await phone.page.waitForFunction(async()=>(await fetch('/api/settings')).status===401);
    }
    await first.page.reload();await first.page.locator('#login-panel').waitFor({state:'visible'});
    const fresh=await waitFile('pairing.json',data=>data?.code&&data.code!==initial.code&&data.code!==next.code);
    assert(fresh);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    fs.writeFileSync(path.join(output,'pairing-browser-results.json'),JSON.stringify({passed:true,
      checks:['two independent browsers','distinct one-use codes','FIFO wait','display-only code','simultaneous sessions',
      'code disappears after last login','authenticated reload','restart invalidates both cookies','new code after restart'],
      consoleErrors:errors,externalRequests:external},null,2));
    console.log('Independent browser pairing acceptance passed');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
