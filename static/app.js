(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = {analysis: null, imageId: null, selected: null, busy: false, history: [], generation: 0};
  const svgNS = 'http://www.w3.org/2000/svg';
  const element = (tag, className, text) => {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const svgElement = (tag, attributes) => {
    const e = document.createElementNS(svgNS, tag);
    Object.entries(attributes).forEach(([key, value]) => e.setAttribute(key, value));
    return e;
  };
  function notice(text) { $('notice').textContent = text; $('notice').classList.toggle('hidden', !text); }
  function controls() {
    const enabled = Boolean(state.imageId) && !state.busy;
    $('questionInput').disabled = !enabled;
    $('sendButton').disabled = !enabled;
    $('demoButton').disabled = state.busy;
    $('changeImage').disabled = state.busy;
    $('exportButton').disabled = !state.history.length;
    document.querySelectorAll('[data-question]').forEach(e => e.disabled = !enabled);
  }
  async function api(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Có lỗi xảy ra. Bạn thử lại nhé.');
    return data;
  }
  function addMessage(role, text, answer) {
    $('messages').querySelector('.welcome')?.remove();
    const item = element('div', `message ${role}`);
    item.append(element('span', 'message-label', role === 'user' ? 'BẠN' : 'NHÌN & HỎI'));
    item.append(element('div', 'bubble', text));
    if (answer?.evidence?.length) {
      answer.evidence.forEach(ev => {
        const card = element('div', 'evidence');
        const crop = element('img'); crop.src = ev.crop; crop.alt = `Vùng ${ev.field === 'shirt' ? 'áo' : 'quần'} của người ${ev.person_id}`;
        const info = element('div');
        info.append(element('b', '', `Vùng ${ev.field === 'shirt' ? 'áo' : 'quần'} · Người ${ev.person_id}`));
        info.append(element('p', '', ev.available ? `Màu chính chiếm khoảng ${Math.round(ev.coverage * 100)}% vùng này.` : 'Vùng trang phục chưa đủ rõ để kết luận.'));
        card.append(crop, info); item.append(card);
      });
    }
    if (answer?.status === 'clarify' && answer.person_ids?.length) {
      const row = element('div', 'select-shortcuts');
      answer.person_ids.forEach(id => {
        const b = element('button', '', `Người ${id}`);
        b.type = 'button'; b.addEventListener('click', () => selectPerson(id)); row.append(b);
      }); item.append(row);
    }
    $('messages').append(item); $('messages').scrollTop = $('messages').scrollHeight;
  }
  function selectPerson(id) {
    if (!state.analysis?.people.some(p => p.id === id)) return;
    state.selected = id;
    $('selectionLabel').textContent = `Đang chọn người ${id}. Bạn có thể hỏi “Áo màu gì?”`;
    $('selection').classList.remove('hidden');
    document.querySelectorAll('.person-rect').forEach(e => e.classList.toggle('selected', Number(e.dataset.id) === id));
    document.querySelectorAll('.person-card').forEach(e => e.classList.toggle('active', Number(e.dataset.id) === id));
    $('questionInput').focus();
  }
  function clearSelection() {
    state.selected = null; $('selection').classList.add('hidden');
    document.querySelectorAll('.selected, .active').forEach(e => e.classList.remove('selected', 'active'));
  }
  function renderPeople() {
    const analysis = state.analysis;
    $('peopleGrid').replaceChildren(); $('boxes').replaceChildren();
    $('boxes').setAttribute('viewBox', `0 0 ${analysis.width} ${analysis.height}`);
    analysis.people.forEach(p => {
      const [x1,y1,x2,y2] = p.box;
      const rect = svgElement('rect', {x:x1,y:y1,width:x2-x1,height:y2-y1,rx:4,class:'person-rect',tabindex:0,role:'button','aria-label':`Chọn người ${p.id}`, 'data-id':p.id});
      rect.addEventListener('click', () => selectPerson(p.id));
      rect.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') {e.preventDefault();selectPerson(p.id);} });
      const labelWidth = Math.max(30, analysis.width / 22), labelHeight = Math.max(28, analysis.height / 35);
      const label = svgElement('rect', {x:x1,y:Math.max(0,y1-labelHeight),width:labelWidth,height:labelHeight,rx:4,class:'person-label'});
      const number = svgElement('text', {x:x1+labelWidth/2,y:Math.max(0,y1-labelHeight)+labelHeight*.74,'text-anchor':'middle',class:'person-number'});
      number.style.fontSize = `${labelHeight*.65}px`; number.textContent = p.id;
      $('boxes').append(rect,label,number);
      const card = element('button','person-card');card.type='button';card.dataset.id=p.id;
      card.setAttribute('aria-label',`Chọn người ${p.id}, ${p.position}`);
      const image=element('img');image.src=p.crop;image.alt=`Người ${p.id}`;
      const details=element('div');details.append(element('h3','',`Người ${p.id}`),element('div','position',p.position));
      ['shirt','pants'].forEach(field=>{
        const a=element('div','attribute');const dot=element('span','swatch');
        dot.style.background=p[field].available ? p[field].colors[0].hex : '#d7ded2';
        a.append(dot,document.createTextNode(`${field==='shirt'?'Áo':'Quần'}: ${p[field].label}`));details.append(a);
      });card.append(image,details);card.addEventListener('click',()=>selectPerson(p.id));$('peopleGrid').append(card);
    });
    $('peopleHeading').textContent=`${analysis.people.length} người đã phát hiện`;
    $('peopleSection').classList.toggle('hidden',!analysis.people.length);
  }
  async function loadImage(file, demo = false) {
    if (state.busy) return;
    if (file && file.size > 8*1024*1024) {notice('Ảnh vượt quá 8 MB. Bạn chọn ảnh nhỏ hơn nhé.');return;}
    const generation=++state.generation;state.busy=true;controls();notice('');
    const oldId=state.imageId;state.imageId=null;state.analysis=null;clearSelection();
    $('dropZone').classList.add('hidden');$('imageStage').classList.remove('hidden');$('analyzing').classList.remove('hidden');
    $('imageMeta').classList.add('hidden');$('peopleSection').classList.add('hidden');$('boxes').replaceChildren();
    let preview=null;
    if (file) {preview=URL.createObjectURL(file);$('mainImage').src=preview;}
    if (oldId) fetch(`/api/image/${oldId}`,{method:'DELETE'}).catch(()=>{});
    try {
      let data;
      if(demo) data=await api('/api/demo',{method:'POST'});
      else {const body=new FormData();body.append('image',file);data=await api('/api/analyze',{method:'POST',body});}
      if (generation!==state.generation) return;
      state.analysis=data;state.imageId=data.image_id;state.history=[];
      $('mainImage').src=data.image;$('mainImage').alt=demo?'Ảnh mẫu đường phố':'Ảnh của bạn';
      $('messages').replaceChildren();$('changeImage').classList.remove('hidden');$('imageMeta').classList.remove('hidden');
      $('imageStats').textContent=`${data.people.length} người được phát hiện · ${data.width} × ${data.height}`;
      renderPeople();
      addMessage('assistant',data.people.length ? `Mình đã phát hiện ${data.people.length} người và đánh số từ trái sang phải. Bạn muốn hỏi về ai?` : 'Mình chưa phát hiện được người trong ảnh. Bạn có thể thử một ảnh có người rõ và lớn hơn.');
    } catch(error) {
      notice(error.message);$('imageStage').classList.add('hidden');$('dropZone').classList.remove('hidden');$('changeImage').classList.add('hidden');
    } finally {
      if(preview)URL.revokeObjectURL(preview);
      state.busy=false;$('analyzing').classList.add('hidden');controls();
    }
  }
  async function ask(question) {
    question=question.trim();if(!question||state.busy||!state.imageId)return;
    notice('');state.busy=true;controls();$('questionInput').value='';addMessage('user',question);
    const pending=element('div','message assistant');pending.append(element('div','bubble','Đang xem lại bức ảnh…'));$('messages').append(pending);
    try {
      const answer=await api('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_id:state.imageId,question,selected_person:state.selected})});
      pending.remove();addMessage('assistant',answer.answer,answer);
      state.history.push({question,answer:answer.answer,intent:answer.intent,person_ids:answer.person_ids,time:new Date().toISOString()});
    } catch(error) {pending.remove();addMessage('assistant',error.message);}
    finally {state.busy=false;controls();$('questionInput').focus();}
  }
  $('dropZone').addEventListener('click',()=>{if(!state.busy)$('fileInput').click();});
  $('dropZone').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('fileInput').click();}});
  $('changeImage').addEventListener('click',()=>$('fileInput').click());
  $('fileInput').addEventListener('change',e=>{if(e.target.files[0])loadImage(e.target.files[0]);e.target.value='';});
  ['dragenter','dragover'].forEach(name=>$('dropZone').addEventListener(name,e=>{e.preventDefault();$('dropZone').classList.add('dragging');}));
  ['dragleave','drop'].forEach(name=>$('dropZone').addEventListener(name,e=>{e.preventDefault();$('dropZone').classList.remove('dragging');}));
  $('dropZone').addEventListener('drop',e=>{if(e.dataTransfer.files[0])loadImage(e.dataTransfer.files[0]);});
  $('demoButton').addEventListener('click',()=>loadImage(null,true));
  $('questionForm').addEventListener('submit',e=>{e.preventDefault();ask($('questionInput').value);});
  $('questionInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask(e.target.value);}});
  document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>ask(button.dataset.question)));
  $('clearSelection').addEventListener('click',clearSelection);
  $('exportButton').addEventListener('click',()=>{
    const blob=new Blob([JSON.stringify({created_at:new Date().toISOString(),messages:state.history},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='nhin-va-hoi.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  api('/api/status').then(data=>{$('readyLabel').textContent=data.ready?(data.public_deployment?'Sẵn sàng · Trực tuyến':'Sẵn sàng · Xử lý tại máy'):'Cần tải mô hình';if(!data.ready)notice('Chạy python download_assets.py để chuẩn bị mô hình.');}).catch(()=>{$('readyLabel').textContent='Chưa kết nối';});
  controls();
})();
