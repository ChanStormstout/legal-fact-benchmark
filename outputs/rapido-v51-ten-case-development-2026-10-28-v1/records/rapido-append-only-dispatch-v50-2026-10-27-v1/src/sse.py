"""Frozen V38 SSE parsing reused; no project runner imports or model loading."""
import json,time,hashlib

class StreamProtocolError(ValueError):
    pass

def consume_sse(lines, raw, content, reasoning, receipt):
    """Preserve every received byte and parse SSE frames, without completing JSON.

    DONE closes the stream; it does not certify that the model completed its
    answer. Usage-only frames and comments are legal and never discarded.
    """
    data=[];frame_type=None;events=0;byte_count=0;terminal=False
    started=time.monotonic();first=None;last=None;framing_hash=hashlib.sha256()
    def emit():
        nonlocal events,terminal,first,last
        if not data:return
        payload='\n'.join(data)
        events+=1;now=time.monotonic();first=now if first is None else first;last=now
        if terminal:raise StreamProtocolError('DATA_AFTER_DONE')
        if payload=='[DONE]':
            terminal=True;receipt['done_received']=True;return
        try:event=json.loads(payload)
        except json.JSONDecodeError as exc:raise StreamProtocolError('MALFORMED_SSE_JSON') from exc
        if not isinstance(event,dict):raise StreamProtocolError('NON_OBJECT_SSE_EVENT')
        if event.get('error') or frame_type=='error':
            receipt['provider_error']=event.get('error',event)
            raise StreamProtocolError('PROVIDER_STREAM_ERROR')
        for key in ('id','model'):
            if key in event and receipt.get(key) not in (None,event[key]):
                raise StreamProtocolError('STREAM_'+key.upper()+'_CHANGED')
        for key in ('id','model','created','system_fingerprint'):
            if key in event:receipt[key]=event[key]
        if event.get('usage') is not None:
            receipt['usage']=event['usage'];receipt['usage_event_count']=receipt.get('usage_event_count',0)+1
        if event.get('warnings'):receipt.setdefault('provider_warnings',[]).extend(event['warnings'])
        for choice in event.get('choices',[]):
            if choice.get('index',0)!=0:raise StreamProtocolError('UNEXPECTED_EXTRA_CHOICE')
            delta=choice.get('delta',choice.get('message',{})) or {}
            if delta.get('content'):
                if receipt.get('finish_reason') is not None:raise StreamProtocolError('CONTENT_AFTER_FINISH')
                content.write(delta['content']);content.flush()
            for key in ('reasoning','reasoning_content'):
                if delta.get(key):reasoning.write(delta[key]);reasoning.flush()
            finish=choice.get('finish_reason')
            if finish is not None:
                if receipt.get('finish_reason') not in (None,finish):raise StreamProtocolError('FINISH_REASON_CHANGED')
                receipt['finish_reason']=finish
                receipt['finish_event_count']=receipt.get('finish_event_count',0)+1
    try:
        for encoded in lines:
            if isinstance(encoded,str):encoded=encoded.encode('utf-8')
            raw.write(encoded);raw.flush();byte_count+=len(encoded);framing_hash.update(encoded)
            line=encoded.decode('utf-8').rstrip('\r\n')
            if not line:
                emit();data=[];frame_type=None
            elif line.startswith(':'):continue
            else:
                field,sep,value=line.partition(':')
                if value.startswith(' '):value=value[1:]
                if field=='data':data.append(value)
                elif field=='event':frame_type=value
        emit()
    finally:
        receipt['stream_evidence']={'event_count':events,'received_bytes':byte_count,
            'received_sha256':framing_hash.hexdigest(),'first_event_seconds':None if first is None else first-started,
            'last_event_seconds':None if last is None else last-started,
            'done_received':receipt.get('done_received',False),'finish_reason':receipt.get('finish_reason'),
            'usage_received':isinstance(receipt.get('usage'),dict),'raw_bytes_preserved':True}

def reported_usage(receipt):
    value=receipt.get('usage')
    if not isinstance(value,dict):return None
    keys=('prompt_tokens','completion_tokens')
    if any(type(value.get(k)) is not int or value[k]<0 for k in keys):return None
    if 'total_tokens' in value and (type(value['total_tokens']) is not int or value['total_tokens']<sum(value[k] for k in keys)):
        return None
    return {k:value[k] for k in keys}
