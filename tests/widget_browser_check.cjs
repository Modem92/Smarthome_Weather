/* Browser acceptance against tests/widget_demo.py, isolated dummy HTTPS + Tk. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const project=path.resolve(__dirname,'..'),output=path.join(project,'build','checks','widget-check');
fs.mkdirSync(path.join(output,'browser-temp'),{recursive:true});
process.env.TEMP=process.env.TMP=path.join(output,'browser-temp');
let playwright;
try{playwright=require('playwright');}
catch{playwright=require(path.join(process.env.USERPROFILE||require('os').homedir(),'.cache','codex-runtimes','codex-primary-runtime','dependencies','node','node_modules','playwright'));}
const {chromium}=playwright;
const executable=process.env.WETTERSTATION_TEST_BROWSER||[
 path.join(process.env.ProgramFiles||'C:/Program Files','Google','Chrome','Application','chrome.exe'),
 path.join(process.env['ProgramFiles(x86)']||'C:/Program Files (x86)','Microsoft','Edge','Application','msedge.exe'),
].find(file=>fs.existsSync(file));
let testBrowser=null;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:executable,args:['--disable-background-networking']});
 testBrowser=browser;
 const context=await browser.newContext({viewport:{width:375,height:900},ignoreHTTPSErrors:true,isMobile:true,hasTouch:true});
 const page=await context.newPage(),errors=[],external=[];
 let arrangementWrites=0;
 page.on('request',request=>{if(request.method()==='POST'&&['/api/dashboard','/api/dashboard/arrange'].includes(new URL(request.url()).pathname))arrangementWrites++;});
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('Failed to load resource'))errors.push(m.text());});
 await context.route('**/*',route=>{if(new URL(route.request().url()).hostname==='127.0.0.1')return route.continue();external.push(route.request().url());return route.abort();});
 const connection=JSON.parse(fs.readFileSync(path.join(output,'connection.json'),'utf8'));
 await page.goto(connection.url);
 const login=async(target)=>{
   await target.waitForFunction(()=>!document.querySelector('#code').disabled);
   let pair;
   for(let i=0;i<100;i++){
     try{pair=JSON.parse(fs.readFileSync(path.join(output,'pairing.json'),'utf8'));}catch{}
     if(pair&&await target.locator('#pair-state').textContent().then(t=>t.includes(pair.label)))break;
     await target.waitForTimeout(100);
   }
   assert(pair);await target.locator('#code').fill(pair.code);await target.locator('#login-form button').click();
 };
 await login(page);
 const saved=async()=>{await page.waitForFunction(()=>/Am Display (gespeichert|angezeigt)/.test(document.querySelector('#draft-state').textContent));};
 await saved();
 const remote=()=>page.evaluate(async()=>await(await fetch('/api/dashboard')).json());
 const click=async selector=>{await page.locator(selector).click();await saved();};
 const select=async title=>{await page.getByRole('button',{name:title,exact:true}).click();await saved();};
 const rename=async title=>{await page.locator('#page-title').fill(title);await click('#rename-page');};
 const checkBounds=async()=>assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 const initial=await remote();assert.equal(initial.layout.pages.length,4);
 const handleStyle=await page.locator('.widget-tile:not(.selected) .widget-handle').first().evaluate(element=>{
   const style=getComputedStyle(element);return {alignment:style.textAlign,width:style.borderTopWidth,color:style.borderTopColor};
 });
 assert.deepEqual(handleStyle,{alignment:'center',width:'2px',color:'rgb(96, 96, 96)'});
 if(initial.demo){assert(await page.locator('#demo-notice').isVisible());assert(await page.locator('#settings-panel details').isHidden());}
 await checkBounds();await page.screenshot({path:path.join(output,'phone-375.png'),fullPage:true});
 await page.setViewportSize({width:320,height:800});await checkBounds();await page.screenshot({path:path.join(output,'phone-320.png'),fullPage:true});
 await page.setViewportSize({width:375,height:900});
 const clock=initial.layout.pages[0].widgets.find(w=>w.type==='clock');
 await page.locator(`[data-id="${clock.id}"] .widget-handle`).click();
 assert(await page.locator('#field-options').isHidden());
 let current=await remote();assert.deepEqual(current.layout,initial.layout);
 // A full page refuses overflow and offers transfer, preserving the old page.
 await page.locator('#widget-type').selectOption('clock');await page.locator('#add-widget').click();
 await page.locator('#transfer-panel').waitFor({state:'visible'});assert.deepEqual((await remote()).layout,initial.layout);
 await page.locator('#transfer-target').selectOption('__new__');await click('#transfer-widget');
 current=await remote();assert.equal(current.layout.pages.length,5);
 let custom=current.layout.pages.at(-1),id=custom.widgets[0].id;
 await rename('Meine Anzeige');
 // Touch dragging uses a stable pointer capture even though preview tiles redraw.
 const handle=page.locator(`[data-id="${id}"] .widget-handle`);await handle.scrollIntoViewIfNeeded();
 let box=await handle.boundingBox(),board=await page.locator('#widget-board').boundingBox();
 const cdp=await context.newCDPSession(page);
 const writesBeforeDrag=arrangementWrites;
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x+12,y:box.y+10}]});
 for(let i=1;i<=8;i++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:box.x+12+board.width*1008/1024/12*2*i/8,y:box.y+10+board.width/1024*544/8*2*i/8}]});
 assert.equal(arrangementWrites,writesBeforeDrag,'No layout writes during touch movement');
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await saved();
 assert.equal(arrangementWrites,writesBeforeDrag+1,'One layout write after touch release');
 custom=(await remote()).layout.pages.at(-1);assert.equal(custom.widgets[0].x,2);assert.equal(custom.widgets[0].y,2);
 // Sliders commit once on change and retain explicit size when contents change.
 await page.locator('#widget-width').evaluate(e=>{e.value='6';e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));});await saved();
 assert.equal((await remote()).layout.pages.at(-1).widgets[0].w,6);
 await click('[data-move="right"]');assert.equal((await remote()).layout.pages.at(-1).widgets[0].x,3);
 // Resize grip and duplicate widgets.
 const grip=page.locator(`[data-id="${id}"] .resize-handle`);await grip.scrollIntoViewIfNeeded();box=await grip.boundingBox();board=await page.locator('#widget-board').boundingBox();
 await page.mouse.move(box.x+10,box.y+10);await page.mouse.down();await page.mouse.move(box.x+10+board.width*1008/1024/12,box.y+10+board.width/1024*544/8,{steps:8});await page.mouse.up();await saved();
 custom=(await remote()).layout.pages.at(-1);assert.equal(custom.widgets[0].w,7);assert.equal(custom.widgets[0].h,4);
 await click('#add-widget');custom=(await remote()).layout.pages.at(-1);assert.equal(custom.widgets.length,2);
 // Transfer an existing widget to a new page and reorder pages without losing IDs.
 await page.locator('#widget-page').selectOption('__new__');await click('#move-widget-page');
 current=await remote();assert.equal(current.layout.pages.length,6);assert.equal(current.layout.pages[4].widgets.length,1);
 const movedPage=current.layout.pages.at(-1).id;
 await click('#page-earlier');current=await remote();assert.equal(current.layout.pages[4].id,movedPage);
 await click('#page-later');await click('#compact-layout');
 // Twenty undo entries are retained, including a full undo boundary.
 for(let i=0;i<22;i++)await rename(`Rückgängig ${i}`);
 for(let i=0;i<20;i++)await click('#undo-layout');
 assert(await page.locator('#undo-layout').isDisabled());assert.equal((await remote()).layout.pages.at(-1).title,'Rückgängig 1');
 // Failed saves retain local draft and do not mutate persisted state.
 const beforeFailure=(await remote()).layout;
 await page.route('**/api/dashboard',route=>route.request().method()==='POST'?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Test: Speichern fehlgeschlagen'})}):route.continue());
 await page.locator('#page-title').fill('Nur lokaler Entwurf');await page.locator('#rename-page').click();
 await page.waitForFunction(()=>document.querySelector('#draft-state').textContent==='Nicht bestätigt');
 assert.equal(await page.locator('#page-title').inputValue(),'Nur lokaler Entwurf');assert.deepEqual((await remote()).layout,beforeFailure);
 await page.unroute('**/api/dashboard');await click('#retry-layout');assert.equal((await remote()).layout.pages.at(-1).title,'Nur lokaler Entwurf');
 // A lost response after a successful write is recovered without overwriting it.
 await page.route('**/api/dashboard',async route=>{if(route.request().method()==='POST'){await route.fetch();await route.abort();}else await route.continue();});
 await page.locator('#page-title').fill('Antwort verloren');await page.locator('#rename-page').click();
 await page.waitForFunction(()=>document.querySelector('#draft-state').textContent==='Nicht bestätigt');
 assert.equal((await remote()).layout.pages.at(-1).title,'Antwort verloren');
 await page.unroute('**/api/dashboard');await click('#retry-layout');
 // Expired authentication keeps a failed draft through a fresh login.
 await page.evaluate(async()=>{const s=await(await fetch('/api/settings')).json();await fetch('/api/logout',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf},body:'{}'});document.querySelector('#page-title').value='Nach neuer Anmeldung';document.querySelector('#rename-page').click();});
 await page.locator('#login-panel').waitFor({state:'visible'});
 await login(page);
 await page.locator('#widget-panel').waitFor({state:'visible'});assert.equal(await page.locator('#page-title').inputValue(),'Nach neuer Anmeldung');
 await click('#retry-layout');
 // Independent session conflict, without silently dropping the local draft.
 const peer=await context.newPage();await peer.goto(connection.url);await peer.waitForFunction(()=>/Am Display/.test(document.querySelector('#draft-state').textContent));
 await peer.locator('#page-title').fill('Andere Sitzung');await peer.locator('#rename-page').click();await peer.waitForFunction(()=>document.querySelector('#draft-state').textContent==='Am Display gespeichert');
 await page.waitForFunction(()=>document.querySelector('#draft-state').textContent==='Layout geändert');
 assert.equal(await page.locator('#page-title').inputValue(),'Nach neuer Anmeldung');
 await page.locator('#reload-layout').click();await saved();assert.equal((await remote()).layout.pages[0].title,'Andere Sitzung');
 await peer.close();
 // Page deletion is reversible; the last page cannot be removed.
 while((await remote()).layout.pages.length>1)await click('#remove-page');
 assert(await page.locator('#remove-page').isDisabled());await click('#undo-layout');assert.equal((await remote()).layout.pages.length,2);
 assert.equal(errors.length,0,errors.join('\n'));assert.equal(external.length,0);
 assert(!JSON.stringify(await remote()).includes('dummy-widget-check-key'));
 // Restore prepared start pages for final visual checks, using the tested interface.
 await page.evaluate(async layout=>{
   const s=await(await fetch('/api/settings')).json(),d=await(await fetch('/api/dashboard')).json();
   await fetch('/api/dashboard',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf},body:JSON.stringify({layout,revision:d.revision,page_id:layout.pages[0].id})});
 },initial.layout);
 await page.locator('#reload-layout').click();await saved();
 await page.locator('#page-tabs button').first().click();await saved();
 fs.writeFileSync(path.join(output,'capture.request'),'capture');
 await page.waitForTimeout(350);await page.screenshot({path:path.join(output,'phone-final.png'),fullPage:true});
 fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({passed:true,consoleErrors:errors,externalRequests:external,checks:['centered widget labels and stronger borders','phone320/375','content fields preserved without editing controls','undo20','full-page transfer','add duplicate','touch drag','resize grip','sliders','direction controls','cross-page move','page rename/reorder/delete','last page guard','save failure','lost response recovery','session reauthentication preserves draft','session conflict','Tk acknowledgement']},null,2));
 console.log('Browser widget acceptance passed');await browser.close();
})().catch(async error=>{console.error(error);if(testBrowser)await testBrowser.close();process.exitCode=1;});
