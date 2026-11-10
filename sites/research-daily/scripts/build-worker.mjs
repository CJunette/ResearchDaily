import {mkdir,readFile,readdir,rm,writeFile,copyFile} from 'node:fs/promises';
import {extname,join,relative,resolve} from 'node:path';

const root=resolve(import.meta.dirname,'..');
const site=join(root,'site');
const dist=join(root,'dist');
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};

async function walk(dir){const entries=await readdir(dir,{withFileTypes:true});const files=[];for(const entry of entries){const path=join(dir,entry.name);if(entry.isDirectory())files.push(...await walk(path));else files.push(path);}return files;}

const assets={};
for(const file of await walk(site)){
  const key='/'+relative(site,file).split('\\').join('/');
  assets[key]={type:types[extname(file)]||'application/octet-stream',body:await readFile(file,'utf8')};
}
const template=await readFile(join(root,'worker/index.js'),'utf8');
if(!template.includes('__RESEARCH_DAILY_ASSETS__'))throw new Error('Worker asset marker missing');
await rm(dist,{recursive:true,force:true});
await mkdir(join(dist,'server'),{recursive:true});
await mkdir(join(dist,'.openai'),{recursive:true});
await mkdir(join(dist,'migrations'),{recursive:true});
await writeFile(join(dist,'server/index.js'),template.replace('__RESEARCH_DAILY_ASSETS__',JSON.stringify(assets)),'utf8');
await copyFile(join(root,'.openai/hosting.json'),join(dist,'.openai/hosting.json'));
await copyFile(join(root,'migrations/0000_feedback.sql'),join(dist,'migrations/0000_feedback.sql'));
console.log(`Built Worker with ${Object.keys(assets).length} assets`);
