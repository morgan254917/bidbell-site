"""Offline signup contract checks. Does not submit any form."""
import json, runpy, subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Signup(unittest.TestCase):
 def test_generated_fields_preserve_provider_contract(self):
  module=runpy.run_path(str(ROOT/'tools/build.py'),run_name='build_test')
  form=module['signup_form']();config=module['C']
  self.assertIn('action="'+config['form_post']+'"',form)
  self.assertIn('method="post"',form)
  for field in config['form_entries'].values():self.assertIn('name="'+field+'"',form)
  self.assertIn('id="state-search"',form)
  self.assertNotIn('data-thanks=',form)
 def test_native_submission_no_fetch_redirect_or_duplicate_retry(self):
  js=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let submit,prevented=false,errors=0,groupCount=1;
const btn={innerHTML:'Start',disabled:false,textContent:''};
const box={hidden:true,textContent:'',scrollIntoView(){}};
const group={dataset:{label:'a trade'},querySelectorAll(){return Array(groupCount)},querySelector(){return null},classList:{add(){},remove(){}},getAttribute(){return ''},setAttribute(){},scrollIntoView(){},addEventListener(){}};
const form={querySelector(s){return s==='button[type=submit]'?btn:null},querySelectorAll(s){return s==='fieldset[data-need]'?[group]:[]},addEventListener(s,fn){if(s==='submit')submit=fn}};
const context={document:{getElementById(id){return id==='signup'?form:id==='form-error'?box:null}},window:{addEventListener(){},matchMedia(){return{matches:true}},fetch(){throw Error('No network allowed')},location:{set href(v){throw Error('False redirect')}}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
submit({preventDefault(){prevented=true}});assert.equal(prevented,false);assert.equal(btn.disabled,true);
prevented=false;submit({preventDefault(){prevented=true}});assert.equal(prevented,true);
btn.disabled=false;groupCount=0;prevented=false;submit({preventDefault(){prevented=true}});assert.equal(prevented,true);assert.equal(box.hidden,false);
'''
  import shutil
  node=shutil.which('node') or r'C:\Program Files\nodejs\node.exe'
  result=subprocess.run([node,'-e',js,str(ROOT/'form.js')],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
