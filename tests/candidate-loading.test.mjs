import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

// Exercise the real page entry point, not just comparison policy. Image decode
// and canvas are stubs here; visual correctness is checked in the browser.
test('current steps load without retired references; hop contact loads only when selected',async()=>{
  const names=['document','window','Image','fetch','matchMedia'];
  const originals=new Map(names.map(name=>[name,Object.getOwnPropertyDescriptor(globalThis,name)]));
  const elements=new Map(),requests=[],decodes=[],painted=[];
  function element(id){
    if(!elements.has(id))elements.set(id,{
      value:id==='idle-action'?'idle':id==='idle-size'?'113':'',checked:false,
      disabled:false,textContent:'',style:{},handlers:new Map(),
      addEventListener(type,handler){this.handlers.set(type,handler);},
      getContext(){return {clearRect(){},drawImage(image){painted.push({id,src:image.src});}};}
    });
    return elements.get(id);
  }
  try{
    globalThis.document={hidden:false,getElementById:element,addEventListener(){}};
    globalThis.window={addEventListener(){}};
    globalThis.matchMedia=()=>({matches:true,addEventListener(){}});
    globalThis.Image=class {
      naturalWidth=1536;naturalHeight=208;
      async decode(){decodes.push(this.src);}
    };
    globalThis.fetch=async path=>{
      requests.push(path);
      return {ok:true,json:async()=>JSON.parse(readFileSync(new URL(path,new URL('../viewer/candidate.mjs',import.meta.url)),'utf8'))};
    };
    await import('../viewer/candidate.mjs?loading-regression');
    const select=async state=>{
      element('idle-action').value=state;
      await element('idle-action').handlers.get('change')();
      assert.match(element('idle-status').textContent,/减少动态/);
      assert.doesNotMatch(element('idle-status').textContent,/加载失败/);
    };
    for(const state of ['run_right','run_left']){
      await select(state);
      assert.equal(element('idle-comparison').value,'idle');
      assert.equal(element('rigid-reference-choice').disabled,true);
      assert(painted.some(p=>p.id==='idle-animated'&&p.src.includes(`/phase5/${state}/strip.webp`)));
    }
    assert(!requests.some(path=>path.includes('/locomotion-rigid/')));
    assert(!decodes.some(path=>path.includes('/locomotion-rigid/')));
    await select('jumping');
    assert.equal(element('idle-comparison').value,'height');
    assert(!requests.some(path=>path.includes('contact-proof.json')));
    element('idle-comparison').value='contact';
    await element('idle-comparison').handlers.get('change')();
    assert(requests.some(path=>path.includes('contact-proof.json')));
    assert.doesNotMatch(element('idle-status').textContent,/加载失败/);
  }finally{
    for(const [name,descriptor] of originals)
      if(descriptor)Object.defineProperty(globalThis,name,descriptor);else delete globalThis[name];
  }
});
