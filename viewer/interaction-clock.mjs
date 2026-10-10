// Independent event/hold model from locally verified facts, not application code.
import {durations} from './clock.mjs';
import {candidateRows} from './candidate-clock.mjs';

export const taskStates=Object.freeze(['idle','waving','jumping','failed','waiting','processing','review']);
const eligible=new Set(['idle','processing','waving']);
function validate(props){
  if(!taskStates.includes(props.base)||![null,'run_right','run_left'].includes(props.drag)
      ||typeof props.hover!=='boolean'||typeof props.reduced!=='boolean'
      ||(props.look!==null&&(!Number.isInteger(props.look?.direction)||props.look.direction<0||props.look.direction>=16)))
    throw new Error('Invalid interaction props');
}
export function selectedInteraction(props){
  validate(props);
  const selected=props.drag??(props.hover?'jumping':props.base);
  return {selected,look:eligible.has(selected)?props.look:null,
    reason:props.drag!==null?'drag':props.hover?'hover':'task'};
}
function sequence(selected,reduced){
  const row=candidateRows[selected];
  if(reduced)return {frames:[{state:selected,row,index:0,holdMs:null}],loopAt:null};
  const cells=state=>durations[candidateRows[state]].map((holdMs,index)=>({state,row:candidateRows[state],index,holdMs}));
  const idle=cells('idle');
  if(selected==='idle')return {frames:idle,loopAt:0};
  const action=cells(selected),frames=[...action,...action,...action,...idle];
  return {frames,loopAt:3*action.length};
}

export class InteractionClock{
  #props; #key; #program; #position=0; #due=null; #lastNow=0; #generation=0; #advances=0;
  constructor(props={},now=0){
    this.#props={base:'idle',drag:null,hover:false,look:null,reduced:false,...props};
    this.update({},now,true);
  }
  #time(now){
    if(!Number.isFinite(now)||now<this.#lastNow||now<0)throw new Error('Interaction time must be finite and monotonic');
  }
  update(changes,now,restart=false){
    this.#time(now);
    const props={...this.#props,...changes},resolved=selectedInteraction(props);
    const key={selected:resolved.selected,look:resolved.look,reduced:props.reduced};
    const reset=restart||!this.#key||Object.keys(key).some(field=>key[field]!==this.#key[field]);
    this.#props=props;this.#lastNow=now;
    if(reset){
      this.#key=key;this.#position=0;this.#generation++;this.#advances=0;
      this.#program=key.look!==null
        ?{frames:[{state:'look',row:9+Math.floor(key.look.direction/8),index:key.look.direction%8,holdMs:null}],loopAt:null}
        :sequence(key.selected,key.reduced);
      const hold=this.#program.frames[0].holdMs;
      this.#due=hold===null?null:now+hold;
    }
    return {reset,frame:this.frame()};
  }
  advance(now){
    this.#time(now);this.#lastNow=now;
    if(this.#due===null||now<this.#due)return false;
    this.#position++;
    if(this.#position===this.#program.frames.length)this.#position=this.#program.loopAt;
    const hold=this.#program.frames[this.#position].holdMs;
    // A delayed native callback advances ONE hold, not all missed slots.
    this.#due=now+hold;this.#advances++;
    return true;
  }
  frame(){
    const selected=selectedInteraction(this.#props);
    return {...this.#program.frames[this.#position],selected:selected.selected,reason:selected.reason,
      base:this.#props.base,programPosition:this.#position,deadline:this.#due,
      generation:this.#generation,advances:this.#advances,
      completedAction:this.#key.selected!=='idle'&&this.#program.frames[this.#position].state==='idle',
      static:this.#due===null};
  }
}

export function validateInteractionAtlas(meta){
  const states=['idle','run_right','run_left','waving','jumping','failed','waiting','processing','review'];
  if(meta.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||JSON.stringify(meta.states)!==JSON.stringify(states)||meta.directionCount!==16
      ||JSON.stringify(meta.atlasSize)!=='[1536,2288]'||JSON.stringify(meta.cell)!=='[192,208]'
      ||meta.atlasCoverageComplete!==true||meta.facialGeometryRepair!==false
      ||meta.visualAcceptance!=='pending'||meta.allStateTransitionsAccepted!==false
      ||meta.hostIntegrationVerified!==false||meta.installableFullAtlas!==false||meta.installed!==false
      ||!Array.isArray(meta.actionRows)||meta.actionRows.length!==9
      ||!(/^[A-F0-9]{64}$/.test(meta.atlasRGBAHash)))throw new Error('Interaction preview must use the current unapproved complete atlas');
  meta.actionRows.forEach((entry,row)=>{
    if(entry.state!==states[row]||entry.nativeRow!==row||entry.frameCount!==durations[row].length
        ||entry.visualMotionApproval!=='pending'||!(/^[A-F0-9]{64}$/.test(entry.sourceRowRGBAHash)))
      throw new Error('Interaction atlas row/source boundary mismatch');
  });
  return meta;
}
