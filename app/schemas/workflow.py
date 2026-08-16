from typing import List, Optional
from pydantic import BaseModel, Field

class WorkflowStep(BaseModel):
    step_number: int = Field(description="Sequential execution order")
    action_name: str = Field(description="Short imperative verb phrase (e.g., 'Verify Sample Batch ID')")
    description: str = Field(description="Detailed operational instruction for the technician/SME")
    actor_role: str = Field(description="Role responsible (e.g., 'Lab Tech', 'Compliance Lead', 'Data Manager')")
    is_compliance_critical: bool = Field(description="Flag whether failure here violates regulatory SOPs")
    deterministic_rule: Optional[str] = Field(description="Explicit condition, threshold, or validation check if applicable")

class ComplianceChecklist(BaseModel):
    workflow_name: str = Field(description="Inferred or stated title of the procedure")
    domain: str = Field(description="Industry sector (e.g., Life Sciences, Clinical Operations, Fintech)")
    summary_of_tacit_knowledge: str = Field(description="Key unwritten SME habits or hidden assumptions identified in the input")
    steps: List[WorkflowStep] = Field(description="Ordered list of standard operational steps")
    identified_risks: List[str] = Field(description="Potential bottlenecks, single points of failure, or compliance risks")