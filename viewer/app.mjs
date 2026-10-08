import {frameAt,lookIndex,cycles,states} from './clock.mjs';
import {baselineUrls,baselineLabels,reviewStates,reviewCell} from './review.mjs';
const el=id=>document.getElementById(id);
const canvases=[el('old'),el('new')];
const ctx=canvases.map(c=>c.getContext('2d',{alpha:true}));
let atlases={},atlasRequests={},staticFrames=[],elapsed=0,lastTime=null,request=null,paused=false,pointer=null,lastKey='',loadEpoch=0,reviewLoading=null;
let paintCount=0,windowStart=performance.now(),switches=0,previousCell='',drawTimes=[];
const isStatic=()=>el('candidate').value==='static4';
const ready=()=>staticFrames.length===9&&atlases[el('baseline').value]&&(isStatic()||atlases.phase3);
const settings=()=>({loop:el('loop').checked,reduced:el('reduced').checked||matchMedia('(prefers-reduced-motion: reduce)').matches,
  look:el('look').checked&&pointer!==null?lookIndex(pointer.x,pointer.y):null});
function resize(){
  const size=Number(el('size').value),height=Math.round(size*208/192),dpr=Math.min(devicePixelRatio||1,3);
  canvases.forEach(c=>{c.width=Math.round(size*dpr);c.height=Math.round(height*dpr);c.style.width=`${size}px`;c.style.height=`${height}px`;});
  lastKey='';draw();
}
function draw(){
  if(!ready())return;
  const state=el('state').value,baseline=el('baseline').value;
  const frame=isStatic()?reviewCell(state,baseline):frameAt(state,elapsed,settings());
  const key=`${baseline}:${el('candidate').value}:${state}:${frame.row}:${frame.col}:${el('smooth').checked}:${canvases[0].width}`;
  if(key===lastKey)return;
  const start=performance.now();
  ctx.forEach((c,i)=>{
    c.clearRect(0,0,canvases[i].width,canvases[i].height);
    c.imageSmoothingEnabled=el('smooth').checked;c.imageSmoothingQuality='high';
    if(i===1&&isStatic()){
      c.drawImage(staticFrames[reviewStates.indexOf(state)],0,0,canvases[i].width,canvases[i].height);
    }else{
      c.drawImage(i===0?atlases[baseline]:atlases.phase3,frame.col*192,frame.row*208,192,208,0,0,canvases[i].width,canvases[i].height);
    }
  });
  lastKey=key;paintCount++;drawTimes.push(performance.now()-start);if(drawTimes.length>200)drawTimes.shift();
  const cell=`${frame.row}:${frame.col}`;
  if(previousCell!==cell){switches++;previousCell=cell;}
  const mean=drawTimes.reduce((a,b)=>a+b,0)/drawTimes.length;
  const period=(performance.now()-windowStart)/1000;
  el('status').textContent=isStatic()
    ?`${state} · 已否决静态试作，不是动画 · 左侧 ${baselineLabels[baseline]} r${frame.row} c${frame.col} · 右侧 ${frame.row===1||frame.row===2?'侧向源姿势尚未重建':'机械共用头部不等于整体结构正确'} · ${paintCount} 次绘制`
    :`${frame.kind==='look'?'方向覆盖':states[frame.row]} · r${frame.row} c${frame.col} · ${Math.round(elapsed)} ms · ${cycles[frame.row]??'静态'} ms/周期 · 绘制调用均值 ${mean.toFixed(2)} ms（不含 GPU 合成） · ${paintCount} 次重绘 / ${period.toFixed(1)} s（不是原生 FPS）`;
}
function tick(now){
  request=null;
  if(!paused&&!document.hidden&&!isStatic()&&el('history-review').open){
    if(lastTime!==null)elapsed+=now-lastTime;lastTime=now;draw();request=requestAnimationFrame(tick);
  }
}
function schedule(){if(!paused&&!document.hidden&&!isStatic()&&el('history-review').open&&request===null){lastTime=null;request=requestAnimationFrame(tick);}}
function cancel(){if(request!==null){cancelAnimationFrame(request);request=null;}lastTime=null;}
function restart(){elapsed=0;lastTime=null;lastKey='';draw();schedule();}
async function mode(){
  cancel();elapsed=0;pointer=null;
  const epoch=++loadEpoch;
  for(const id of ['loop','look','reduced','pause','restart'])el(id).disabled=isStatic();
  el('baseline-title').textContent=baselineLabels[el('baseline').value];
  el('candidate-title').textContent=isStatic()?'Phase 4 静态试作 · 已否决':'Phase 3 动画 · 旧候选';
  lastKey='';
  if(!ready()){
    ctx.forEach((c,i)=>c.clearRect(0,0,canvases[i].width,canvases[i].height));
    el('status').textContent='正在解码所选基准…';
  }
  try{
    await Promise.all([ensureAtlas(el('baseline').value),...(!isStatic()?[ensureAtlas('phase3')]:[])]);
    if(epoch!==loadEpoch)return;
    draw();schedule();
  }catch(e){if(epoch===loadEpoch)el('status').textContent=`加载失败：${e.message}`;console.error(e);}
}
el('state').addEventListener('change',restart);el('size').addEventListener('change',resize);
el('baseline').addEventListener('change',mode);el('candidate').addEventListener('change',mode);
for(const id of ['loop','look','reduced','smooth'])el(id).addEventListener('change',()=>{lastKey='';draw();});
el('background').addEventListener('change',()=>el('stage').className=`stage ${el('background').value}`);
el('restart').addEventListener('click',restart);
el('pause').addEventListener('click',()=>{paused=!paused;el('pause').textContent=paused?'继续':'暂停';if(paused)cancel();schedule();});
document.addEventListener('visibilitychange',()=>{if(document.hidden)cancel();lastTime=null;schedule();});
el('stage').addEventListener('pointermove',e=>{
  if(isStatic())return;
  const c=canvases[e.target.closest('article')===canvases[0].parentElement?0:1];
  const b=c.getBoundingClientRect();pointer={x:e.clientX-(b.left+b.width/2),y:e.clientY-(b.top+b.height/2)};draw();
});
el('stage').addEventListener('pointerleave',()=>{pointer=null;lastKey='';draw();});
async function load(url,width,height){
  const img=new Image();img.src=url;await img.decode();
  if(img.naturalWidth!==width||img.naturalHeight!==height)throw new Error(`Invalid asset dimensions: ${url}`);return img;
}
async function ensureAtlas(key){
  if(atlases[key])return atlases[key];
  if(!atlasRequests[key])atlasRequests[key]=load(baselineUrls[key],1536,2288)
    .then(img=>{atlases[key]=img;delete atlasRequests[key];return img;})
    .catch(e=>{delete atlasRequests[key];throw e;});
  return atlasRequests[key];
}
async function initializeHistoricalReview(){
  if(reviewLoading)return reviewLoading;
  reviewLoading=(async()=>{
    if(staticFrames.length!==9)staticFrames=await Promise.all(reviewStates.map(name=>load(`../candidates/phase4/static/${name}.png`,192,208)));
    resize();await mode();
  })().catch(e=>{el('status').textContent=`加载失败：${e.message}。请从仓库根目录启动 HTTP 服务器。`;console.error(e);})
    .finally(()=>{reviewLoading=null;});
  return reviewLoading;
}
el('history-review').addEventListener('toggle',()=>{if(el('history-review').open)initializeHistoricalReview();else cancel();});
  window.kaguyaLab={snapshot:()=>({loaded:Object.keys(atlases).length,staticLoaded:staticFrames.length,
    baseline:el('baseline').value,candidate:el('candidate').value,state:el('state').value,
    elapsed,paused,hidden:document.hidden,scheduled:request!==null,
    frame:isStatic()?reviewCell(el('state').value,el('baseline').value):frameAt(el('state').value,elapsed,settings()),
    paintCount,switches,drawTimes:[...drawTimes],canvasSizes:canvases.map(c=>[c.width,c.height])})};
if(el('history-review').open)initializeHistoricalReview();
