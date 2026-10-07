const initALAQTAR = () => {
 const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s), wa='9647809000845';
 const nav=$('.nav'),toggle=$('.menu-toggle'),ret=$('.return-field'),toast=$('#toast');
 $('#year').textContent=new Date().getFullYear();
 if(toggle&&nav){toggle.onclick=()=>{const o=nav.classList.toggle('open');toggle.textContent=o?'✕':'☰';toggle.setAttribute('aria-expanded',o)};$$('.nav a').forEach(a=>a.onclick=()=>nav.classList.remove('open'))}
 $$('input[name="trip"]').forEach(r=>r.onchange=()=>{if(ret)ret.style.display=$('input[name="trip"]:checked').value==='oneway'?'none':'flex'});
 const show=m=>{toast.textContent=m;toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),2800)};
 const openWA=service=>window.open(`https://wa.me/${wa}?text=${encodeURIComponent('مرحباً، أرغب بطلب: '+service)}`,'_blank','noopener');
 $$('.order-btn,.visa-order').forEach(b=>b.onclick=()=>{const s=b.dataset.service||'خدمة';$('#serviceSelect').value=s.includes('تأشيرة')?'تأشيرة':s.includes('رخص')?'رخصة قيادة دولية':s.includes('عرض')?'عرض سياحي':'خدمة أخرى';$('#request').scrollIntoView({behavior:'smooth'});$('#notes').value=s});
 $('#requestForm').onsubmit=async e=>{
  e.preventDefault();
  const name=$('#customerName').value.trim();
  const phone=$('#customerPhone').value.trim();
  const service=$('#serviceSelect').value;
  const notes=$('#notes').value.trim();
  const files=$('#documents').files.length;
  const btn=e.currentTarget.querySelector('button[type="submit"]');

  if(!name||!phone||!service){
   show('يرجى إكمال الاسم ورقم الهاتف والخدمة.');
   return;
  }

  btn.disabled=true;
  const oldText=btn.textContent;
  btn.textContent='جارٍ إرسال الطلب...';

  try{
 const formData = new FormData();

formData.append('customer_name', name);
formData.append('phone', phone);
formData.append('service', service);
formData.append('notes', notes);

const selectedFiles = $('#documents').files;

for (const file of selectedFiles) {
  formData.append('documents', file);
}

const response = await fetch(
  'https://alaqtartravel-production.up.railway.app/api/orders',
  {
    method: 'POST',
    body: formData
  }
);  

   const data=await response.json();

   if(!response.ok||!data.ok){
    throw new Error(data.error||'Request failed');
   }

   const msg=`مرحباً، تم تقديم طلب لدى الأقطار للسفر والسياحة.\nرقم الطلب: ${data.order_no}\nالاسم: ${name}\nالهاتف: ${phone}\nالخدمة: ${service}\nعدد الملفات المختارة: ${files}\nملاحظات: ${notes||'-'}\n\nملاحظة: المستمسكات المختارة لم تُرفع بعد، وسيتم إرسالها حسب تعليمات الشركة.`;

   show(`تم تسجيل الطلب بنجاح: ${data.order_no}`);
   window.open(`https://wa.me/${wa}?text=${encodeURIComponent(msg)}`,'_blank','noopener');
   e.currentTarget.reset();
  }catch(err){
   console.error(err);
   show('تعذر إرسال الطلب. يرجى المحاولة مرة أخرى.');
  }finally{
   btn.disabled=false;
   btn.textContent=oldText;
  }
 };
 $('#flightSearchBtn').onclick=()=>show('البحث المباشر سيتفعّل بعد ربط مزود حجز الطيران API.');
 let usd=false;$('#currencyBtn').onclick=()=>{usd=!usd;$('#currencyBtn').textContent=usd?'IQD':'USD';$$('[data-iqd]').forEach(el=>{const n=Number(el.dataset.iqd);el.textContent=usd?`$${(n/1310).toFixed(0)}*`:`${n.toLocaleString('en-US')} د.ع`});if(usd)show('تحويل USD تقديري للعرض فقط؛ السعر النهائي سيُربط بسعر الصرف من الإدارة.')};
 const ar={navHome:'الرئيسية',navServices:'الخدمات',navVisas:'التأشيرات',navIdp:'الرخص الدولية',navOffers:'العروض',navContact:'اتصل بنا',companyLogin:'دخول الشركات'};
 const en={navHome:'Home',navServices:'Services',navVisas:'Visas',navIdp:'International License',navOffers:'Offers',navContact:'Contact',companyLogin:'Companies Login'};
 let english=false;$('#langBtn').onclick=()=>{english=!english;document.documentElement.lang=english?'en':'ar';document.documentElement.dir=english?'ltr':'rtl';$('#langBtn').textContent=english?'AR':'EN';const d=english?en:ar;Object.entries(d).forEach(([k,v])=>{const el=document.querySelector(`[data-i18n="${k}"]`);if(el)el.textContent=v});show(english?'English interface enabled. Full content translation will be managed in the next backend phase.':'تم تفعيل الواجهة العربية.')};
};

if (document.readyState === 'loading') {
 document.addEventListener('DOMContentLoaded', initALAQTAR);
} else {
 initALAQTAR();
}
