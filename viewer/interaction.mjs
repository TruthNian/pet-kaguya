// QA-only abrupt state/overlay inspection. No new desktop pet host or artwork.
import {InteractionClock,validateInteractionAtlas} from './interaction-clock.mjs?v=20261010-interaction-1';
import {paintCel} from './cel-painter.mjs';

const el=id=>document.getElementById(id);
const section=el('interaction-review'),contexts=['interaction-before','interaction-current'].map(id=>el(id).getContext('2d',{alpha:true}));
const media=matchMedia('(prefers-reduced-motion: reduce)');
el('interaction-reduced').checked=media.matches;
let image=null,metadata=null,loading=null,model=null,timer=null,playing=false,virtualTime=0,startedAt=null;
let lastPaint='',paintCount=0;
const now=()=>virtualTime+(startedAt===null?0:performance.now()-startedAt);
function stop(){
  virtualTime=now();startedAt=null;
  if(timer!==null)clearTimeout(timer);
  timer=null;
}
function controls(){
  const frame=model?.frame();
  el('interaction-play').textContent=playing?'暂停切换验收':'播放切换验收';
  el('interaction-play').disabled=!model||(frame.static&&!playing);
  el('interaction-next').disabled=!model||frame.static;
  el('interaction-reset').disabled=!model;
}
function draw(note=''){
  if(!model)return;
  const frame=model.frame(),key=`${frame.row}:${frame.index}`;
  if(key!==lastPaint){paintCel(contexts[1],image,frame.index,frame.row);lastPaint=key;paintCount++;}
  el('interaction-current-title').textContent=`当前：${frame.state} 第 ${frame.index+1} 格`;
  const playback=frame.static?`静态保持${playing?'（取消静态覆盖后续播）':''}`:playing?'按停留链播放':'暂停/单槽检查';
  el('interaction-status').textContent=`底层 ${frame.base} · 覆盖 ${frame.reason} · 选择 ${frame.selected} · 显示 ${frame.state} r${frame.row} c${frame.index} · ${frame.static?'静态方向/减少动态':`原生停留 ${frame.holdMs} ms`}${frame.completedAction?' · 三轮已回慢idle':''} · ${playback} · ${paintCount} 次当前绘制${note?' · '+note:''} · 图集 ${metadata.atlasRGBAHash.slice(0,12)} · 独立规则验收，非宿主录像/完整通过`;
  controls();
}
function schedule(){
  if(!playing||!model||!section.open||model.frame().static)return;
  if(startedAt===null)startedAt=performance.now();
  timer=setTimeout(()=>{
    timer=null;model.advance(now());draw();schedule();
  },Math.max(1,model.frame().deadline-now()));
}
function freezeBefore(frame){
  paintCel(contexts[0],image,frame.index,frame.row);
  el('interaction-before-title').textContent=`切换前冻结：${frame.state} 第 ${frame.index+1} 格`;
}
function change(changes,restart=false){
  if(!model)return;
  stop();
  const before=model.frame(),result=model.update(changes,now(),restart);
  if(result.reset)freezeBefore(before);
  draw(result.reset?'有效属性变化：立即从新选择首格开始':'有效属性不变：保留当前槽，不重启');
  schedule();
}
function size(){
  const width=Number(el('interaction-size').value);
  for(const id of ['interaction-before','interaction-current']){
    el(id).style.width=`${width}px`;el(id).style.height=`${Math.round(width*208/192)}px`;
  }
}
async function load(){
  if(model||loading)return loading;
  loading=(async()=>{
    const root='../candidates/phase5/global';
    const response=await fetch(`${root}/build.json`,{cache:'no-cache'});
    if(!response.ok)throw new Error('global interaction atlas unavailable');
    metadata=validateInteractionAtlas(await response.json());
    image=new Image();image.src=`${root}/spritesheet.webp?v=${metadata.atlasRGBAHash}`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==2288)throw new Error('global interaction canvas mismatch');
    const look=el('interaction-look').value;
    model=new InteractionClock({base:el('interaction-task').value,
      drag:el('interaction-drag').value==='none'?null:el('interaction-drag').value,
      hover:el('interaction-hover').checked,look:look==='none'?null:Object.freeze({direction:Number(look)}),
      reduced:el('interaction-reduced').checked},0);
    freezeBefore(model.frame());size();draw('未安装、不补间；左侧不是同动作同步参照');
  })().catch(error=>{el('interaction-status').textContent=`切换验收加载失败：${error.message}`;console.error(error);})
    .finally(()=>{loading=null;});
  return loading;
}
el('interaction-task').addEventListener('change',()=>change({base:el('interaction-task').value}));
el('interaction-drag').addEventListener('change',()=>change({drag:el('interaction-drag').value==='none'?null:el('interaction-drag').value}));
el('interaction-hover').addEventListener('change',()=>change({hover:el('interaction-hover').checked}));
el('interaction-look').addEventListener('change',()=>change({look:el('interaction-look').value==='none'?null:Object.freeze({direction:Number(el('interaction-look').value)})}));
el('interaction-reduced').addEventListener('change',()=>change({reduced:el('interaction-reduced').checked}));
media.addEventListener('change',event=>{el('interaction-reduced').checked=event.matches;change({reduced:event.matches});});
el('interaction-size').addEventListener('change',size);
el('interaction-background').addEventListener('change',()=>{el('interaction-stage').className=`stage ${el('interaction-background').value}`;});
el('interaction-play').addEventListener('click',()=>{stop();playing=!playing;draw();schedule();});
el('interaction-next').addEventListener('click',()=>{
  if(!model||model.frame().static)return;
  stop();playing=false;virtualTime=Math.max(virtualTime,model.frame().deadline);
  model.advance(virtualTime);draw('手动走一槽，不插值、不跳过中间格');
});
el('interaction-reset').addEventListener('click',()=>change({},true));
section.addEventListener('toggle',async()=>{
  if(section.open){await load();schedule();}
  else{stop();playing=false;draw('收起验收区：暂停，重新展开不会自动播放');}
});
window.addEventListener('pagehide',()=>{stop();playing=false;});
if(section.open)await load();
