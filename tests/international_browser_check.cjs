/* Touch/browser acceptance against the isolated synthetic harness. No external traffic. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const output=path.resolve(__dirname,'../build/checks/international-check');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const executable=[path.join(process.env.ProgramFiles,'Google/Chrome/Application/chrome.exe'),path.join(process.env['ProgramFiles(x86)'],'Microsoft/Edge/Application/msedge.exe')].find(p=>fs.existsSync(p));
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:executable,args:['--disable-background-networking']});
 const context=await browser.newContext({viewport:{width:375,height:900},ignoreHTTPSErrors:true,isMobile:true,hasTouch:true});
 const page=await context.newPage(),errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 await context.route('**/*',route=>{if(new URL(route.request().url()).hostname==='127.0.0.1')return route.continue();external.push(route.request().url());return route.abort();});
 const connection=JSON.parse(fs.readFileSync(path.join(output,'connection.json'),'utf8'));
 await page.goto(connection.url);await page.waitForFunction(()=>!document.querySelector('#code').disabled);
 let pair;
 for(let i=0;i<60;i++){try{pair=JSON.parse(fs.readFileSync(path.join(output,'pairing.json'),'utf8'));}catch{}if(pair)break;await pause(100);}
 assert(pair);await page.locator('#code').fill(pair.code);await page.locator('#login-form button').click();
 await page.waitForFunction(()=>document.querySelector('#draft-state').textContent==='Am Display angezeigt');
 const capture=async name=>{const file=path.join(output,name+'-1024.png');if(fs.existsSync(file))fs.unlinkSync(file);fs.writeFileSync(path.join(output,'capture.request'),name);for(let i=0;i<40;i++){if(fs.existsSync(file))return;await pause(100);}throw Error('PC capture timed out');};
 await capture('overview');
 await page.locator('#page-tabs button').nth(1).click();await page.waitForFunction(()=>document.querySelector('#draft-state').textContent==='Am Display angezeigt');await capture('forecast');
 await page.locator('#page-tabs button').nth(2).click();await page.waitForFunction(()=>document.querySelector('#draft-state').textContent==='Am Display angezeigt');
 for(let i=0;i<40;i++){const display=JSON.parse(fs.readFileSync(path.join(output,'display.json'),'utf8'));if(display.labels.some(t=>t.includes('OpenStreetMap')))break;await pause(100);}
 await capture('radar');
 await page.locator('#settings-panel summary').click();
 await page.locator('#country').fill('Frankreich');
 assert.equal(await page.locator('#countries option[value="Frankreich"]').count(),1);
 await page.locator('#location').fill('Paris');
 for(const width of [375,320]){
   await page.setViewportSize({width,height:900});
   await page.locator('#settings-panel summary').scrollIntoViewIfNeeded();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.join(output,`phone-${width}.png`),fullPage:true});
 }
 const original=await page.evaluate(async()=>await(await fetch('/api/dashboard')).json());
 await page.locator('#settings-form button').click();
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Gespeichert.'));
 const saved=await page.evaluate(async()=>await(await fetch('/api/settings')).json());
 assert.equal(saved.location,'Paris');assert.equal(saved.country_code,'FR');assert.equal(saved.api_key_configured,true);
 const after=await page.evaluate(async()=>await(await fetch('/api/dashboard')).json());
 assert.deepEqual(after.layout,original.layout);
 await page.reload();await page.locator('#country').waitFor({state:'attached'});await page.waitForFunction(()=>document.querySelector('#country').value==='Frankreich');
 await page.locator('#settings-panel summary').click();
 await page.locator('#country').fill('Unbekannt');await page.locator('#settings-form button').click();
 await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Land aus der Länderauswahl'));
 const unchanged=await page.evaluate(async()=>await(await fetch('/api/settings')).json());assert.equal(unchanged.country_code,'FR');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 const display=JSON.parse(fs.readFileSync(path.join(output,'display.json'),'utf8'));assert.deepEqual(display.errors,[]);
 fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify({ok:true,widths:[375,320],country_saved:'FR',layout_preserved:true,key_preserved:true,errors,external},null,2));
 console.log('International mobile/PC visual checks passed; no external browser requests.');
 await browser.close();fs.writeFileSync(path.join(output,'stop.request'),'stop');
})().catch(async error=>{console.error(error);if(browser)await browser.close();fs.writeFileSync(path.join(output,'stop.request'),'stop');process.exitCode=1;});
