"""Versioned post-run I/O fix; no model reruns in aligned-v1."""
import json,os,tempfile
from pathlib import Path

def preflight(root):
    root=Path(root)
    for name in ('weights','training','analysis'):
        folder=root/name;folder.mkdir(parents=True,exist_ok=True)
        fd,path=tempfile.mkstemp(prefix='.write-check-',dir=folder)
        os.close(fd);Path(path).unlink()

def save_completed_fit(root,stem,fit_record,save_weights):
    """Write actual fit record first, then record weight-export success/failure."""
    root=Path(root);preflight(root);record=root/'training'/(stem+'-fit.json')
    if record.exists():raise FileExistsError(record)
    record.write_text(json.dumps(fit_record,ensure_ascii=False,indent=2))
    try:
        save_weights(str(root/'weights'/(stem+'.safetensors')))
        result={'status':'OK','fit_record':str(record)}
    except Exception as exc:
        result={'status':'WEIGHT_EXPORT_FAILURE','fit_record':str(record),'error':repr(exc)}
    (root/'training'/(stem+'-export.json')).write_text(json.dumps(result,indent=2))
    return result
