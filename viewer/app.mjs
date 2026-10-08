import {frameAt,lookIndex,cycles,states} from './clock.mjs';
const el=id=>document.getElementById(id);
const canvases=[el('old'),el('new')];
const ctx=canvases.map(c=>c.getContext('2d',{alpha:true}));
let assets=[],elapsed=0,lastTime=null,request=null,paused=false,pointer=null,lastKey='';
let paintCount=0,windowStart=performance.now(),switches=0,previousCell='',drawTimes=[];
const settings=()=>({loop:el('loop').checked,reduced:el('reduced').checked||matchMedia('(prefers-reduced-motion: reduce)').matches,
  look:el('look').checked&&pointer!==null?lookIndex(pointer.x,pointer.y):null});
function resize(){
  const size=Number(el('size').value),height=Math.round(size*208/192),dpr=Math.min(devicePixelRatio||1,3);
  canvases.forEach(c=>{c.width=Math.round(size*dpr);c.height=Math.round(height*dpr);c.style.width=`${size}px`;c.style.height=`${height}px`;});
  lastKey='';draw();
}
function draw(){
  if(assets.length!==2) return;
  const frame=frameAt(el('state').value,elapsed,settings());
  const key=`${frame.row}:${frame.col}:${el('smooth').checked}:${canvases[0].width}`;
  if(key===lastKey)return;
  const start=performance.now();
  ctx.forEach((c,i)=>{
    c.clearRect(0,0,canvases[i].width,canvases[i].height);
    c.imageSmoothingEnabled=el('smooth').checked;c.imageSmoothingQuality='high';
    c.drawImage(assets[i],frame.col*192,frame.row*208,192,208,0,0,canvases[i].width,canvases[i].height);
  });
  lastKey=key;paintCount++;drawTimes.push(performance.now()-start);if(drawTimes.length>200)drawTimes.shift();
  const cell=`${frame.row}:${frame.col}`;
  if(previousCell!==cell){switches++;previousCell=cell;}
  const mean=drawTimes.reduce((a,b)=>a+b,0)/drawTimes.length;
  const period=(performance.now()-windowStart)/1000;
  el('status').textContent=`${frame.kind==='look'?'方向覆盖':states[frame.row]} · r${frame.row} c${frame.col} · ${Math.round(elapsed)} ms · ${cycles[frame.row]??'静态'} ms/周期 · 绘制调用均值 ${mean.toFixed(2)} ms（不含 GPU 合成） · ${paintCount} 次重绘 / ${period.toFixed(1)} s（不是原生 FPS）`;
}
function tick(now){
  request=null;
  if(!paused&&!document.hidden){if(lastTime!==null)elapsed+=now-lastTime;lastTime=now;draw();request=requestAnimationFrame(tick);}
}
function schedule(){if(!paused&&!document.hidden&&request===null){lastTime=null;request=requestAnimationFrame(tick);}}
function restart(){elapsed=0;lastTime=null;lastKey='';draw();schedule();}
el('state').addEventListener('change',restart);el('size').addEventListener('change',resize);
for(const id of ['loop','look','reduced','smooth'])el(id).addEventListener('change',()=>{lastKey='';draw();});
el('background').addEventListener('change',()=>el('stage').className=`stage ${el('background').value}`);
el('restart').addEventListener('click',restart);
el('pause').addEventListener('click',()=>{paused=!paused;el('pause').textContent=paused?'继续':'暂停';if(paused&&request!==null){cancelAnimationFrame(request);request=null;}schedule();});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&request!==null){cancelAnimationFrame(request);request=null;}lastTime=null;schedule();});
el('stage').addEventListener('pointermove',e=>{
  const c=canvases[e.target.closest('article')===canvases[0].parentElement?0:1];
  const b=c.getBoundingClientRect();pointer={x:e.clientX-(b.left+b.width/2),y:e.clientY-(b.top+b.height/2)};draw();
});
el('stage').addEventListener('pointerleave',()=>{pointer=null;lastKey='';draw();});
async function load(url){const img=new Image();img.src=url;await img.decode();if(img.naturalWidth!==1536||img.naturalHeight!==2288)throw new Error('Invalid atlas dimensions');return img;}
try{
  assets=await Promise.all([load('../baseline/phase2/spritesheet.webp'),load('../pet/spritesheet.webp')]);
  resize();schedule();
  // Read-only diagnostics for repeatable browser checks; not app automation.
  window.kaguyaLab={snapshot:()=>({loaded:assets.length,state:el('state').value,
    elapsed,paused,hidden:document.hidden,frame:frameAt(el('state').value,elapsed,settings()),
    paintCount,switches,drawTimes:[...drawTimes],canvasSizes:canvases.map(c=>[c.width,c.height])})};
}catch(e){el('status').textContent=`加载失败：${e.message}。请从仓库根目录启动 HTTP 服务器。`;console.error(e);}
