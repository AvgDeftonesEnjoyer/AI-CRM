class CRMException(Exception):
    """Base CRM exception"""
    pass


class LeadNotFoundError(CRMException):
    def __init__(self, lead_id: int):
        self.lead_id = lead_id
        super().__init__(f"Lead {lead_id} not found")


class InvalidStageTransitionError(CRMException):
    def __init__(self, from_stage: str, to_stage: str):
        super().__init__(f"Cannot transition from '{from_stage}' to '{to_stage}'")


class LeadTransferError(CRMException):
    pass


class SaleNotFoundError(CRMException):
    def __init__(self, sale_id: int):
        super().__init__(f"Sale {sale_id} not found")


class AIServiceError(CRMException):
    pass
