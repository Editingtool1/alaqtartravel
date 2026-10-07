document.addEventListener('DOMContentLoaded',()=>{
 const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s), wa='9647809000845';
 const nav=$('.nav'),toggle=$('.menu-toggle'),ret=$('.return-field'),toast=$('#toast');
 $('#year').textContent=new Date().getFullYear();
 if(toggle&&nav){toggle.onclick=()=>{const o=nav.classList.toggle('open');toggle.textContent=o?'✕':'☰';toggle.setAttribute('aria-expanded',o)};$$('.nav a').forEach(a=>a.onclick=()=>nav.classList.remove('open'))}
 $$('input[name="trip"]').forEach(r=>r.onchange=()=>{if(ret)ret.style.display=$('input[name="trip"]:checked').value==='oneway'?'none':'flex'});
 const show=m=>{toast.textContent=m;toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),2800)};
 const openWA=service=>window.open(`https://wa.me/${wa}?text=${encodeURIComponent('مرحباً، أرغب بطلب: '+service)}`,'_blank','noopener');
 $$('.order-btn,.visa-order').forEach(b=>b.onclick=()=>{const s=b.dataset.service||'خدمة';$('#serviceSelect').value=s.includes('تأشيرة')?'تأشيرة':s.includes('رخص')?'رخصة قيادة دولية':s.includes('عرض')?'عرض سياحي':'خدمة أخرى';$('#request').scrollIntoView({behavior:'smooth'});$('#notes').value=s});
 $('#requestForm').onsubmit=e=>{e.preventDefault();const name=$('#customerName').value.trim(),phone=$('#customerPhone').value.trim(),service=$('#serviceSelect').value,notes=$('#notes').value.trim(),files=$('#documents').files.length;const id='AQ-'+Date.now().toString().slice(-8);const msg=`مرحباً، أرغب بتقديم طلب لدى الأقطار للسفر والسياحة.\nرقم الطلب المبدئي: ${id}\nالاسم: ${name}\nالهاتف: ${phone}\nالخدمة: ${service}\nعدد الملفات المختارة: ${files}\nملاحظات: ${notes||'-'}\n\nملاحظة: الملفات لم تُرفع للموقع بعد، وسأرسل المستمسكات المطلوبة حسب تعليماتكم.`;window.open(`https://wa.me/${wa}?text=${encodeURIComponent(msg)}`,'_blank','noopener')};
 $('#flightSearchBtn').onclick=()=>show('البحث المباشر سيتفعّل بعد ربط مزود حجز الطيران API.');
 let usd=false;$('#currencyBtn').onclick=()=>{usd=!usd;$('#currencyBtn').textContent=usd?'IQD':'USD';$$('[data-iqd]').forEach(el=>{const n=Number(el.dataset.iqd);el.textContent=usd?`$${(n/1310).toFixed(0)}*`:`${n.toLocaleString('en-US')} د.ع`});if(usd)show('تحويل USD تقديري للعرض فقط؛ السعر النهائي سيُربط بسعر الصرف من الإدارة.')};
 const ar={navHome:'الرئيسية',navServices:'الخدمات',navVisas:'التأشيرات',navIdp:'الرخص الدولية',navOffers:'العروض',navContact:'اتصل بنا',companyLogin:'دخول الشركات'};
 const en={navHome:'Home',navServices:'Services',navVisas:'Visas',navIdp:'International License',navOffers:'Offers',navContact:'Contact',companyLogin:'Companies Login'};
 let english=false;$('#langBtn').onclick=()=>{english=!english;document.documentElement.lang=english?'en':'ar';document.documentElement.dir=english?'ltr':'rtl';$('#langBtn').textContent=english?'AR':'EN';const d=english?en:ar;Object.entries(d).forEach(([k,v])=>{const el=document.querySelector(`[data-i18n="${k}"]`);if(el)el.textContent=v});show(english?'English interface enabled. Full content translation will be managed in the next backend phase.':'تم تفعيل الواجهة العربية.')};
});
