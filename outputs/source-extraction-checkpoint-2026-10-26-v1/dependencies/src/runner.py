"""Transport exception interface only; no full-pipeline entry is included."""
class ResourceStop(RuntimeError):
    pass

class CallFailure(ResourceStop):
    def __init__(self,status,halt_reason=None,provider_halted=False):
        super().__init__('API:'+status)
        self.status=status
        self.halt_reason=halt_reason
        self.provider_halted=provider_halted
