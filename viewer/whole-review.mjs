import {reviewSchedule} from './whole-review-clock.mjs';
import {paintCel} from './cel-painter.mjs';

const el=id=>document.getElementById(id);
const steps=reviewSchedule(),contexts=[...document.querySelectorAll('canvas')].map(c=>c.getContext('2d',{alpha:true}));
const total=steps.reduce((n,step)=>n+step.holdMs,0),prefix=[];
steps.reduce((n,step)=>{prefix.push(n);return n+step.holdMs;},0);
let atlas,position=0,timer=null,playing=false,deadline=0,remaining=steps[0].holdMs,lastKey;
function cancel(){if(timer!==null)clearTimeout(timer);timer=null;}
function draw(){
  const step=steps[position],key=`${step.row}:${step.index}`;
  if(key!==lastKey){contexts.forEach(context=>paintCel(context,atlas,step.index,step.row));lastKey=key;}
  el('chapter').value=step.chapter;
  el('state').textContent=step.state==='look'?`视线 ${step.direction+1}/16 · 原图眼内微变形`
    :step.after?`回到 idle · ${step.after==='look'?'视线演示':step.after+'三轮'}结束`
    :`${step.state} · 第${step.index+1}格${step.row===0?'':` · 第${step.cycle}/3轮`}`;
  el('progress').value=prefix[position]/total;
  el('status').textContent=`${playing?'播放中':'已暂停'} · 本格${step.holdMs}ms${step.state==='look'?'（演示设置）':'（原生计划）'} · 两尺寸×明暗同格 · 无补间 · 独立验收页，非宿主加载证明`;
  el('pause').textContent=playing?'暂停演示':'播放演示';
}
function schedule(){
  deadline=performance.now()+remaining;
  timer=setTimeout(()=>{
    timer=null;
    if(position===steps.length-1){playing=false;remaining=steps[position].holdMs;draw();el('progress').value=1;el('status').textContent='完整观看结束 · 当前整套观感已认可；实际部署另见记录，任意切换与性能不据此验证';return;}
    position++;remaining=steps[position].holdMs;draw();schedule();
  },remaining);
}
function stop(){if(playing){remaining=Math.max(0,deadline-performance.now());playing=false;cancel();draw();}}
function start(){if(document.hidden)return;playing=true;draw();schedule();}
el('pause').addEventListener('click',()=>playing?stop():start());
el('replay').addEventListener('click',()=>{cancel();position=0;remaining=steps[0].holdMs;playing=false;start();});
el('chapter').addEventListener('change',()=>{cancel();position=steps.findIndex(step=>step.chapter===el('chapter').value);remaining=steps[position].holdMs;draw();if(playing)schedule();});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
addEventListener('pagehide',()=>stop());
try{
  const base='../candidates/phase5/global/';
  const metadata=await (await fetch(base+'build.json',{cache:'no-store'})).json();
  if(metadata.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||metadata.visualAcceptance!=='pending'||metadata.installed!==false||metadata.generatedFromRejectedSources!==false
      ||metadata.cell.join(',')!=='192,208'||metadata.directionCount!==16)
    throw new Error('现用图集来源或开发边界不符');
  const blob=await (await fetch(base+'spritesheet.webp',{cache:'no-store'})).blob();
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))]
    .map(n=>n.toString(16).padStart(2,'0')).join('').toUpperCase();
  const receipt=await (await fetch('../sources/canonical/whole-review-acceptance-20261011.json',{cache:'no-store'})).json();
  if(receipt.scope!=='current-whole-review-visual-acceptance'||receipt.visualAcceptance!=='accepted'
      ||receipt.atlasSHA256!==hash||receipt.atlasRGBAHash!==metadata.atlasRGBAHash
      ||receipt.motherSHA256!==metadata.sourceSha256)
    throw new Error('认可记录与当前图集不一致，不能继承整套观感批准');
  el('acceptance').textContent='2026-10-11：当前整套观感已获用户认可，精确图集哈希已核对。真实宿主加载、任意中断与性能不在此次视觉批准内。';
  atlas=await createImageBitmap(blob);
  if(atlas.width!==1536||atlas.height!==2288)throw new Error('原生图集尺寸不符');
  draw();['replay','pause','chapter'].forEach(id=>el(id).disabled=false);
}catch(error){cancel();playing=false;el('state').textContent='无法载入现用图集';el('status').textContent=error.message;}
