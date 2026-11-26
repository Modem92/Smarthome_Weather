'use strict';
const byId=id=>document.getElementById(id),{copy}=WidgetLayout;
let viewport={width:1024,height:600,grid:{x:12,y:52,width:1000,height:536,gap:8}};
let pairTimer=null,pairingPending=false;
let csrf='',layout=null,catalog={},layoutRevision='',pageId='',selected='',undoStack=[];
let saving=false,blocked=false,dirty=false,settingsBusy=false,drag=null,transfer=null,sliderBefore=null,pollTimer=null;
let savedLayout=null;
let lastActivity=Date.now(),paused=false,resuming=false;
const IDLE_MS=60000;
const page=()=>layout?.pages.find(p=>p.id===pageId);
const design=()=>[3,4].includes(layout?.version);
const dimensions=(p=page())=>({columns:p?.grid?.columns||12,rows:p?.grid?.rows||8});
const maxPages=()=>design()?64:12;
function arrange(items,pinned=null,compact=false,target=null){const {columns,rows}=dimensions(target||page());return WidgetLayout.arrange(items,pinned,compact,columns,rows,design()&&pinned!==null&&!compact);}
function placeNew(items,proposed,target=page()){
  if(!design())return arrange([...items,proposed],null,false,target);
  const {columns,rows}=dimensions(target),w=copy(proposed);w.w=Math.min(columns,w.w);w.h=Math.min(rows,w.h);
  for(let y=0;y<=rows-w.h;y++)for(let x=0;x<=columns-w.w;x++){
    w.x=x;w.y=y;if(!items.some(b=>w.x<b.x+b.w&&b.x<w.x+w.w&&w.y<b.y+b.h&&b.y<w.y+w.h))return [...copy(items),w];
  }
  throw new Error('NO_SPACE');
}
function arrangementOperations(before,after){
  const ops=[],oldPages=new Map(before.pages.map(p=>[p.id,p])),oldWidgets=new Map(before.pages.flatMap(p=>p.widgets.map(w=>[w.id,{w,page:p.id}])));
  const newWidgets=new Map(after.pages.flatMap(p=>p.widgets.map(w=>[w.id,{w,page:p.id}])));
  for(const p of after.pages){
    if(!oldPages.has(p.id))ops.push({op:'add_page',page:p.id,title:p.title});
    else if(oldPages.get(p.id).title!==p.title)ops.push({op:'rename_page',page:p.id,title:p.title});
  }
  for(const [id,{w,page}] of newWidgets){
    const old=oldWidgets.get(id);
    if(!old)ops.push({op:'add_widget',page,id,type:w.type,x:w.x,y:w.y,w:w.w,h:w.h});
    else {
      if(old.page!==page||['x','y','w','h'].some(k=>w[k]!==old.w[k]))ops.push({op:'move_widget',page,id,x:w.x,y:w.y,w:w.w,h:w.h});
      if(JSON.stringify(old.w.fields)!==JSON.stringify(w.fields))ops.push({op:'fields',page,id,fields:w.fields});
    }
  }
  for(const [id,old] of oldWidgets)if(!newWidgets.has(id))ops.push({op:'remove_widget',page:old.page,id});
  for(const p of before.pages)if(!after.pages.some(v=>v.id===p.id))ops.push({op:'remove_page',page:p.id});
  ops.push({op:'order_pages',ids:after.pages.map(p=>p.id)});return ops;
}
const widget=()=>page()?.widgets.find(w=>w.id===selected);
const uid=prefix=>`${prefix}-${crypto.randomUUID()}`;
const snapshot=()=>({layout:copy(layout),pageId,selected});
function restore(s){layout=copy(s.layout);pageId=s.pageId;selected=s.selected;}
function notice(text,kind=''){byId('status').textContent=text;byId('status').className=`notice ${kind}`;}
function draft(text){byId('draft-state').textContent=text;}
function showLogin(message,preserveDraft=false,requestCode=true){
  csrf='';saving=false;drag=null;transfer=null;
  if(!preserveDraft){layout=null;dirty=false;blocked=false;undoStack=[];}
  else if(layout)blocked=true;
  clearTimeout(pollTimer);byId('api-key').value='';byId('location').value='';
  byId('settings-panel').hidden=true;byId('widget-panel').hidden=true;byId('login-panel').hidden=false;notice(message);
  if(requestCode)beginPairing();
  else{clearTimeout(pairTimer);pairState({state:'expired'});}
}
function pairState(state){
  const active=state.state==='active';
  byId('pair-state').textContent=active?`${state.label}: Der Code steht jetzt auf dem Display der Wetterstation.`:
    state.state==='waiting'?`${state.label}: Du bist an Position ${state.position+1}. Bitte warten, bis dein Code am Display erscheint.`:
    state.state==='full'?'Acht Browser sind bereits verbunden. Bitte einen davon abmelden.':
    'Der Anmeldeversuch ist abgelaufen. Fordere bei Bedarf einen neuen Code an.';
  byId('code').disabled=!active;byId('login-form').querySelector('button').disabled=!active;
  byId('pair-retry').hidden=!['expired','full'].includes(state.state);
}
async function beginPairing(){
  if(pairingPending||byId('login-panel').hidden)return;
  pairingPending=true;clearTimeout(pairTimer);
  try{
    const state=await request('/api/pairing/start',{});
    if(state.state==='authenticated'){await loadSettings();return;}
    pairState(state);pollPairing();
  }catch(error){byId('pair-state').textContent=error.message;byId('pair-retry').hidden=false;}
  finally{pairingPending=false;}
}
function pollPairing(){
  clearTimeout(pairTimer);
  if(byId('login-panel').hidden)return;
  pairTimer=setTimeout(async()=>{
    try{const state=await request('/api/pairing');pairState(state);if(!['expired','full'].includes(state.state))pollPairing();}
    catch(error){byId('pair-state').textContent=error.message;byId('pair-retry').hidden=false;}
  },1500);
}
byId('pair-retry').addEventListener('click',beginPairing);
async function request(path,data){
  const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),10000);
  try{
    const options={credentials:'same-origin',cache:'no-store',signal:abort.signal};
    if(data!==undefined){options.method='POST';options.headers={'Content-Type':'application/json','X-CSRF-Token':csrf};options.body=JSON.stringify(data);}
    const response=await fetch(path,options),result=await response.json();
    if(!response.ok){
      if(response.status===401&&path!=='/api/login')showLogin(result.error,true);
      const error=new Error(result.error||'Die Anfrage ist fehlgeschlagen.');error.status=response.status;throw error;
    }
    return result;
  }catch(error){
    if(error instanceof TypeError||error.name==='AbortError')throw new Error('Keine Verbindung zur Wetterstation. Prüfe die Vorschau und das Heimnetz.');
    throw error;
  }finally{clearTimeout(timeout);}
}
function setControls(){
  if(!layout)return;
  document.querySelectorAll('#widget-panel button,#widget-panel input,#widget-panel select').forEach(e=>e.disabled=saving||blocked);
  byId('retry-layout').hidden=!blocked;
  byId('retry-layout').disabled=saving;
  byId('reload-layout').disabled=saving;
  byId('undo-layout').disabled=saving||blocked||!undoStack.length;
  byId('remove-page').disabled=saving||blocked||layout.pages.length===1;
  byId('add-page').disabled=saving||blocked||layout.pages.length>=maxPages();
  byId('page-earlier').disabled=saving||blocked||layout.pages[0].id===pageId;
  byId('page-later').disabled=saving||blocked||layout.pages.at(-1).id===pageId;
  byId('logout').disabled=saving||settingsBusy;
}
function renderPages(){
  const tabs=byId('page-tabs');tabs.replaceChildren();
  layout.pages.forEach((p,index)=>{
    const button=document.createElement('button');button.type='button';button.className='page-tab'+(p.id===pageId?' active':'');
    button.textContent=`${index+1} · ${p.title}`;button.setAttribute('aria-pressed',String(p.id===pageId));
    button.addEventListener('click',()=>selectPage(p.id));tabs.append(button);
  });
  byId('page-title').value=page().title;
}
function renderBoard(){
  if(!layout)return;
  const board=byId('widget-board');board.replaceChildren();board.style.aspectRatio=`${viewport.width}/${viewport.height}`;
  const g=viewport.grid;
  const {columns,rows}=dimensions(),gx=g.gap_x??g.gap,gy=g.gap_y??g.gap;
  const fullRadar=!design()&&page().widgets.length===1&&page().widgets[0].type==='radar'&&page().widgets[0].w===12&&page().widgets[0].h===8&&page().widgets[0].fields.includes('map');
  const title=document.createElement('span');title.className='board-title';title.textContent=page().title;board.append(title);
  if(!page().widgets.length){const empty=document.createElement('span');empty.className='board-empty';empty.textContent='Platz für deine Widgets';board.append(empty);}
  page().widgets.forEach(w=>{
    const tile=document.createElement('div');tile.className='widget-tile'+(w.id===selected?' selected':'');tile.dataset.id=w.id;
    tile.style.left=`${(g.x+w.x*(g.width+gx)/columns)/viewport.width*100}%`;tile.style.top=`${(g.y+w.y*(g.height+gy)/rows)/viewport.height*100}%`;
    tile.style.width=`${(w.w*(g.width+gx)/columns-gx)/viewport.width*100}%`;tile.style.height=`${(w.h*(g.height+gy)/rows-gy)/viewport.height*100}%`;
    if(fullRadar){tile.style.left='0%';tile.style.top='0%';tile.style.width='100%';tile.style.height='100%';}
    const handle=document.createElement('button');handle.type='button';handle.className='widget-handle';
    handle.textContent=catalog[w.type].title;handle.setAttribute('aria-label',`${catalog[w.type].title} auswählen und verschieben`);
    handle.addEventListener('click',()=>{selected=w.id;renderBoard();renderEditor();setControls();});
    handle.addEventListener('pointerdown',event=>startDrag(event,w,false));
    const resize=document.createElement('button');resize.type='button';resize.className='resize-handle';resize.textContent='↘';
    resize.setAttribute('aria-label',`${catalog[w.type].title} Größe ändern`);resize.addEventListener('pointerdown',event=>startDrag(event,w,true));
    tile.append(handle,resize);board.append(tile);
  });
}
function destinationOptions(select,exclude){
  select.replaceChildren();layout.pages.filter(p=>p.id!==exclude).forEach(p=>{
    const option=document.createElement('option');option.value=p.id;option.textContent=p.title;select.append(option);
  });
  if(layout.pages.length<maxPages()){const option=document.createElement('option');option.value='__new__';option.textContent='+ Neue Seite';select.append(option);}
}
function renderEditor(){
  const w=widget();byId('widget-editor').hidden=!w;if(!w)return;
  const spec=catalog[w.type];byId('selected-title').textContent=spec.title;
  const {columns,rows}=dimensions();
  for(const [name,key,min] of [['width','w',spec.min_width],['height','h',spec.min_height]]){
    byId(`widget-${name}`).min=min;byId(`widget-${name}`).value=w[key];
    byId(`widget-${name}`).max=key==='w'?columns:rows;
    byId(`widget-${name}`).disabled=saving||blocked||Boolean(w.locked);
    byId(`${name}-value`).textContent=`${w[key]} / ${key==='w'?columns:rows}`;
  }
  byId('field-options').hidden=true;
  destinationOptions(byId('widget-page'),pageId);
}
function render(){if(!layout)return;renderPages();renderBoard();renderEditor();setControls();}
async function loadSettings(){
  const settings=await request('/api/settings');csrf=settings.csrf;
  byId('location').value=settings.location;byId('api-key').value='';
  byId('countries').replaceChildren(...settings.countries.sort((a,b)=>a.name.localeCompare(b.name,'de')).map(row=>{
    const option=document.createElement('option');option.value=row.name;option.dataset.code=row.code;return option;
  }));
  byId('country').value=settings.countries.find(row=>row.code===settings.country_code)?.name||'';
  byId('key-state').textContent=settings.api_key_configured?'Ein Schlüssel ist bereits hinterlegt.':'Noch kein Schlüssel hinterlegt.';
  clearTimeout(pairTimer);byId('code').value='';
  byId('login-panel').hidden=true;byId('settings-panel').hidden=false;
  if(!layout)await loadDashboard();
  else{byId('widget-panel').hidden=false;render();schedulePoll();}
}
async function loadDashboard(){
  const result=await request('/api/dashboard');layout=result.layout;catalog=result.catalog;layoutRevision=result.revision;
  savedLayout=copy(layout);
  if(design()){viewport.width=layout.display.width;viewport.height=layout.display.height;}
  if(result.display.viewport)viewport=result.display.viewport;
  byId('preview-label').textContent=`DEIN DISPLAY · ${viewport.width} × ${viewport.height}`;
  byId('demo-notice').hidden=!result.demo;
  byId('settings-panel').querySelector('details').hidden=Boolean(result.demo);
  pageId=layout.pages.some(p=>p.id===pageId)?pageId:layout.pages[0].id;selected=page().widgets[0]?.id||'';
  undoStack=[];blocked=false;dirty=false;transfer=null;byId('transfer-panel').hidden=true;
  paused=false;lastActivity=Date.now();
  byId('widget-type').replaceChildren();Object.entries(catalog).forEach(([key,spec])=>{const option=document.createElement('option');option.value=key;option.textContent=spec.title;byId('widget-type').append(option);});
  byId('widget-panel').hidden=false;render();
  await selectPage(pageId);schedulePoll();
}
async function waitDisplay(expectedRevision,expectedPage){
  for(let attempt=0;attempt<25;attempt++){
    const state=await request('/api/display');if(state.error)throw new Error(state.error);
    if(state.revision===expectedRevision&&state.page_id===expectedPage){if(state.viewport)viewport=state.viewport;return;}
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  throw new Error('Gespeichert, aber das Display hat die Änderung noch nicht bestätigt. Bitte erneut verbinden.');
}
async function selectPage(id){
  if(saving||blocked||!layout)return;
  pageId=id;selected=page().widgets[0]?.id||'';transfer=null;byId('transfer-panel').hidden=true;render();
  saving=true;setControls();draft('Wird angezeigt …');
  try{await request('/api/display/page',{page_id:id,revision:layoutRevision});await waitDisplay(layoutRevision,id);draft('Am Display angezeigt');}
  catch(error){if(layout){blocked=true;draft('Nicht bestätigt');notice(error.message,'error');}}
  finally{saving=false;render();}
}
async function saveLayout(){
  saving=true;setControls();draft('Wird übertragen …');
  try{
    const result=design()?await request('/api/dashboard/arrange',{operations:arrangementOperations(savedLayout,layout),revision:layoutRevision,page_id:pageId}):await request('/api/dashboard',{layout,revision:layoutRevision,page_id:pageId});
    if(!layout)return;
    layout=result.layout;layoutRevision=result.revision;
    savedLayout=copy(layout);
    await waitDisplay(layoutRevision,pageId);dirty=false;blocked=false;draft('Am Display gespeichert');notice('Änderung auf der Wetterstation übernommen.','success');
  }catch(error){if(layout){blocked=true;draft('Nicht bestätigt');notice(`${error.message} Dein Entwurf bleibt hier sichtbar.`,'error');}}
  finally{saving=false;render();}
}
function pushUndo(before){undoStack.push(before);if(undoStack.length>20)undoStack.shift();}
function offerTransfer(proposed,sourceId){
  transfer={widget:copy(proposed),sourceId};byId('transfer-panel').hidden=false;
  destinationOptions(byId('transfer-target'),sourceId);notice('Kein Platz. Die letzte passende Anordnung bleibt erhalten.','error');
}
function commit(change,{before=null,proposed=null,sourceId=pageId}={}){
  if(saving||blocked)return;
  before=before||snapshot();
  try{change();}
  catch(error){restore(before);render();if(error.message==='NO_SPACE'&&proposed)offerTransfer(proposed,sourceId);else notice(error.message==='NO_SPACE'?'Auf dieser Seite ist kein Platz.':error.message,'error');return;}
  if(JSON.stringify(before.layout)===JSON.stringify(layout)){render();return;}
  pushUndo(before);dirty=true;transfer=null;byId('transfer-panel').hidden=true;render();saveLayout();
}
function reposition(w){
  if(w.locked)throw new Error('Dieses Widget ist am PC gesperrt.');
  const {columns,rows}=dimensions();w.x=Math.max(0,Math.min(columns-w.w,w.x));w.y=Math.max(0,Math.min(rows-w.h,w.y));
  page().widgets=arrange(page().widgets,w.id);
}
function startDrag(event,w,resize){
  if(saving||blocked||w.locked||event.button!==0)return;event.preventDefault();selected=w.id;
  byId('widget-board').setPointerCapture(event.pointerId);
  drag={before:snapshot(),id:w.id,resize,px:event.clientX,py:event.clientY,width:byId('widget-board').getBoundingClientRect().width,changed:false,failed:false,proposal:null};
  renderBoard();renderEditor();setControls();
}
document.addEventListener('pointermove',event=>{
  if(!drag)return;event.preventDefault();
  const {columns,rows}=dimensions();
  const dx=Math.round((event.clientX-drag.px)/(drag.width*(viewport.grid.width+(viewport.grid.gap_x??viewport.grid.gap))/viewport.width/columns));
  const dy=Math.round((event.clientY-drag.py)/(drag.width/viewport.width*(viewport.grid.height+(viewport.grid.gap_y??viewport.grid.gap))/rows));
  restore(drag.before);const w=widget(),spec=catalog[w.type];
  if(drag.resize){w.w=Math.max(spec.min_width,Math.min(columns,w.w+dx));w.h=Math.max(spec.min_height,Math.min(rows,w.h+dy));}else{w.x+=dx;w.y+=dy;}
  w.x=Math.max(0,Math.min(columns-w.w,w.x));w.y=Math.max(0,Math.min(rows-w.h,w.y));drag.proposal=copy(w);
  try{reposition(w);drag.failed=false;drag.changed=JSON.stringify(layout)!==JSON.stringify(drag.before.layout);}
  catch(error){restore(drag.before);drag.failed=true;drag.changed=false;}
  renderBoard();renderEditor();setControls();
},{passive:false});
function finishDrag(){
  if(!drag)return;const done=drag;drag=null;
  if(done.failed){restore(done.before);render();offerTransfer(done.proposal,done.before.pageId);return;}
  if(done.changed){pushUndo(done.before);dirty=true;render();saveLayout();}else render();
}
function cancelDrag(){if(drag){restore(drag.before);drag=null;render();}}
function cancelSlider(){if(sliderBefore){restore(sliderBefore);sliderBefore=null;render();}}
document.addEventListener('pointerup',finishDrag);document.addEventListener('pointercancel',cancelDrag);
window.addEventListener('blur',()=>{cancelDrag();cancelSlider();});document.addEventListener('keydown',e=>{if(e.key==='Escape'){cancelDrag();cancelSlider();}});
for(const [name,key] of [['width','w'],['height','h']]){
  const input=byId(`widget-${name}`);
  input.addEventListener('pointercancel',cancelSlider);
  input.addEventListener('input',()=>{
    if(saving||blocked)return;if(!sliderBefore)sliderBefore=snapshot();
    const desired=Number(input.value);restore(sliderBefore);const w=widget();w[key]=desired;
    const proposed=copy(w);
    try{reposition(w);renderBoard();const dims=dimensions();byId(`${name}-value`).textContent=`${w[key]} / ${key==='w'?dims.columns:dims.rows}`;}
    catch{restore(sliderBefore);renderBoard();byId(`${name}-value`).textContent='Kein Platz';input.dataset.failed='true';input._proposed=proposed;return;}
    input.dataset.failed='';
  });
  input.addEventListener('change',()=>{
    if(!sliderBefore)return;const before=sliderBefore;sliderBefore=null;
    if(input.dataset.failed){restore(before);render();offerTransfer(input._proposed,before.pageId);input.dataset.failed='';return;}
    if(JSON.stringify(layout)!==JSON.stringify(before.layout)){pushUndo(before);dirty=true;render();saveLayout();}else render();
  });
}
document.querySelectorAll('[data-move]').forEach(button=>button.addEventListener('click',()=>{
  const w=widget();if(!w)return;const [dx,dy]={left:[-1,0],right:[1,0],up:[0,-1],down:[0,1]}[button.dataset.move];
  const proposed={...copy(w),x:w.x+dx,y:w.y+dy};commit(()=>{const current=widget();current.x+=dx;current.y+=dy;reposition(current);},{proposed});
}));
function createPage(){if(layout.pages.length>=maxPages())throw new Error('Maximale Seitenzahl erreicht.');const p={id:uid('p'),title:`Seite ${layout.pages.length+1}`,widgets:[]};if(design()){p.grid={columns:12,rows:8};p.style={};}layout.pages.push(p);return p;}
byId('add-page').addEventListener('click',()=>commit(()=>{pageId=createPage().id;selected='';}));
byId('rename-page').addEventListener('click',()=>{const title=byId('page-title').value.trim();if(!title||title.length>40){notice('Bitte einen Seitennamen mit höchstens 40 Zeichen eingeben.','error');return;}commit(()=>page().title=title);});
byId('page-title').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();byId('rename-page').click();}});
byId('remove-page').addEventListener('click',()=>{if(layout.pages.length<=1)return;commit(()=>{const index=layout.pages.findIndex(p=>p.id===pageId);layout.pages.splice(index,1);pageId=layout.pages[Math.min(index,layout.pages.length-1)].id;selected=page().widgets[0]?.id||'';});});
for(const [id,step] of [['page-earlier',-1],['page-later',1]])byId(id).addEventListener('click',()=>commit(()=>{const index=layout.pages.findIndex(p=>p.id===pageId),next=index+step;if(next>=0&&next<layout.pages.length)[layout.pages[index],layout.pages[next]]=[layout.pages[next],layout.pages[index]];}));
byId('add-widget').addEventListener('click',()=>{
  const type=byId('widget-type').value,spec=catalog[type];let fields=Object.keys(spec.fields).filter(f=>f!=='seconds');
  if(type==='weather')fields=['temp','description','humidity'];if(type==='hourly'||type==='daily')fields=['temp','rain'];
  const proposed={id:uid('w'),type,x:0,y:0,w:spec.width,h:spec.height,fields};
  commit(()=>{if(design())page().widgets=placeNew(page().widgets,proposed);else{page().widgets.push(copy(proposed));page().widgets=arrange(page().widgets,proposed.id);}selected=proposed.id;},{proposed,sourceId:pageId});
});
byId('remove-widget').addEventListener('click',()=>commit(()=>{page().widgets=page().widgets.filter(w=>w.id!==selected);selected=page().widgets[0]?.id||'';}));
byId('compact-layout').addEventListener('click',()=>commit(()=>page().widgets=arrange(page().widgets,null,true)));
function moveTo(targetId,proposed,sourceId){
  commit(()=>{
    const target=targetId==='__new__'?createPage():layout.pages.find(p=>p.id===targetId);
    if(!target)throw new Error('Die Zielseite ist nicht mehr vorhanden.');
    const moved={...copy(proposed),x:0,y:0};target.widgets=placeNew(target.widgets,moved,target);
    const source=layout.pages.find(p=>p.id===sourceId);if(source)source.widgets=source.widgets.filter(w=>w.id!==proposed.id);
    pageId=target.id;selected=moved.id;
  },{proposed,sourceId});
}
byId('move-widget-page').addEventListener('click',()=>{if(widget())moveTo(byId('widget-page').value,widget(),pageId);});
byId('transfer-widget').addEventListener('click',()=>{if(transfer)moveTo(byId('transfer-target').value,transfer.widget,transfer.sourceId);});
byId('cancel-transfer').addEventListener('click',()=>{transfer=null;byId('transfer-panel').hidden=true;notice('Anordnung unverändert.');});
byId('undo-layout').addEventListener('click',()=>{if(saving||blocked||!undoStack.length)return;restore(undoStack.pop());dirty=true;render();saveLayout();});
byId('reload-layout').addEventListener('click',async()=>{
  if(saving)return;if(dirty&&!window.confirm('Deinen nicht bestätigten Entwurf verwerfen und den gespeicherten Stand laden?'))return;
  try{await loadDashboard();notice('Gespeichertes Layout geladen.','success');}catch(error){notice(error.message,'error');}
});
byId('retry-layout').addEventListener('click',async()=>{
  if(saving||!layout)return;saving=true;setControls();
  try{
    const remote=await request('/api/dashboard');
    if(JSON.stringify(remote.layout)===JSON.stringify(layout)){
      layoutRevision=remote.revision;await request('/api/display/page',{page_id:pageId,revision:layoutRevision});await waitDisplay(layoutRevision,pageId);
      dirty=false;blocked=false;draft('Am Display gespeichert');notice('Verbindung wiederhergestellt.','success');
    }else if(remote.revision===layoutRevision){saving=false;blocked=false;await saveLayout();}
    else throw new Error('Eine andere Sitzung hat das Layout geändert. Bitte den gespeicherten Stand neu laden.');
  }catch(error){if(layout){blocked=true;notice(error.message,'error');}}
  finally{saving=false;render();}
});
async function settingsAction(work){
  if(settingsBusy||saving)return;settingsBusy=true;
  document.querySelectorAll('#login-panel button,#settings-panel button').forEach(b=>b.disabled=true);
  try{await work();}catch(error){notice(error.message||'Bitte erneut versuchen.','error');}
  finally{settingsBusy=false;document.querySelectorAll('#login-panel button,#settings-panel button').forEach(b=>b.disabled=false);byId('login-form').querySelector('button').disabled=byId('code').disabled;setControls();}
}
byId('login-form').addEventListener('submit',event=>{event.preventDefault();settingsAction(async()=>{const code=byId('code').value;byId('code').value='';await request('/api/login',{code});await loadSettings();if(!blocked)notice('Verbunden. Ordne jetzt deine Widgets an.','success');});});
byId('settings-form').addEventListener('submit',event=>{event.preventDefault();settingsAction(async()=>{
  const selected=Array.from(byId('countries').options).find(o=>o.value.toLocaleLowerCase('de')===byId('country').value.trim().toLocaleLowerCase('de'));
  if(!selected)throw new Error('Bitte ein Land aus der Länderauswahl wählen.');
  const update={location:byId('location').value,country_code:selected.dataset.code,api_key:byId('api-key').value};
  byId('api-key').value='';const result=await request('/api/settings',update);await loadSettings();notice(result.message,'success');
});});
byId('logout').addEventListener('click',()=>settingsAction(async()=>{if(dirty&&!window.confirm('Nicht bestätigten Entwurf verwerfen und abmelden?'))return;await request('/api/logout',{});showLogin('Abgemeldet. Zum erneuten Verbinden einen neuen Code anfordern.',false,false);}));
function schedulePoll(){
  clearTimeout(pollTimer);if(!csrf||!layout||paused||document.hidden)return;
  pollTimer=setTimeout(async()=>{
    if(Date.now()-lastActivity>=IDLE_MS||document.hidden){pausePolling();return;}
    if(!saving&&!blocked)await checkDisplay();
    schedulePoll();
  },2000);
}
async function checkDisplay(){
  try{
    const state=await request('/api/display');
    if(state.error)throw new Error(state.error);
    if(state.viewport&&JSON.stringify(state.viewport)!==JSON.stringify(viewport)){
      viewport=state.viewport;renderBoard();byId('preview-label').textContent=`DEIN DISPLAY · ${viewport.width} × ${viewport.height}`;
    }
    if(state.revision!==layoutRevision){blocked=true;draft('Layout geändert');notice('Eine andere Sitzung hat das Layout geändert. Bitte neu laden.','error');setControls();return false;}
    if(state.page_id!==pageId)draft('Andere Seite am Gerät');
    return true;
  }catch(error){if(layout){draft('Verbindung unterbrochen');notice(error.message,'error');}return false;}
}
function pausePolling(){paused=true;clearTimeout(pollTimer);}
async function resumePolling(){
  if(!csrf||!layout||document.hidden||resuming)return;
  resuming=true;paused=true;
  try{if(await checkDisplay()){paused=false;lastActivity=Date.now();schedulePoll();}}
  finally{resuming=false;}
}
function activity(event){
  const asleep=paused||resuming||Date.now()-lastActivity>=IDLE_MS;
  lastActivity=Date.now();
  if(!csrf||!layout||!asleep||event.target.closest('#reload-layout,#logout,#retry-layout'))return;
  // A gesture cannot be applied to a stale layout while resuming. Focus normally
  // synchronizes before the first gesture; otherwise let the user retry it.
  event.preventDefault();event.stopImmediatePropagation();
  if(!resuming){draft('Aktuellen Stand prüfen …');resumePolling();}
}
for(const kind of ['pointerdown','keydown'])document.addEventListener(kind,activity,{capture:true});
document.addEventListener('pointermove',()=>{if(!paused&&!resuming)lastActivity=Date.now();},{passive:true});
document.addEventListener('visibilitychange',()=>{if(document.hidden)pausePolling();else if(paused)resumePolling();});
window.addEventListener('blur',pausePolling);
window.addEventListener('focus',()=>{if(paused)resumePolling();});
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
settingsAction(async()=>{try{await loadSettings();}catch{if(!csrf)showLogin('Melde dich mit dem Zugangscode der Wetterstation an.');else notice('Der Editor konnte nicht geladen werden. Bitte erneut laden.','error');}});
