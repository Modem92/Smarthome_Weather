/* Real phone-sized Chromium against isolated HTTPS + schema-3 Tk display. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'..'),output=path.join(root,'build/checks/designer-phone');
fs.mkdirSync(path.join(output,'browser-temp'),{recursive:true});process.env.TEMP=process.env.TMP=path.join(output,'browser-temp');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const executable=[path.join(process.env.ProgramFiles||'C:/Program Files','Google/Chrome/Application/chrome.exe'),path.join(process.env['ProgramFiles(x86)']||'C:/Program Files (x86)','Microsoft/Edge/Application/msedge.exe')].find(fs.existsSync);
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:executable,args:['--disable-background-networking']});
 const context=await browser.newContext({viewport:{width:375,height:900},ignoreHTTPSErrors:true,isMobile:true,hasTouch:true});
 const page=await context.newPage(),errors=[],external=[],posts=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts.push({path:new URL(r.url()).pathname,data:r.postDataJSON()});});
 await context.route('**/*',route=>{if(new URL(route.request().url()).hostname==='127.0.0.1')return route.continue();external.push(route.request().url());return route.abort();});
 const connection=JSON.parse(fs.readFileSync(path.join(output,'connection.json'),'utf8'));await page.goto(connection.url);
 await page.waitForFunction(()=>!document.querySelector('#code').disabled);
 let pairing;for(let i=0;i<30;i++){try{pairing=JSON.parse(fs.readFileSync(path.join(output,'pairing.json'),'utf8'));if(pairing?.code)break;}catch{}await page.waitForTimeout(100);}
 assert(pairing?.code);await page.locator('#code').fill(pairing.code);await page.locator('#login-form button').click();
 const settled=()=>page.waitForFunction(()=>document.querySelector('#draft-state').textContent.includes('Display')&&!document.querySelector('#add-page').disabled);
 await settled();
 const get=()=>page.evaluate(async()=>await (await fetch('/api/dashboard')).json());
 const initial=await get();assert([3,4].includes(initial.layout.version));assert.deepEqual(initial.layout.pages[0].grid,{columns:24,rows:16});
 fs.writeFileSync(path.join(output,'initial-display.json'),JSON.stringify(initial.display,null,2));
 const original=initial.layout.pages[0].widgets.find(w=>w.id==='clock');
 await page.locator('[data-id="clock"] .widget-handle').click();
 const handle=await page.locator('[data-id="clock"] .widget-handle').boundingBox();const board=await page.locator('#widget-board').boundingBox();
 const dx=board.width*(initial.display.viewport.grid.width+initial.display.viewport.grid.gap_x)/initial.display.viewport.width/24*2;
 await page.mouse.move(handle.x+handle.width/2,handle.y+handle.height/2);await page.mouse.down();await page.mouse.move(handle.x+handle.width/2+dx,handle.y+handle.height/2,{steps:6});await page.mouse.up();await settled();
 let current=await get(),clock=current.layout.pages[0].widgets.find(w=>w.id==='clock');assert.equal(clock.x,2);assert.deepEqual(clock.style,original.style);assert.deepEqual(clock.content_layout,original.content_layout);
 await page.locator('#widget-width').evaluate(e=>{e.value='6';e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));});await settled();
 current=await get();clock=current.layout.pages[0].widgets.find(w=>w.id==='clock');assert.equal(clock.w,6);
 await page.locator('#remove-widget').click();await settled();assert(!(await get()).layout.pages[0].widgets.some(w=>w.id==='clock'));
 await page.locator('#undo-layout').click();await settled();clock=(await get()).layout.pages[0].widgets.find(w=>w.id==='clock');assert.deepEqual(clock.style,original.style);assert.deepEqual(clock.content_layout,original.content_layout);assert.equal(clock.w,6);
 await page.locator('[data-id="series"] .widget-handle').click();const series=(await get()).layout.pages[0].widgets.find(w=>w.id==='series');
 await page.locator('#remove-widget').click();await settled();await page.locator('#undo-layout').click();await settled();assert.deepEqual((await get()).layout.pages[0].widgets.find(w=>w.id==='series'),series);
 await page.locator('#add-page').click();await settled();const added=(await get()).layout.pages.at(-1);
 await page.locator('#page-tabs button').first().click();await settled();await page.locator('[data-id="clock"] .widget-handle').click();await page.locator('#widget-page').selectOption(added.id);await page.locator('#move-widget-page').click();await settled();
 current=await get();assert.deepEqual(current.layout.pages.at(-1).widgets.find(w=>w.id==='clock').style,original.style);assert.deepEqual(current.layout.pages.at(-1).widgets.find(w=>w.id==='clock').content_layout,original.content_layout);
 await page.locator('#undo-layout').click();await settled();
 for(const width of [375,320]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));await page.screenshot({path:path.join(output,`phone-${width}.png`),fullPage:true});}
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert(posts.some(p=>p.path==='/api/dashboard/arrange'));assert(!posts.some(p=>p.path==='/api/dashboard'));assert(posts.filter(p=>p.path==='/api/dashboard/arrange').every(p=>!('layout' in p.data)));
 const display=JSON.parse(fs.readFileSync(path.join(output,'display.json'),'utf8'));assert.deepEqual(display.errors,[]);
 fs.writeFileSync(path.join(output,'results.json'),JSON.stringify({ok:true,version:initial.layout.version,checks:['24x16','touch-drag','resize','delete-undo-style','delete-undo-series','pages','cross-page','320px','375px','no-external','narrow-commands'],errors,external},null,2));
 await browser.close();fs.writeFileSync(path.join(output,'stop.request'),'stop');
})().catch(async error=>{console.error(error);if(browser)await browser.close();fs.writeFileSync(path.join(output,'stop.request'),'stop');process.exitCode=1;});
