import {describe,it,expect} from 'vitest';
import {visibleRows,validate,defaults,fileName,indexedRows,needsReview} from '../src/model';
describe('results and geometry settings',()=>{
 it('keeps unverified rows separate, searches notes and combines unchanged labels',()=>{const rows=[{a_index:0,b_index:0,status:'SAME',note:'base'},{a_index:1,b_index:1,status:'RENAMED',note:'renamed'},{a_index:2,b_index:null,status:'UNCERTAIN',note:'Osłona Molex'}];expect(visibleRows(rows,'','SAME')).toHaveLength(2);expect(visibleRows(rows,'molex','UNCERTAIN')).toHaveLength(1);expect(visibleRows(rows,'molex','SAME')).toHaveLength(0)});
 it('rejects invalid precision and density before a native job starts',()=>{expect(validate(defaults)).toBe('');expect(validate({...defaults,tolerance:NaN})).not.toBe('');expect(validate({...defaults,density:-1})).not.toBe('')});
 it('handles Windows and Unix filenames',()=>{expect(fileName('C:\\Models\\arm.step')).toBe('arm.step');expect(fileName('/tmp/arm.stp')).toBe('arm.stp')});
});

describe('review workspace identity',()=>{
 it('uses original row positions after filtering instead of page or filtered offsets',()=>{
  const rows=indexedRows({records:[{a_index:0,b_index:0,status:'SAME'},{a_index:2,b_index:null,status:'UNCERTAIN',name_a:'Osłona'},{a_index:null,b_index:7,status:'ADDED'}]});
  expect(visibleRows(rows,'','CHANGES').map(r=>r.record_index)).toEqual([1,2]);
  expect(visibleRows(rows,'osłona','DIAGNOSTIC').map(r=>r.record_index)).toEqual([1]);
  expect(needsReview(rows[2])).toBe(false);
 });
});
