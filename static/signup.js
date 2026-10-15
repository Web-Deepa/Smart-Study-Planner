document.addEventListener('DOMContentLoaded',function(){
    const faculty=document.getElementById('faculty_select');
    const other=document.getElementById('other_faculty_container');
    const otherf=document.getElementById('other_faculty');

    if (faculty && other && otherf){
        faculty.addEventListener('change',function(){
            if(this.value==='Others'){
                other.style.display='block';
                otherf.required=true;
                otherf.focus();
            }
           
        })
    }
})