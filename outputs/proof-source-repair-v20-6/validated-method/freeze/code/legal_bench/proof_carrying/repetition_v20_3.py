"""Preserve attributed-record guard scope after refs becomes ref_set."""
from .repetition_v19_6 import ExpansionGuard


class RecordGuard(ExpansionGuard):
    def completed_record(self,record,unit,start,end):
        adapted=dict(record)
        if 'ref_set' in record:adapted['refs']=['SHARED:'+record['ref_set']]
        return super().completed_record(adapted,unit,start,end)
